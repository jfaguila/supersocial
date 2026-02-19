"""
Smart time-slot allocator.
Uses historical engagement data to find optimal posting times per platform.
Updates strategy_weights with peak_hour.{hour} keys.
"""
from collections import defaultdict

from memory.repository import Repository


class TimeSlotAllocator:
    def __init__(self, repo: Repository):
        self._repo = repo

    async def recalculate(self, platforms: list[str]) -> dict[str, list[int]]:
        """
        Analyze published post performance by hour of day.
        Updates DB weights for peak hours.
        Returns {platform: [hour1, hour2, hour3]}.
        """
        results: dict[str, list[int]] = {}
        for platform in platforms:
            hour_engagement: dict[int, list[float]] = defaultdict(list)

            posts = await self._repo.get_published_posts_since(since_ts=0)
            platform_posts = [p for p in posts if p.platform == platform and p.published_at]

            for post in platform_posts:
                import time
                hour = int(time.gmtime(post.published_at).tm_hour)
                metrics_list = await self._repo.get_metrics_for_post(post.id, window_hours=168)
                if metrics_list:
                    er = metrics_list[-1].engagement_rate or 0
                    hour_engagement[hour].append(er)

            if not hour_engagement:
                results[platform] = []
                continue

            hour_avg = {h: sum(vals) / len(vals) for h, vals in hour_engagement.items()}
            top_hours = sorted(hour_avg, key=lambda h: -hour_avg[h])[:4]

            # Update DB weights
            for rank, hour in enumerate(top_hours):
                weight = 1.0 + (len(top_hours) - rank) * 0.2
                await self._repo.set_weight(
                    platform,
                    f"peak_hour.{hour}",
                    weight,
                    reason=f"Learned from {len(hour_engagement.get(hour, []))} posts",
                )

            results[platform] = top_hours

        return results
