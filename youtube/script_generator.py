"""
YouTube script generator — 5-scene structured scripts.

Generates scripts with the fixed structure:
    1. HOOK       — Grab attention in first 5 seconds
    2. PROBLEM    — Identify the viewer's pain point
    3. DEEPENING  — Explore why the problem persists
    4. SOLUTION   — Present the actionable solution
    5. CTA        — Call to action (subscribe, comment, link)

Each scene includes: narration text, timing, visual description.
"""
import json
import logging
from dataclasses import dataclass, field

from content.llm_client import LLMClient

logger = logging.getLogger(__name__)

SCENE_TYPES = ["hook", "problem", "deepening", "solution", "cta"]


@dataclass
class ScriptScene:
    index: int
    scene_type: str  # hook | problem | deepening | solution | cta
    narration: str
    visual_description: str
    duration_seconds: float
    start_second: float = 0.0
    end_second: float = 0.0
    word_count: int = 0
    include_character: bool = True  # Whether character appears in frame


@dataclass
class YouTubeScript:
    topic: str
    title_suggestion: str
    total_duration_seconds: float
    scenes: list[ScriptScene]
    full_narration: str
    language: str = "en"
    niche: str = ""
    word_count: int = 0

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "title_suggestion": self.title_suggestion,
            "total_duration_seconds": self.total_duration_seconds,
            "language": self.language,
            "niche": self.niche,
            "word_count": self.word_count,
            "scenes": [
                {
                    "index": s.index,
                    "scene_type": s.scene_type,
                    "narration": s.narration,
                    "visual_description": s.visual_description,
                    "duration_seconds": s.duration_seconds,
                    "start_second": s.start_second,
                    "end_second": s.end_second,
                    "include_character": s.include_character,
                }
                for s in self.scenes
            ],
        }


# Duration distribution by scene type (percentage of total)
# Hook is short and punchy, Solution gets the most time
_DURATION_WEIGHTS = {
    "hook": 0.08,       # ~5% - 15-25 seconds
    "problem": 0.22,    # ~22% - 40-80 seconds
    "deepening": 0.30,  # ~30% - 55-110 seconds
    "solution": 0.30,   # ~30% - 55-110 seconds
    "cta": 0.10,        # ~10% - 20-35 seconds
}

WORDS_PER_SECOND = 2.5  # YouTube narration pace (slower than TikTok)


class YouTubeScriptGenerator:
    """
    Generates a 5-scene YouTube script via LLM with strict structure.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self._llm = llm_client or LLMClient()

    async def generate(
        self,
        topic: str,
        niche: str,
        tone: str = "professional, authoritative",
        target_duration_minutes: int = 5,
        language: str = "en",
        character_name: str = "the narrator",
    ) -> YouTubeScript:
        """
        Generate a structured 5-scene YouTube script.

        Args:
            topic: Video topic/title concept
            niche: Content niche (e.g. "artificial_intelligence")
            tone: Desired tone of the narration
            target_duration_minutes: Target video length in minutes (3-8)
            language: Output language code
            character_name: Name of the character for narration context
        """
        target_seconds = target_duration_minutes * 60
        target_words = int(target_seconds * WORDS_PER_SECOND)

        scene_targets = {}
        for scene_type, weight in _DURATION_WEIGHTS.items():
            scene_seconds = target_seconds * weight
            scene_words = int(scene_seconds * WORDS_PER_SECOND)
            scene_targets[scene_type] = {
                "seconds": round(scene_seconds),
                "words": scene_words,
            }

        system_prompt = self._build_system_prompt(tone, language, character_name)
        user_prompt = self._build_user_prompt(
            topic, niche, target_words, scene_targets, language,
        )

        response = await self._llm.generate_json(system_prompt, user_prompt)
        script = self._parse_response(response, topic, niche, target_seconds, language)

        logger.info(
            f"[yt_script] generated script for '{topic}': "
            f"{len(script.scenes)} scenes, {script.word_count} words, "
            f"{script.total_duration_seconds:.0f}s"
        )
        return script

    def _build_system_prompt(self, tone: str, language: str, character_name: str) -> str:
        lang_instruction = ""
        if language != "en":
            lang_instruction = f"\nIMPORTANT: Write ALL narration text in language code '{language}'."

        return f"""You are a world-class YouTube scriptwriter specializing in educational and motivational content.

