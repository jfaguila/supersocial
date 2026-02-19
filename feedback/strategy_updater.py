"""
Strategy weight updater.
Adjusts narrative, emotion, hook, and time-slot weights
based on cycle comparison results.
"""
from .cycle_comparator import CycleComparison
from memory.repository import Repository


LEARNING_RATE = 0.15   # how aggressively weights are adjusted per cycle
MAX_WEIGHT = 3.0
MIN_WEIGHT = 0.1


class StrategyUpdater:
    def __init__(self, repo: Repository):
        self._repo = repo

    async def update(self, comparison: CycleComparison) -> dict[str, float]:
        """
        Update strategy weights based on cycle comparison.
        Returns dict of changed weights.
        """
        platform = comparison.platform
        changes: dict[str, float] = {}

        # Boost best hook type
        if comparison.best_hook_type and comparison.best_hook_type != "unknown":
            key = f"hook_type.{comparison.best_hook_type}"
            current = await self._repo.get_weight(platform, key)
            boost = min(current * (1 + LEARNING_RATE), MAX_WEIGHT)
            await self._repo.set_weight(
                platform, key, boost,
                reason=f"Best performing hook in cycle (engagement delta: {comparison.engagement_delta_pct:.1f}%)"
            )
            changes[key] = boost

        # Boost best emotional trigger
        if comparison.best_emotional_trigger:
            key = f"emotion.{comparison.best_emotional_trigger}"
            current = await self._repo.get_weight(platform, key)
            boost = min(current * (1 + LEARNING_RATE * 0.5), MAX_WEIGHT)
            await self._repo.set_weight(platform, key, boost, reason="Top emotion this cycle")
            changes[key] = boost

        # Penalize worst hook type
        if comparison.worst_hook_type:
            key = f"hook_type.{comparison.worst_hook_type}"
            current = await self._repo.get_weight(platform, key)
            penalty = max(current * (1 - LEARNING_RATE), MIN_WEIGHT)
            await self._repo.set_weight(platform, key, penalty, reason="Worst performing hook")
            changes[key] = penalty

        # Penalize worst content type
        if comparison.worst_content_type:
            key = f"content_type.{comparison.worst_content_type}"
            current = await self._repo.get_weight(platform, key)
            penalty = max(current * (1 - LEARNING_RATE), MIN_WEIGHT)
            await self._repo.set_weight(platform, key, penalty, reason="Worst content type")
            changes[key] = penalty

        # If engagement dropped, dampen current narrative weights slightly
        if comparison.engagement_delta_pct < -15 and comparison.best_narrative:
            key = f"narrative.{comparison.best_narrative}"
            current = await self._repo.get_weight(platform, key)
            adjusted = max(current * (1 - LEARNING_RATE * 0.3), MIN_WEIGHT)
            await self._repo.set_weight(platform, key, adjusted, reason="Engagement decline — reduce weight")
            changes[key] = adjusted

        return changes
