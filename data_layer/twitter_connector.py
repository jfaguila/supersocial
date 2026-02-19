"""
X (Twitter) API v2 connector.
Handles trend fetching, account analysis, publishing, and metrics.
"""
import time
from typing import Any

import httpx

from config.credentials import CredentialManager
from .base_connector import BaseConnector, TrendPost
from .rate_limiter import RateLimiter


class TwitterConnector(BaseConnector):
    PLATFORM = "twitter"
    BASE_URL = "https://api.twitter.com/2"

    # Target accounts for analysis (handles — configurable)
    ANALYSIS_ACCOUNTS = [
        "garyvee", "naval", "tferriss", "elonmusk", "alexhormozi",
    ]

    NICHE_KEYWORDS = {
        "entrepreneurship": "entrepreneur startup founder hustle",
        "financial_freedom": "financial freedom passive income wealth",
        "network_marketing": "mlm network marketing downline",
        "anti_system": "freedom matrix redpill sovereignty",
    }

    def __init__(self):
        super().__init__()
        creds = CredentialManager().twitter()
        self._bearer = creds.token
        self._extra = creds.extra or {}
        self._rate_limiter = RateLimiter()
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self._bearer}",
                "User-Agent": "SuperSocial/1.0",
            },
            timeout=30.0,
        )

    async def fetch_trending_posts(self, niches: list[str], limit: int = 50) -> list[TrendPost]:
        query_parts = [self.NICHE_KEYWORDS.get(n, n) for n in niches]
        query = " OR ".join(f"({q})" for q in query_parts[:3])
        query += " -is:retweet lang:en min_faves:100"

        await self._rate_limiter.acquire("twitter", "search")

        resp = await self._client.get(
            "/tweets/search/recent",
            params={
                "query": query,
                "max_results": min(limit, 100),
                "tweet.fields": "public_metrics,created_at,author_id,text",
                "expansions": "author_id",
                "user.fields": "public_metrics,username",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        users_map: dict[str, Any] = {
            u["id"]: u for u in data.get("includes", {}).get("users", [])
        }

        posts = []
        for tweet in data.get("data", []):
            metrics = tweet.get("public_metrics", {})
            author = users_map.get(tweet["author_id"], {})
            author_metrics = author.get("public_metrics", {})
            posts.append(
                TrendPost(
                    platform="twitter",
                    post_id=tweet["id"],
                    author_id=tweet["author_id"],
                    author_username=author.get("username", ""),
                    author_follower_count=author_metrics.get("followers_count", 0),
                    content_text=tweet["text"],
                    content_type="text",
                    published_at=int(
                        time.mktime(
                            time.strptime(tweet["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        )
                    ),
                    likes=metrics.get("like_count", 0),
                    comments=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                    impressions=metrics.get("impression_count", 0),
                    raw=tweet,
                )
            )
        return posts

    async def fetch_account_posts(self, account_id: str, limit: int = 20) -> list[TrendPost]:
        await self._rate_limiter.acquire("twitter", "timeline")
        resp = await self._client.get(
            f"/users/{account_id}/tweets",
            params={
                "max_results": min(limit, 100),
                "tweet.fields": "public_metrics,created_at",
                "exclude": "retweets,replies",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for tweet in data.get("data", []):
            metrics = tweet.get("public_metrics", {})
            posts.append(
                TrendPost(
                    platform="twitter",
                    post_id=tweet["id"],
                    author_id=account_id,
                    author_username="",
                    author_follower_count=0,
                    content_text=tweet["text"],
                    content_type="text",
                    published_at=0,
                    likes=metrics.get("like_count", 0),
                    comments=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                    impressions=metrics.get("impression_count", 0),
                    raw=tweet,
                )
            )
        return posts

    async def publish_post(self, content: dict) -> dict:
        """Publish a tweet. content must have 'text' key."""
        await self._rate_limiter.acquire("twitter", "publish")
        # Use OAuth 1.0a for publishing (bearer token is read-only)
        resp = await self._client.post(
            "/tweets",
            json={"text": content["text"]},
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "external_id": data["data"]["id"],
            "status": "published",
            "platform": "twitter",
        }

    async def fetch_post_metrics(self, post_id: str) -> dict:
        await self._rate_limiter.acquire("twitter", "metrics")
        resp = await self._client.get(
            f"/tweets/{post_id}",
            params={"tweet.fields": "public_metrics,non_public_metrics"},
        )
        resp.raise_for_status()
        metrics = resp.json().get("data", {}).get("public_metrics", {})
        return {
            "likes": metrics.get("like_count", 0),
            "comments": metrics.get("reply_count", 0),
            "shares": metrics.get("retweet_count", 0),
            "impressions": metrics.get("impression_count", 0),
            "bookmarks": metrics.get("bookmark_count", 0),
        }

    async def fetch_account_metrics(self, account_id: str) -> dict:
        await self._rate_limiter.acquire("twitter", "users")
        resp = await self._client.get(
            f"/users/{account_id}",
            params={"user.fields": "public_metrics"},
        )
        resp.raise_for_status()
        metrics = resp.json().get("data", {}).get("public_metrics", {})
        return {
            "followers": metrics.get("followers_count", 0),
            "following": metrics.get("following_count", 0),
            "tweet_count": metrics.get("tweet_count", 0),
        }
