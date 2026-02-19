"""
Cycle comparator.
Compares this week's performance to the previous cycle
to detect what improved, what declined, and what to change.
"""
from dataclasses import dataclass
from typing import Optional

from memory.repository import Repository


@dataclass
class CycleComparison:
    platform: str
    engagement_delta_pct: float       # positive = improved
    reach_delta_pct: float
    follower_delta: int
    best_hook_type: str
    worst_hook_type: Optional[str]
    best_emotional_trigger: str
    worst_content_type: Optional[str]
    best_narrative: Optional[str]
    recommendations: list[str]


class CycleComparator:
    def __init__(self, repo: Repository):
        self._repo = repo

    async def compare(self, platform: str, current_cycle_id: str) -> CycleComparison:
        """
        Compare current cycle metrics to previous cycle.
        Generates actionable recommendations.
        """
        current = await self._repo.get_growth_history(platform, weeks=1)
        previous = await self._repo.get_growth_history(platform, weeks=2)

        curr_growth = current[0] if current else None
        prev_growth = previous[1] if len(previous) > 1 else None

        engagement_delta = 0.0
        reach_delta = 0.0
        follower_delta = 0

        if curr_growth and prev_growth:
            if prev_growth.avg_engagement and prev_growth.avg_engagement > 0:
                engagement_delta = (
                    (curr_growth.avg_engagement - prev_growth.avg_engagement)
                    / prev_growth.avg_engagement
                    * 100
                )
            if prev_growth.avg_reach and prev_growth.avg_reach > 0:
                reach_delta = (
                    (curr_growth.avg_reach - prev_growth.avg_reach)
                    / prev_growth.avg_reach
                    * 100
                )
            follower_delta = curr_growth.follower_delta or 0

        # Analyze post-level performance for pattern insights
        top_hooks = await self._repo.get_top_hooks(limit=5)
        best_hook = top_hooks[0].pattern_type if top_hooks else "unknown"
        worst_hook = None

        top_triggers = await self._repo.get_top_triggers(platform=platform, limit=1)
        best_trigger = top_triggers[0].trigger_name if top_triggers else "aspiration"

        recommendations = self._generate_recommendations(
            engagement_delta=engagement_delta,
            reach_delta=reach_delta,
            follower_delta=follower_delta,
            best_hook=best_hook,
        )

        return CycleComparison(
            platform=platform,
            engagement_delta_pct=round(engagement_delta, 1),
            reach_delta_pct=round(reach_delta, 1),
            follower_delta=follower_delta,
            best_hook_type=best_hook,
            worst_hook_type=worst_hook,
            best_emotional_trigger=best_trigger,
            worst_content_type=None,
            best_narrative=None,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        engagement_delta: float,
        reach_delta: float,
        follower_delta: int,
        best_hook: str,
    ) -> list[str]:
        recs = []
        if engagement_delta < -10:
            recs.append(f"Engagement dropped {abs(engagement_delta):.1f}% — shift to more {best_hook} hooks")
        elif engagement_delta > 20:
            recs.append(f"Strong engagement growth ({engagement_delta:.1f}%) — double down on current strategy")

        if reach_delta < -15:
            recs.append("Reach declining — increase posting frequency or diversify hashtags")

        if follower_delta < 0:
            recs.append("Net follower loss — audit content quality and consistency")
        elif follower_delta > 500:
            recs.append(f"Strong follower growth (+{follower_delta}) — amplify with cross-platform promotion")

        if not recs:
            recs.append("Performance stable — continue current strategy with minor optimizations")

        return recs
