"""
Emotional angle selector.
Picks the emotional trigger most likely to perform on a given platform
based on historical performance data.
"""
from dataclasses import dataclass
from typing import Optional

from memory.repository import Repository


EMOTION_PLATFORM_AFFINITY: dict[str, dict[str, float]] = {
    "twitter": {
        "anger": 1.4,
        "contrarian": 1.3,
        "aspiration": 1.1,
        "fear": 1.0,
        "identity": 1.2,
        "hope": 0.8,
    },
    "tiktok": {
        "aspiration": 1.4,
        "story": 1.3,
        "fear": 1.2,
        "identity": 1.1,
        "hope": 1.0,
        "anger": 0.9,
    },
    "linkedin": {
        "aspiration": 1.3,
        "social_proof": 1.4,
        "tactical": 1.3,
        "identity": 1.0,
        "hope": 1.1,
        "fear": 0.8,
    },
    "instagram": {
        "aspiration": 1.5,
        "identity": 1.3,
        "social_proof": 1.2,
        "hope": 1.2,
        "fear": 0.9,
        "anger": 0.7,
    },
}


@dataclass
class SelectedEmotion:
    emotion_key: str
    platform: str
    affinity_score: float
    learned_weight: float
    final_score: float


class EmotionSelector:
    def __init__(self, repo: Repository):
        self._repo = repo

    async def select(self, platform: str, narrative_key: str) -> SelectedEmotion:
        platform_affinity = EMOTION_PLATFORM_AFFINITY.get(platform, {})
        weights = await self._repo.get_all_weights(platform)

        scored: dict[str, float] = {}
        for emotion, affinity in platform_affinity.items():
            learned = weights.get(f"emotion.{emotion}", 1.0)
            scored[emotion] = affinity * learned

        if not scored:
            return SelectedEmotion("aspiration", platform, 1.0, 1.0, 1.0)

        best = max(scored, key=lambda k: scored[k])
        affinity = platform_affinity.get(best, 1.0)
        learned = weights.get(f"emotion.{best}", 1.0)

        return SelectedEmotion(
            emotion_key=best,
            platform=platform,
            affinity_score=affinity,
            learned_weight=learned,
            final_score=scored[best],
        )
