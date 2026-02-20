"""
Capa 3 — Multi-platform content generation.

Takes scored TrendSignal rows and generates ContentDraft entries
for each target platform (Instagram, TikTok, LinkedIn, X, YouTube).

For video platforms (TikTok, YouTube), the generated script is
automatically passed through the video pipeline (Runway + ElevenLabs)
to produce a ready-to-publish .mp4 file.
"""
import logging
import os
import time
from typing import Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from content.llm_client import LLMClient
from memory.models import ContentDraft, TrendSignal

logger = logging.getLogger(__name__)

# Platforms that get auto-video generation
VIDEO_PLATFORMS = {"tiktok", "youtube"}
VIDEO_EXPORT_DIR = os.environ.get("VIDEO_EXPORT_DIR", "/data/video_exports")

# Platform-specific generation instructions
PLATFORM_SPECS: dict[str, dict] = {
    "instagram": {
        "content_type": "post",
        "max_chars": 2200,
        "hashtags_max": 15,
        "instruction": (
            "Write an Instagram caption. Start with a powerful hook (first line must stop the scroll). "
            "Body: 3-5 insights or a micro-story. End with CTA + hashtags. "
            "Tone: aspirational, visual, community-focused. Use line breaks for readability."
        ),
    },
    "tiktok": {
        "content_type": "script",
        "max_chars": 2200,
        "hashtags_max": 5,
        "instruction": (
            "Write a 60-second TikTok script. Format:\n"
            "HOOK (0-3s): [first words — must stop scroll]\n"
            "BODY (3-50s): [core message, rapid delivery, conversational]\n"
            "CTA (50-60s): [follow/comment/share ask]\n"
            "Tone: raw, energetic, authentic. Write spoken words only."
        ),
    },
    "linkedin": {
        "content_type": "post",
        "max_chars": 3000,
        "hashtags_max": 3,
        "instruction": (
            "Write a LinkedIn post. Start with a hook that creates curiosity. "
            "Tell a story or share a contrarian insight. End with a question or CTA. "
            "Tone: professional but human, story-driven, thought-leadership. "
            "Use short paragraphs and line breaks."
        ),
    },
    "twitter": {
        "content_type": "thread",
        "max_chars": 280,
        "hashtags_max": 2,
        "instruction": (
            "Write a Twitter/X thread (5-7 tweets). First tweet = powerful hook. "
            "Each tweet must stand alone but build on previous. "
            "Last tweet = CTA. Tone: direct, punchy, controversial or insightful. "
            "Mark each tweet with its number: 1/, 2/, etc."
        ),
    },
    "youtube": {
        "content_type": "idea",
        "max_chars": 5000,
        "hashtags_max": 5,
        "instruction": (
            "Write a YouTube video concept. Include:\n"
            "TITLE: [click-worthy title, under 60 chars]\n"
            "THUMBNAIL TEXT: [3-5 words for thumbnail overlay]\n"
            "HOOK (first 30s): [what to say to retain viewers]\n"
            "OUTLINE: [5-7 bullet points for the video structure]\n"
            "CTA: [subscribe/comment prompt]\n"
            "Tone: educational, authoritative, slightly provocative."
        ),
    },
}

GENERATOR_SYSTEM_PROMPT = """You are a world-class social media content strategist for a B2B AI agency.

You create platform-specific content that drives engagement and positions the brand as an authority
in AI, automation, and digital transformation.

RULES:
- Every piece must have a strong hook in the first line
- No generic advice. Be specific, contrarian, and data-driven when possible
- Adapt tone and format strictly to the target platform
- Include relevant hashtags at the end (count specified per platform)
- Return ONLY the finished content. No preamble, no explanation.
- Write in the language specified"""


