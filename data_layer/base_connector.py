"""
Abstract base class for all platform API connectors.
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import get_settings


@dataclass
class TrendPost:
    """Normalized post object from any platform."""
    platform: str
    post_id: str
    author_id: str
    author_username: str
    author_follower_count: int
    content_text: str
    content_type: str              # text|image|video|carousel|reel
    published_at: int              # Unix timestamp
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: int = 0
    impressions: int = 0
    hashtags: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def engagement_rate(self) -> float:
        total = self.likes + self.comments + self.shares + self.saves
        if self.impressions > 0:
            return total / self.impressions
        if self.author_follower_count > 0:
            return total / self.author_follower_count
        return 0.0

    @property
    def virality_score(self) -> float:
        """Simplified virality: shares are weighted 3x."""
        return (self.likes + self.comments + self.shares * 3 + self.saves * 2) / max(
            self.author_follower_count, 1
        )


class BaseConnector(ABC):
    PLATFORM: str = ""
    BASE_URL: str = ""

    def __init__(self):
        self._settings = get_settings()
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "SuperSocial/1.0 (+github.com/supersocial)"},
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    @abstractmethod
    async def fetch_trending_posts(
        self, niches: list[str], limit: int = 50
    ) -> list[TrendPost]:
        """Fetch trending posts relevant to our target niches."""
        ...

    @abstractmethod
    async def fetch_account_posts(
        self, account_id: str, limit: int = 20
    ) -> list[TrendPost]:
        """Fetch recent posts from a specific account for analysis."""
        ...

    @abstractmethod
    async def publish_post(self, content: dict) -> dict:
        """Publish a post. Returns dict with external_id and status."""
        ...

    @abstractmethod
    async def fetch_post_metrics(self, post_id: str) -> dict:
        """Pull engagement metrics for a specific post."""
        ...

    @abstractmethod
    async def fetch_account_metrics(self, account_id: str) -> dict:
        """Pull follower count, reach, and profile metrics."""
        ...

    def _retry_decorator(self):
        settings = get_settings()
        return retry(
            retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
            stop=stop_after_attempt(settings.george_max_retries),
            wait=wait_exponential(
                multiplier=settings.george_retry_base_seconds,
                min=settings.george_retry_base_seconds,
                max=settings.george_retry_base_seconds ** 3,
            ),
            reraise=True,
        )
