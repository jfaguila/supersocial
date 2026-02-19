"""
Instagram Graph API connector.
Requires a Facebook Business account with Instagram connected.
"""
import httpx

from config.credentials import CredentialManager
from .base_connector import BaseConnector, TrendPost
from .rate_limiter import RateLimiter


class InstagramConnector(BaseConnector):
    PLATFORM = "instagram"
    BASE_URL = "https://graph.facebook.com/v19.0"

    HASHTAG_TARGETS = [
        "entrepreneur", "financialfreedom", "passiveincome",
        "mindset", "networkmarketing", "freedom",
    ]

    def __init__(self):
        super().__init__()
        creds = CredentialManager().instagram()
        self._token = creds.token
        self._extra = creds.extra or {}
        self._account_id = self._extra.get("business_account_id", "")
        self._rate_limiter = RateLimiter()
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
        )

    def _params(self, extra: dict = None) -> dict:
        base = {"access_token": self._token}
        if extra:
            base.update(extra)
        return base

    async def fetch_trending_posts(self, niches: list[str], limit: int = 50) -> list[TrendPost]:
        """Fetch top media for target hashtags."""
        posts: list[TrendPost] = []
        for hashtag in self.HASHTAG_TARGETS[:3]:
            await self._rate_limiter.acquire("instagram", "hashtag")

            # Step 1: Get hashtag ID
            id_resp = await self._client.get(
                "/ig_hashtag_search",
                params=self._params({"user_id": self._account_id, "q": hashtag}),
            )
            if id_resp.status_code != 200:
                continue
            hashtag_id = id_resp.json().get("data", [{}])[0].get("id")
            if not hashtag_id:
                continue

            # Step 2: Get top media
            media_resp = await self._client.get(
                f"/{hashtag_id}/top_media",
                params=self._params({
                    "user_id": self._account_id,
                    "fields": "id,media_type,caption,like_count,comments_count,timestamp",
                    "limit": min(limit // 3, 50),
                }),
            )
            if media_resp.status_code != 200:
                continue

            for item in media_resp.json().get("data", []):
                posts.append(
                    TrendPost(
                        platform="instagram",
                        post_id=item["id"],
                        author_id="",
                        author_username="",
                        author_follower_count=0,
                        content_text=item.get("caption", ""),
                        content_type=item.get("media_type", "IMAGE").lower(),
                        published_at=0,
                        likes=item.get("like_count", 0),
                        comments=item.get("comments_count", 0),
                        hashtags=[hashtag],
                        raw=item,
                    )
                )
        return posts

    async def fetch_account_posts(self, account_id: str, limit: int = 20) -> list[TrendPost]:
        await self._rate_limiter.acquire("instagram", "media")
        resp = await self._client.get(
            f"/{account_id}/media",
            params=self._params({
                "fields": "id,media_type,caption,like_count,comments_count,timestamp,permalink",
                "limit": min(limit, 100),
            }),
        )
        resp.raise_for_status()
        posts = []
        for item in resp.json().get("data", []):
            posts.append(
                TrendPost(
                    platform="instagram",
                    post_id=item["id"],
                    author_id=account_id,
                    author_username="",
                    author_follower_count=0,
                    content_text=item.get("caption", ""),
                    content_type=item.get("media_type", "IMAGE").lower(),
                    published_at=0,
                    likes=item.get("like_count", 0),
                    comments=item.get("comments_count", 0),
                    raw=item,
                )
            )
        return posts

    async def publish_post(self, content: dict) -> dict:
        """
        Two-step publish: create container → publish container.
        content: {caption, image_url OR video_url, media_type}
        """
        await self._rate_limiter.acquire("instagram", "publish")

        media_type = content.get("media_type", "IMAGE").upper()
        container_params: dict = {
            "caption": content.get("caption", ""),
        }

        if media_type == "VIDEO":
            container_params["media_type"] = "REELS"
            container_params["video_url"] = content["video_url"]
        elif media_type == "CAROUSEL":
            # Carousel requires separate children creation — simplified here
            container_params["media_type"] = "CAROUSEL"
        else:
            container_params["image_url"] = content["image_url"]

        # Step 1: Create media container
        container_resp = await self._client.post(
            f"/{self._account_id}/media",
            params=self._params(container_params),
        )
        container_resp.raise_for_status()
        container_id = container_resp.json().get("id")

        # Step 2: Publish
        publish_resp = await self._client.post(
            f"/{self._account_id}/media_publish",
            params=self._params({"creation_id": container_id}),
        )
        publish_resp.raise_for_status()
        post_id = publish_resp.json().get("id")

        return {
            "external_id": post_id,
            "status": "published",
            "platform": "instagram",
        }

    async def fetch_post_metrics(self, post_id: str) -> dict:
        await self._rate_limiter.acquire("instagram", "insights")
        resp = await self._client.get(
            f"/{post_id}/insights",
            params=self._params({
                "metric": "impressions,reach,likes,comments,shares,saved,profile_visits",
            }),
        )
        if resp.status_code != 200:
            return {}
        metrics: dict = {}
        for item in resp.json().get("data", []):
            metrics[item["name"]] = item.get("values", [{}])[-1].get("value", 0)
        return metrics

    async def fetch_account_metrics(self, account_id: str) -> dict:
        await self._rate_limiter.acquire("instagram", "account")
        resp = await self._client.get(
            f"/{account_id}",
            params=self._params({"fields": "followers_count,media_count,profile_views"}),
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "followers": data.get("followers_count", 0),
            "media_count": data.get("media_count", 0),
            "profile_views": data.get("profile_views", 0),
        }
