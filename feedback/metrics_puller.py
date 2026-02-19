"""
Metrics puller.
Fetches fresh 7-day performance data from all platforms
and stores it in the performance_metrics table.
"""
import time
from datetime import datetime

from data_layer.twitter_connector import TwitterConnector
from data_layer.tiktok_connector import TikTokConnector
from data_layer.linkedin_connector import LinkedInConnector
from data_layer.instagram_connector import InstagramConnector
from memory.models import PostHistory
from memory.repository import Repository


CONNECTORS = {
    "twitter": TwitterConnector,
    "tiktok": TikTokConnector,
    "linkedin": LinkedInConnector,
    "instagram": InstagramConnector,
}


class MetricsPuller:
    def __init__(self, repo: Repository):
        self._repo = repo

    async def pull_7day_metrics(self, cycle_id: str) -> dict[str, int]:
        """
        Pull metrics for all published posts from last 7 days.
        Returns counts: {platform: posts_updated}.
        """
        seven_days_ago = int(time.time()) - 7 * 86400
        posts: list[PostHistory] = await self._repo.get_published_posts_since(seven_days_ago)

        results: dict[str, int] = {}

        for post in posts:
            platform = post.platform
            connector_class = CONNECTORS.get(platform)
            if not connector_class or not post.external_id:
                continue

            async with connector_class() as connector:
                try:
                    raw_metrics = await connector.fetch_post_metrics(post.external_id)

                    engagement_rate = self._compute_engagement(raw_metrics)
                    virality = self._compute_virality(raw_metrics)

                    await self._repo.save_metrics(
                        post_id=post.id,
                        platform=platform,
                        window_hours=168,  # 7 days
                        impressions=raw_metrics.get("impressions", 0),
                        likes=raw_metrics.get("likes", 0),
                        comments=raw_metrics.get("comments", 0),
                        shares=raw_metrics.get("shares", 0),
                        saves=raw_metrics.get("saves", raw_metrics.get("bookmarks", 0)),
                        views=raw_metrics.get("views", 0),
                        engagement_rate=engagement_rate,
                        virality_score=virality,
                    )
                    results[platform] = results.get(platform, 0) + 1
                except Exception:
                    continue

        return results

    async def pull_account_snapshots(self, cycle_id: str, platforms: list[str]) -> dict[str, dict]:
        """Snapshot follower counts for all configured platforms."""
        snapshots: dict[str, dict] = {}
        for platform in platforms:
            connector_class = CONNECTORS.get(platform)
            if not connector_class:
                continue
            async with connector_class() as connector:
                try:
                    metrics = await connector.fetch_account_metrics("me")
                    snapshots[platform] = metrics
                except Exception:
                    snapshots[platform] = {}
        return snapshots

    def _compute_engagement(self, metrics: dict) -> float:
        total = (
            metrics.get("likes", 0)
            + metrics.get("comments", 0)
            + metrics.get("shares", 0)
            + metrics.get("saves", 0)
        )
        impressions = max(metrics.get("impressions", 0), 1)
        return total / impressions

    def _compute_virality(self, metrics: dict) -> float:
        """Shares weighted higher as virality signal."""
        return (
            metrics.get("likes", 0)
            + metrics.get("comments", 0) * 2
            + metrics.get("shares", 0) * 3
            + metrics.get("saves", 0) * 2
        ) / max(metrics.get("impressions", 1), 1)
