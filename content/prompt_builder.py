"""
Structured prompt builder for content generation.
Produces precise, constrained prompts that generate platform-optimized content.
"""
from dataclasses import dataclass
from typing import Optional

from analysis.trend_detector import TrendReport
from strategy.narrative_selector import SelectedNarrative
from strategy.emotion_selector import SelectedEmotion
from strategy.authority_selector import SelectedAuthority


# Platform character/word limits and format constraints
PLATFORM_CONSTRAINTS: dict[str, dict] = {
    "twitter": {
        "max_chars": 280,
        "format": "text",
        "hashtags_max": 2,
        "emojis": "minimal",
        "tone": "direct, punchy, controversial or insightful",
    },
    "tiktok": {
        "max_chars": 2200,
        "format": "video_script",
        "hashtags_max": 5,
        "emojis": "moderate",
        "tone": "energetic, relatable, raw, authentic",
        "duration_seconds": 60,
    },
    "linkedin": {
        "max_chars": 3000,
        "format": "long_text",
        "hashtags_max": 3,
        "emojis": "professional",
        "tone": "professional, insightful, story-driven",
    },
    "instagram": {
        "max_chars": 2200,
        "format": "caption",
        "hashtags_max": 15,
        "emojis": "moderate",
        "tone": "aspirational, visual, community-focused",
    },
}

NICHE_CONTEXT = {
    "entrepreneurship": "building businesses, escaping employment, creating value, founding companies",
    "financial_freedom": "passive income, investments, wealth building, escaping the rat race",
    "network_marketing": "leverage, team building, residual income, MLM, direct sales",
    "anti_system": "questioning mainstream career advice, rejecting 9-5, sovereignty, alternative paths",
}


@dataclass
class ContentPrompt:
    system_prompt: str
    user_prompt: str
    platform: str
    content_type: str
    narrative_key: str
    emotion_key: str


class PromptBuilder:
    def build(
        self,
        platform: str,
        narrative: SelectedNarrative,
        emotion: SelectedEmotion,
        authority: SelectedAuthority,
        trend_report: Optional[TrendReport],
        niches: list[str],
        strategic_prompt: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> ContentPrompt:
        constraints = PLATFORM_CONSTRAINTS.get(platform, PLATFORM_CONSTRAINTS["twitter"])
        ct = content_type or narrative.content_type
        niche_context = " | ".join(NICHE_CONTEXT.get(n, n) for n in niches[:2])

        # Trend context injection
        trend_context = ""
        if trend_report and trend_report.top_keywords:
            top_kws = [kw for kw, _ in trend_report.top_keywords[:8]]
            trend_context = f"\nCurrently trending keywords: {', '.join(top_kws)}"
            if trend_report.rising_topics:
                trend_context += f"\nRising topics: {', '.join(trend_report.rising_topics[:5])}"

        system_prompt = self._build_system(platform, constraints, authority, emotion)
        user_prompt = self._build_user(
            platform=platform,
            constraints=constraints,
            narrative=narrative,
            emotion=emotion,
            authority=authority,
            content_type=ct,
            niche_context=niche_context,
            trend_context=trend_context,
            strategic_prompt=strategic_prompt,
        )

        return ContentPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            platform=platform,
            content_type=ct,
            narrative_key=narrative.narrative_key,
            emotion_key=emotion.emotion_key,
        )

    def _build_system(self, platform: str, constraints: dict, authority: SelectedAuthority, emotion: SelectedEmotion) -> str:
        return f"""You are a world-class content strategist specializing in {platform} growth for entrepreneurship and financial freedom niches.

Your role is to generate SINGLE PIECES of high-performing {platform} content — not multiple variations.

Authority frame: {authority.description}
Emotional driver: {emotion.emotion_key}
Tone: {constraints.get('tone', 'authentic and direct')}

HARD RULES:
- Maximum {constraints['max_chars']} characters
- Maximum {constraints['hashtags_max']} hashtags (place at end only)
- {"Include a strong hook in the first line" if platform != "twitter" else "Hook IS the entire post — first 5 words must grab attention"}
- End with a clear call-to-action (CTA)
- No generic advice. No clichés. Be specific and original.
- Write as a real person, not a corporate brand
- Do NOT use: "In today's digital landscape", "As an entrepreneur", "I'm excited to share"
- Return ONLY the finished post content. No preamble, no explanation."""

    def _build_user(
        self,
        platform: str,
        constraints: dict,
        narrative: SelectedNarrative,
        emotion: SelectedEmotion,
        authority: SelectedAuthority,
        content_type: str,
        niche_context: str,
        trend_context: str,
        strategic_prompt: Optional[str],
    ) -> str:
        extra_instruction = ""
        if strategic_prompt:
            extra_instruction = f"\n\nOPERATOR DIRECTIVE (incorporate this): {strategic_prompt}"

        if content_type == "video_script":
            return f"""Generate a {constraints.get('duration_seconds', 60)}-second TikTok/Reel script.

Narrative: {narrative.description}
Niche context: {niche_context}{trend_context}

Script format:
HOOK (0-3s): [first words spoken — must stop scroll]
BODY (3-45s): [core message, rapid delivery]
CTA (45-60s): [follow/comment/share ask]

Write the script as spoken words only. No stage directions.{extra_instruction}"""

        elif content_type in ("carousel", "list"):
            return f"""Generate a {platform} carousel/list post.

Narrative: {narrative.description}
Niche context: {niche_context}{trend_context}

Format: Slide 1 = hook, Slides 2-7 = numbered points, Slide 8 = CTA
Each point must be under 15 words.
Total under {constraints['max_chars']} characters combined.{extra_instruction}"""

        else:
            return f"""Generate a {platform} text post.

Narrative: {narrative.description}
Emotional angle: {emotion.emotion_key}
Niche context: {niche_context}{trend_context}

Requirements:
- First line must be a powerful hook
- Body: 3-5 key points or a compelling story
- CTA at the end
- Under {constraints['max_chars']} characters total{extra_instruction}"""
