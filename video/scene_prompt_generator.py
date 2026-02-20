"""
Scene prompt generator.
Divides a video script into visual scenes and generates
Runway-compatible text prompts for each one.

Each scene prompt describes what should be SEEN visually —
not what is said. George uses the niche and script content
to create relevant, business-focused visual descriptions.
"""
from dataclasses import dataclass

from .script_formatter import FormattedScript, ScriptSegment


# Visual style keywords appended to every scene prompt
_STYLE_SUFFIX = (
    "cinematic, 4K, professional, sharp focus, smooth motion, "
    "social media vertical format 9:16"
)

# Topic → visual keywords mapping for niche-specific imagery
_NICHE_VISUALS: dict[str, str] = {
    "artificial_intelligence": "futuristic tech interface, glowing neural networks, data streams",
    "entrepreneurship": "modern office, entrepreneur working, city skyline, growth charts",
    "financial_freedom": "luxury lifestyle, passive income concept, financial charts, freedom",
    "network_marketing": "team meeting, collaboration, success celebration, business network",
    "anti_system": "breaking chains, freedom concept, alternative path, rebellion aesthetic",
    "marketing": "brand strategy board, digital campaign, audience engagement",
    "technology": "cutting-edge devices, code on screens, innovation lab",
    "business": "corporate environment, business meeting, professional setting",
}

# Hook segment visual: always attention-grabbing
_HOOK_VISUAL = (
    "dramatic close-up, bold typography on screen, fast-paced cut, "
    "eye-catching opener"
)

# CTA segment visual: always compelling ending
_CTA_VISUAL = (
    "motivational scene, call to action graphic, follow button animation, "
    "engaging outro"
)


@dataclass
class VideoScene:
    index: int
    start_second: float
    end_second: float
    duration_seconds: float
    segment_type: str          # hook | body | cta
    narration_text: str        # what is said (for ElevenLabs)
    visual_prompt: str         # what Runway generates
    clip_duration: int         # 5 or 10 seconds (Runway supported values)


@dataclass
class SceneBundle:
    title: str
    platform: str
    total_duration_seconds: float
    scenes: list[VideoScene]
    full_narration: str        # complete script for voiceover
    niche_keywords: list[str]


