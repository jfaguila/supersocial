"""
Narrative selection algorithm.
Picks the story arc / content angle for the next cycle based on
performance history and strategy weights.
"""
from dataclasses import dataclass
from typing import Optional

from memory.repository import Repository


NARRATIVE_CATALOG = {
    "hero_journey": {
        "description": "Personal transformation story: from broke/trapped to free",
        "best_platforms": ["instagram", "tiktok", "linkedin"],
        "content_types": ["video", "carousel", "text"],
        "base_weight": 1.0,
    },
    "system_expose": {
        "description": "Expose how the traditional system keeps people trapped",
        "best_platforms": ["twitter", "linkedin", "tiktok"],
        "content_types": ["text", "video"],
        "base_weight": 1.0,
    },
    "tactical_value": {
        "description": "Actionable step-by-step content with immediate value",
        "best_platforms": ["linkedin", "instagram", "twitter"],
        "content_types": ["carousel", "text", "reel"],
        "base_weight": 1.0,
    },
    "social_proof": {
        "description": "Results, numbers, transformation evidence",
        "best_platforms": ["instagram", "tiktok"],
        "content_types": ["video", "image"],
        "base_weight": 0.8,
    },
    "mindset_shift": {
        "description": "Challenge a common belief about money, work, or success",
        "best_platforms": ["twitter", "linkedin", "tiktok"],
        "content_types": ["text", "video"],
        "base_weight": 1.0,
    },
    "community_call": {
        "description": "Direct address to the audience identity group",
        "best_platforms": ["instagram", "twitter", "tiktok"],
        "content_types": ["video", "text"],
        "base_weight": 0.7,
    },
    "contrarian_take": {
        "description": "Disagree with popular opinion with evidence",
        "best_platforms": ["twitter", "linkedin"],
        "content_types": ["text"],
        "base_weight": 0.9,
    },
}


@dataclass
class SelectedNarrative:
    narrative_key: str
    description: str
    best_platform: str
    content_type: str
    weight_applied: float
    reason: str


class NarrativeSelector:
    def __init__(self, repo: Repository):
        self._repo = repo

    async def select(
        self,
        platform: str,
        strategic_prompt: Optional[str] = None,
        exclude_recent: Optional[list[str]] = None,
    ) -> SelectedNarrative:
        """
        Select the best narrative for the given platform.
        Applies learned strategy weights from the DB.
        """
        exclude = set(exclude_recent or [])
        weights: dict[str, float] = await self._repo.get_all_weights(platform)

        candidates = {}
        for key, meta in NARRATIVE_CATALOG.items():
            if key in exclude:
                continue
            if platform not in meta["best_platforms"] and platform != "all":
                continue
            base = meta["base_weight"]
            learned = weights.get(f"narrative.{key}", 1.0)
            candidates[key] = base * learned

        if not candidates:
            candidates = {k: v["base_weight"] for k, v in NARRATIVE_CATALOG.items() if k not in exclude}

        # If strategic prompt hints at a narrative, boost it
        if strategic_prompt:
            prompt_lower = strategic_prompt.lower()
            for key in candidates:
                if key.replace("_", " ") in prompt_lower or key in prompt_lower:
                    candidates[key] *= 2.0

        best_key = max(candidates, key=lambda k: candidates[k])
        meta = NARRATIVE_CATALOG[best_key]
        preferred_ct = meta["content_types"][0]

        return SelectedNarrative(
            narrative_key=best_key,
            description=meta["description"],
            best_platform=platform,
            content_type=preferred_ct,
            weight_applied=candidates[best_key],
            reason=f"Highest combined weight ({candidates[best_key]:.2f}) for {platform}",
        )

    async def select_weekly_plan(
        self,
        platforms: list[str],
        days: int = 7,
        strategic_prompt: Optional[str] = None,
    ) -> dict[str, list[SelectedNarrative]]:
        """Generate a 7-day narrative plan per platform."""
        plan: dict[str, list[SelectedNarrative]] = {}
        for platform in platforms:
            narratives = []
            used = []
            from config.settings import get_settings
            posts_per_day = get_settings().max_posts_per_platform_per_day
            total = days * posts_per_day
            for _ in range(total):
                n = await self.select(platform, strategic_prompt, exclude_recent=used[-3:] if len(used) >= 3 else [])
                narratives.append(n)
                used.append(n.narrative_key)
            plan[platform] = narratives
        return plan