You write scripts for {character_name}, a YouTube creator with a {tone} style.
{lang_instruction}

RULES:
- Every script MUST have exactly 5 scenes in this order: hook, problem, deepening, solution, cta
- The HOOK must grab attention in the first 5-10 seconds with a provocative question or shocking statement
- The PROBLEM must identify a specific pain point the viewer relates to
- The DEEPENING must explore WHY the problem persists and add depth/data/examples
- The SOLUTION must present clear, actionable steps the viewer can take
- The CTA must ask for subscribe, comment, or click a link — with a reason WHY
- Each scene needs a VISUAL DESCRIPTION of what should be shown on screen
- Mark which scenes show the character (include_character: true/false)
- Write as spoken words only. No stage directions. Natural speech.
- Be specific. No generic advice. Include real examples, numbers, frameworks.
- Do NOT use cliches like "In today's video" or "What's up guys"

Return valid JSON with this exact structure:
{{
  "title_suggestion": "SEO-optimized title under 70 chars",
  "scenes": [
    {{
      "scene_type": "hook",
      "narration": "The spoken words for this scene...",
      "visual_description": "What the viewer sees on screen...",
      "include_character": true
    }},
    ... (5 scenes total)
  ]
}}"""

    def _build_user_prompt(
        self,
        topic: str,
        niche: str,
        target_words: int,
        scene_targets: dict,
        language: str,
    ) -> str:
        scene_breakdown = "\n".join(
            f"  - {st.upper()}: ~{info['words']} words ({info['seconds']}s)"
            for st, info in scene_targets.items()
        )

        return f"""Generate a YouTube script about:

TOPIC: {topic}
NICHE: {niche}
TARGET TOTAL WORDS: {target_words}
LANGUAGE: {language}

Word count per scene:
{scene_breakdown}

The visual_description for each scene should describe what a viewer would SEE — not what is said.
Think: B-roll footage, data visualizations, the character speaking to camera, screen recordings, etc.

Return ONLY the JSON object. No markdown, no explanation."""

    def _parse_response(
        self,
        data: dict,
        topic: str,
        niche: str,
        target_seconds: float,
        language: str,
    ) -> YouTubeScript:
        """Parse LLM JSON response into a YouTubeScript."""
        raw_scenes = data.get("scenes", [])
        title_suggestion = data.get("title_suggestion", topic[:70])

        scenes: list[ScriptScene] = []
        current_time = 0.0

        for i, raw in enumerate(raw_scenes[:5]):
            scene_type = raw.get("scene_type", SCENE_TYPES[i] if i < 5 else "body")
            narration = raw.get("narration", "")
            visual = raw.get("visual_description", "")
            include_char = raw.get("include_character", True)

            word_count = len(narration.split())
            duration = word_count / WORDS_PER_SECOND

            scenes.append(ScriptScene(
                index=i,
                scene_type=scene_type,
                narration=narration,
                visual_description=visual,
                duration_seconds=round(duration, 2),
                start_second=round(current_time, 2),
                end_second=round(current_time + duration, 2),
                word_count=word_count,
                include_character=include_char,
            ))
            current_time += duration + 0.5  # 500ms pause between scenes

        # Fill missing scenes if LLM returned fewer than 5
        while len(scenes) < 5:
            idx = len(scenes)
            stype = SCENE_TYPES[idx]
            scenes.append(ScriptScene(
                index=idx,
                scene_type=stype,
                narration=f"[{stype} placeholder — regenerate]",
                visual_description="Generic B-roll footage",
                duration_seconds=5.0,
                start_second=round(current_time, 2),
                end_second=round(current_time + 5.0, 2),
                word_count=0,
                include_character=True,
            ))
            current_time += 5.5

        full_narration = " ".join(s.narration for s in scenes)
        total_words = sum(s.word_count for s in scenes)

        return YouTubeScript(
            topic=topic,
            title_suggestion=title_suggestion,
            total_duration_seconds=round(current_time, 1),
            scenes=scenes,
            full_narration=full_narration,
            language=language,
            niche=niche,
            word_count=total_words,
        )
