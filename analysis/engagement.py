"""
Engagement ratio computation and scoring.
Produces normalized scores across platforms with different engagement scales.
"""
import statistics
from dataclasses import dataclass
from typing import Optional

from data_layer.base_connector import TrendPost


@dataclass
class EngagementScore:
    post_id: str
    platform: str
    raw_engagement_rate: float
    normalized_score: float        # 0.0 – 1.0 relative to batch
    virality_score: float
    save_ratio: float              # saves / impressions (intent signal)
    comment_ratio: float          # comments / likes (controversy / depth)
    share_ratio: float            # shares / impressions
    tier: str                     # S|A|B|C|D


class EngagementAnalyzer:
    """
    Analyzes a batch of TrendPost objects and returns ranked engagement scores.
    Normalizes scores within each platform cohort before cross-platform comparison.
    """

    TIER_THRESHOLDS = {
        "S": 0.85,
        "A": 0.70,
        "B": 0.50,
        "C": 0.30,
        "D": 0.0,
    }

    def analyze(self, posts: list[TrendPost]) -> list[EngagementScore]:
        if not posts:
            return []

        raw_rates = [p.engagement_rate for p in posts]
        mean = statistics.mean(raw_rates) if raw_rates else 0
        std = statistics.stdev(raw_rates) if len(raw_rates) > 1 else 1.0

        scores = []
        for post in posts:
            rate = post.engagement_rate
            # Z-score normalization then sigmoid squash to 0-1
            z = (rate - mean) / (std or 1)
            normalized = 1 / (1 + 2.718 ** (-z))

            save_ratio = post.saves / max(post.impressions, 1)
            comment_ratio = post.comments / max(post.likes, 1)
            share_ratio = post.shares / max(post.impressions, 1)

            tier = "D"
            for t, threshold in self.TIER_THRESHOLDS.items():
                if normalized >= threshold:
                    tier = t
                    break

            scores.append(
                EngagementScore(
                    post_id=post.post_id,
                    platform=post.platform,
                    raw_engagement_rate=rate,
                    normalized_score=normalized,
                    virality_score=post.virality_score,
                    save_ratio=save_ratio,
                    comment_ratio=comment_ratio,
                    share_ratio=share_ratio,
                    tier=tier,
                )
            )

        return sorted(scores, key=lambda s: s.normalized_score, reverse=True)

    def top_posts(self, posts: list[TrendPost], top_n: int = 10) -> list[TrendPost]:
        """Return top N posts by engagement score."""
        scores = self.analyze(posts)
        top_ids = {s.post_id for s in scores[:top_n]}
        return [p for p in posts if p.post_id in top_ids]

    def platform_benchmark(self, posts: list[TrendPost]) -> dict[str, dict]:
        """Compute per-platform engagement benchmarks."""
        by_platform: dict[str, list[float]] = {}
        for p in posts:
            by_platform.setdefault(p.platform, []).append(p.engagement_rate)

        benchmarks = {}
        for platform, rates in by_platform.items():
            benchmarks[platform] = {
                "mean": statistics.mean(rates),
                "median": statistics.median(rates),
                "p90": sorted(rates)[int(len(rates) * 0.9)] if len(rates) >= 10 else max(rates),
                "count": len(rates),
            }
        return benchmarks
