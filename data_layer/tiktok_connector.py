"""
TikTok Content Posting API connector.
Uses TikTok for Business API v2 for content discovery and publishing.
"""
import time

import httpx

from config.credentials import CredentialManager
from .base_connector import BaseConnector, TrendPost
from .rate_limiter import RateLimiter


class TikTokConnector(BaseConnector):
    PLATFORM = "tiktok"
    BASE_URL = "https://open.tiktokapis.com/v2"

    HASHTAG_TARGETS = [
        "entrepreneur", "financialfreedom", "sidehustle",
        "passiveincome", "networkmarketing", "mindset",
    ]

    def __init__(self):
        super().__init__()
        creds = CredentialManager().tiktok()
        self._token = creds.token
        self._extra = creds.extra or {}
        self._rate_limiter = RateLimiter()
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            timeout=30.0,
        )

    async def fetch_trending_posts(self, niches: list[str], limit: int = 50) -> list[TrendPost]:
        """
        TikTok Research API — requires approved Research API access.
        Queries videos by hashtag combination.
        """
        await self._rate_limiter.acquire("tiktok", "search")

        hashtags = self.HASHTAG_TARGETS[:5]
        resp = await self._client.post(
            "/research/video/query/",
            json={
                "query": {
                    "and": [
                        {
                            "operation": "IN",
                            "field_name": "hashtag_name",
                            "field_values": hashtags,
                        }
                    ]
                },
                "start_date": _days_ago(7),
                "end_date": _today(),
                "max_count": min(limit, 100),
                "fields": "id,create_time,username,video_description,like_count,comment_count,share_count,view_count,play_url",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        posts = []
        for video in data.get("data", {}).get("videos", []):
            posts.append(
                TrendPost(
                    platform="tiktok",
                    post_id=str(video["id"]),
                    author_id=video.get("username", ""),
                    author_username=video.get("username", ""),
                    author_follower_count=0,
                    content_text=video.get("video_description", ""),
                    content_type="video",
                    published_at=video.get("create_time", 0),
                    likes=video.get("like_count", 0),
                    comments=video.get("comment_count", 0),
                    shares=video.get("share_count", 0),
                    views=video.get("view_count", 0),
                    raw=video,
                )
            )
        return posts

    async def fetch_account_posts(self, account_id: str, limit: int = 20) -> list[TrendPost]:
        await self._rate_limiter.acquire("tiktok", "user_videos")
        resp = await self._client.post(
            "/research/user/info/",
            json={
                "username": account_id,
                "fields": "display_name,follower_count,video_count",
            },
        )
        resp.raise_for_status()
        return []

    async def publish_post(self, content: dict) -> dict:
        """
        Publish a video to TikTok via Content Posting API.
        content must include: video_url, caption, hashtags
        """
        await self._rate_limiter.acquire("tiktok", "publish")

        # Step 1: Initialize video upload
        init_resp = await self._client.post(
            "/post/publish/video/init/",
            json={
                "post_info": {
                    "title": content.get("caption", ""),
                    "privacy_level": "SELF_ONLY" if content.get("draft") else "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": content["video_url"],
                },
            },
        )
        init_resp.raise_for_status()
        publish_id = init_resp.json().get("data", {}).get("publish_id")

        return {
            "external_id": publish_id,
            "status": "processing",
            "platform": "tiktok",
        }

    async def fetch_post_metrics(self, post_id: str) -> dict:
        await self._rate_limiter.acquire("tiktok", "metrics")
        resp = await self._client.post(
            "/research/video/query/",
            json={
                "query": {"and": [{"operation": "EQ", "field_name": "video_id", "field_values": [post_id]}]},
                "start_date": _days_ago(30),
                "end_date": _today(),
                "fields": "like_count,comment_count,share_count,view_count",
            },
        )
        resp.raise_for_status()
        videos = resp.json().get("data", {}).get("videos", [{}])
        v = videos[0] if videos else {}
        return {
            "likes": v.get("like_count", 0),
            "comments": v.get("comment_count", 0),
            "shares": v.get("share_count", 0),
            "views": v.get("view_count", 0),
        }

    async def fetch_account_metrics(self, account_id: str) -> dict:
        await self._rate_limiter.acquire("tiktok", "user_info")
        resp = await self._client.post(
            "/research/user/info/",
            json={"username": account_id, "fields": "follower_count,video_count,likes_count"},
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "followers": data.get("follower_count", 0),
            "video_count": data.get("video_count", 0),
            "total_likes": data.get("likes_count", 0),
        }


def _today() -> str:
    return time.strftime("%Y%m%d")


def _days_ago(n: int) -> str:
    return time.strftime("%Y%m%d", time.gmtime(time.time() - n * 86400))
