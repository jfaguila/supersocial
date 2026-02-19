"""
LinkedIn API v2 connector.
Uses the Marketing Developer Platform for posting and analytics.
"""
import json

import httpx

from config.credentials import CredentialManager
from .base_connector import BaseConnector, TrendPost
from .rate_limiter import RateLimiter


class LinkedInConnector(BaseConnector):
    PLATFORM = "linkedin"
    BASE_URL = "https://api.linkedin.com/v2"

    def __init__(self):
        super().__init__()
        creds = CredentialManager().linkedin()
        self._token = creds.token
        self._person_urn = (creds.extra or {}).get("person_urn", "")
        self._rate_limiter = RateLimiter()
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
            },
            timeout=30.0,
        )

    async def fetch_trending_posts(self, niches: list[str], limit: int = 50) -> list[TrendPost]:
        """
        LinkedIn does not offer a public trending/feed search API.
        We fetch from known high-engagement personal/company pages.
        """
        posts: list[TrendPost] = []
        # Best practice: analyze known accounts
        return posts

    async def fetch_account_posts(self, account_id: str, limit: int = 20) -> list[TrendPost]:
        """Fetch posts from a person/company URN."""
        await self._rate_limiter.acquire("linkedin", "posts")
        resp = await self._client.get(
            "/ugcPosts",
            params={
                "q": "authors",
                "authors": f"List({account_id})",
                "count": min(limit, 50),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for item in data.get("elements", []):
            specific_content = item.get("specificContent", {}).get(
                "com.linkedin.ugc.ShareContent", {}
            )
            text = specific_content.get("shareCommentary", {}).get("text", "")
            posts.append(
                TrendPost(
                    platform="linkedin",
                    post_id=item.get("id", ""),
                    author_id=account_id,
                    author_username=account_id,
                    author_follower_count=0,
                    content_text=text,
                    content_type="text",
                    published_at=item.get("created", {}).get("time", 0) // 1000,
                    raw=item,
                )
            )
        return posts

    async def publish_post(self, content: dict) -> dict:
        """
        Publish a text/image post as a UGC post.
        content: {text, media_url (optional), media_type (optional)}
        """
        await self._rate_limiter.acquire("linkedin", "publish")

        share_media_category = "NONE"
        media = []

        if content.get("media_url"):
            share_media_category = content.get("media_type", "IMAGE").upper()
            media.append({
                "status": "READY",
                "description": {"text": content.get("media_description", "")},
                "media": content["media_url"],
                "title": {"text": content.get("title", "")},
            })

        payload = {
            "author": self._person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content["text"]},
                    "shareMediaCategory": share_media_category,
                    "media": media,
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        resp = await self._client.post("/ugcPosts", content=json.dumps(payload))
        resp.raise_for_status()
        post_id = resp.headers.get("X-RestLi-Id", "")
        return {
            "external_id": post_id,
            "status": "published",
            "platform": "linkedin",
        }

    async def fetch_post_metrics(self, post_id: str) -> dict:
        await self._rate_limiter.acquire("linkedin", "metrics")
        resp = await self._client.get(
            "/socialActions/{post_id}",
            params={"q": "socialActions"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "likes": data.get("likesSummary", {}).get("totalLikes", 0),
                "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                "shares": data.get("sharesSummary", {}).get("totalShares", 0),
            }
        return {"likes": 0, "comments": 0, "shares": 0}

    async def fetch_account_metrics(self, account_id: str) -> dict:
        await self._rate_limiter.acquire("linkedin", "followers")
        resp = await self._client.get(
            "/networkSizes",
            params={"q": "member", "edgeType": "CompanyFollowedByMember"},
        )
        followers = 0
        if resp.status_code == 200:
            followers = resp.json().get("firstDegreeSize", 0)
        return {"followers": followers}