class ContentGenerator:
    """Generate platform-specific content from scored trends."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        platforms: Optional[list[str]] = None,
        language: str = "es",
        generate_videos: bool = True,
    ):
        self.llm = llm or LLMClient()
        self.platforms = platforms or ["instagram", "tiktok", "linkedin", "twitter"]
        self.language = language
        self.generate_videos = generate_videos

    async def generate_from_signals(
        self,
        session: AsyncSession,
        signals: list[TrendSignal],
    ) -> list[ContentDraft]:
        """Generate content for each signal x platform combination."""
        drafts: list[ContentDraft] = []
        now = int(time.time())

        for signal in signals:
            for platform in self.platforms:
                spec = PLATFORM_SPECS.get(platform)
                if not spec:
                    continue

                draft = await self._generate_one(signal, platform, spec)
                if not draft:
                    continue

                # Determine if this draft needs video rendering
                needs_video = (
                    self.generate_videos
                    and platform in VIDEO_PLATFORMS
                    and spec["content_type"] in ("script", "idea")
                )

                row = ContentDraft(
                    signal_id=signal.id,
                    platform=platform,
                    content_type=spec["content_type"],
                    content_text=draft["content"],
                    hook_text=draft.get("hook", ""),
                    hashtags=draft.get("hashtags", ""),
                    emotional_tone=draft.get("tone", ""),
                    narrative_type=signal.viral_angle or "",
                    char_count=len(draft["content"]),
                    status="pending_review",
                    video_status="pending" if needs_video else None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                await session.flush()  # get the row ID

                # Render video if needed
                if needs_video:
                    video_result = await self._render_video(
                        row, platform, signal, draft["content"]
                    )
                    if video_result:
                        row.video_path = video_result.get("video_path", "")
                        row.video_srt_path = video_result.get("srt_path", "")
                        row.video_status = "ready"
                    else:
                        row.video_status = "failed"

                drafts.append(row)

            # Mark signal as used
            signal.status = "used"

        await session.flush()
        return drafts

    async def _render_video(
        self,
        draft: ContentDraft,
        platform: str,
        signal: TrendSignal,
        script_text: str,
    ) -> Optional[dict]:
        """Run the video pipeline on a script draft.

        Returns {"video_path": ..., "srt_path": ...} or None on failure.
        """
        try:
            from config.settings import get_settings
            from video.script_formatter import ScriptFormatter
            from video.render_exporter import VideoPipeline

            settings = get_settings()

            # Check that video APIs are configured
            if not getattr(settings, "runwayml_api_key", ""):
                logger.warning(
                    f"[content_generator] Runway API key not set — skipping video for draft {draft.id}"
                )
                return None

            # Format the raw script into timed segments
            formatter = ScriptFormatter()
            formatted = formatter.format(
                raw_script=script_text,
                platform=platform,
                title=signal.keyword[:40],
            )

            # Run the full video pipeline
            output_dir = os.path.join(VIDEO_EXPORT_DIR, f"pipeline_{draft.id}")
            pipeline = VideoPipeline(settings=settings)
            result = await pipeline.run(
                script=formatted,
                output_dir=output_dir,
                niches=settings.niches,
                business_context="B2B AI automation agency",
            )

            if result.success:
                logger.info(
                    f"[content_generator] video ready: {result.final_video_path} "
                    f"({result.scenes_count} scenes, {result.duration_seconds}s)"
                )
                return {
                    "video_path": result.final_video_path,
                    "srt_path": result.srt_path,
                }
            else:
                logger.warning(
                    f"[content_generator] video failed for draft {draft.id}: {result.error}"
                )
                return None

        except Exception as e:
            logger.error(f"[content_generator] video pipeline error: {e}")
            return None

    async def _generate_one(
        self, signal: TrendSignal, platform: str, spec: dict
    ) -> Optional[dict]:
        """Generate a single content piece for one platform."""
        user_prompt = f"""{spec['instruction']}

TREND TO COVER:
- Keyword: {signal.keyword}
- Viral angle: {signal.viral_angle or 'Find the best angle'}
- Target audience: {signal.ideal_client or 'B2B professionals, entrepreneurs'}
- Category: {signal.category or 'technology'}

CONSTRAINTS:
- Maximum {spec['max_chars']} characters
- Maximum {spec['hashtags_max']} hashtags
- Language: {self.language}
- Platform: {platform}

Generate the content now."""

        try:
            response = await self.llm.generate(
                system_prompt=GENERATOR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=1500,
                temperature=0.85,
            )

            content = response.content.strip()
            if not content:
                return None

            # Extract hook (first line)
            lines = content.split("\n")
            hook = lines[0].strip() if lines else ""

            # Extract hashtags from end
            hashtags = ""
            for line in reversed(lines):
                if "#" in line:
                    hashtags = line.strip()
                    break

            return {
                "content": content,
                "hook": hook[:200],
                "hashtags": hashtags,
                "tone": signal.ideal_client or "",
            }
        except Exception:
            return None