class ScenePromptGenerator:
    """
    Converts a FormattedScript into a list of VideoScenes,
    each with a visual_prompt ready to send to Runway Gen-3.
    """

    MAX_SCENES = 8
    MIN_SCENES = 3

    def generate(
        self,
        script: FormattedScript,
        niches: list[str] | None = None,
        business_context: str = "",
    ) -> SceneBundle:
        """
        Generate scenes from a formatted script.

        Args:
            script: Formatted script from ScriptFormatter
            niches: List of content niches (e.g. ['artificial_intelligence', 'entrepreneurship'])
            business_context: Optional extra context about the business (e.g. "AI consulting agency")
        """
        niches = niches or []
        niche_visual_context = self._build_niche_visual_context(niches)

        # Group segments into scenes (merge short segments together)
        scene_groups = self._group_segments_into_scenes(script.segments)

        scenes: list[VideoScene] = []
        for i, group in enumerate(scene_groups):
            seg_type = group[0].segment_type
            narration = " ".join(seg.text for seg in group)
            start = group[0].start_second
            end = group[-1].end_second
            duration = end - start

            visual_prompt = self._build_visual_prompt(
                segment_type=seg_type,
                narration=narration,
                niche_visual_context=niche_visual_context,
                business_context=business_context,
                scene_index=i,
                total_scenes=len(scene_groups),
            )

            # Runway supports 5s or 10s clips
            clip_duration = 10 if duration > 7 else 5

            scenes.append(VideoScene(
                index=i,
                start_second=round(start, 2),
                end_second=round(end, 2),
                duration_seconds=round(duration, 2),
                segment_type=seg_type,
                narration_text=narration,
                visual_prompt=visual_prompt,
                clip_duration=clip_duration,
            ))

        full_narration = " ".join(seg.text for seg in script.segments)
        niche_kw = [kw for n in niches for kw in _NICHE_VISUALS.get(n, "").split(", ") if kw]

        return SceneBundle(
            title=script.title,
            platform=script.platform,
            total_duration_seconds=script.total_duration_seconds,
            scenes=scenes,
            full_narration=full_narration,
            niche_keywords=niche_kw[:10],
        )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _group_segments_into_scenes(
        self, segments: list[ScriptSegment]
    ) -> list[list[ScriptSegment]]:
        """
        Merge short consecutive segments so we have between MIN_SCENES
        and MAX_SCENES total scenes.
        """
        if not segments:
            return []

        # If already within bounds, each segment is its own scene
        if self.MIN_SCENES <= len(segments) <= self.MAX_SCENES:
            return [[seg] for seg in segments]

        # Too many segments → merge body segments together
        if len(segments) > self.MAX_SCENES:
            hook_segs = [s for s in segments if s.segment_type == "hook"]
            cta_segs = [s for s in segments if s.segment_type == "cta"]
            body_segs = [s for s in segments if s.segment_type == "body"]

            # Split body into (MAX_SCENES - hook - cta) groups
            body_target = max(1, self.MAX_SCENES - len(hook_segs) - len(cta_segs))
            body_groups = self._split_into_n_groups(body_segs, body_target)

            groups: list[list[ScriptSegment]] = []
            groups.extend([[s] for s in hook_segs])
            groups.extend(body_groups)
            groups.extend([[s] for s in cta_segs])
            return groups

        # Too few → each segment becomes its own scene anyway
        return [[seg] for seg in segments]

    def _split_into_n_groups(
        self, items: list[ScriptSegment], n: int
    ) -> list[list[ScriptSegment]]:
        """Split a list into n roughly equal groups."""
        if not items:
            return []
        n = min(n, len(items))
        size = max(1, len(items) // n)
        groups = []
        for i in range(0, len(items), size):
            groups.append(items[i: i + size])
            if len(groups) == n:
                break
        return groups

    def _build_niche_visual_context(self, niches: list[str]) -> str:
        parts = []
        for niche in niches:
            visual = _NICHE_VISUALS.get(niche, "")
            if visual:
                parts.append(visual)
        return ", ".join(parts) if parts else "professional business environment"

    def _build_visual_prompt(
        self,
        segment_type: str,
        narration: str,
        niche_visual_context: str,
        business_context: str,
        scene_index: int,
        total_scenes: int,
    ) -> str:
        """
        Build a Runway visual prompt from narration content and context.
        """
        if segment_type == "hook":
            base = _HOOK_VISUAL
        elif segment_type == "cta":
            base = _CTA_VISUAL
        else:
            # Extract key visual nouns from narration for body scenes
            visual_keywords = self._extract_visual_keywords(narration)
            base = f"{niche_visual_context}, {visual_keywords}"

        business_suffix = f", {business_context}" if business_context else ""
        return f"{base}{business_suffix}, {_STYLE_SUFFIX}"

    def _extract_visual_keywords(self, text: str) -> str:
        """
        Simple keyword extractor: pull meaningful nouns/verbs for visual prompts.
        Avoids first/second person pronouns.
        """
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "i", "you", "we", "they", "it", "this", "that", "and", "or",
            "but", "in", "on", "at", "to", "for", "of", "with", "by",
            "from", "not", "no", "can", "will", "do", "did", "have", "has",
            "your", "my", "our", "their", "its", "if", "when", "how",
        }
        words = [
            w.lower().strip(".,!?;:\"'")
            for w in text.split()
            if len(w) > 3 and w.lower().strip(".,!?;:\"'") not in stop_words
        ]
        # Take first 6 unique keywords
        seen: set[str] = set()
        keywords = []
        for w in words:
            if w not in seen:
                seen.add(w)
                keywords.append(w)
            if len(keywords) >= 6:
                break
        return ", ".join(keywords) if keywords else "professional scene"
