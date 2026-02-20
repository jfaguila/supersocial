"""
Metricool API integration — Capa 5 publisher.

Metricool acts as the final scheduler/publisher.
Approved content is sent here for scheduling and auto-publishing.

API docs: https://developers.metricool.com
"""
import time
from typing import Optional

import httpx

from config.settings import get_settings


class MetricoolClient:
    """Client for Metricool's scheduling API."""

    BASE_URL = "https://app.metricool.com/api/v2"

    def __init__(self, api_token: Optional[str] = None, user_token: Optional[str] = None):
        self.api_token = api_token or ""
        self.user_token = user_token or ""

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.api_token)

    async def schedule_post(
        self,
        platform: str,
        content: str,
        scheduled_at: int,
        media_urls: Optional[list[str]] = None,
    ) -> dict:
        """Schedule a post through Metricool.

        Returns:
            {"id": "metricool-post-id", "status": "scheduled", "scheduled_at": ...}
        """
        if not self.is_configured():
            return {"error": "Metricool not configured", "status": "skipped"}

        # Map our platform names to Metricool's
        platform_map = {
            "instagram": "instagram",
            "tiktok": "tiktok",
            "linkedin": "linkedin",
            "twitter": "twitter",
            "youtube": "youtube",
        }
        metricool_platform = platform_map.get(platform, platform)

        payload: dict = {
            "networks": [metricool_platform],
            "text": content,
            "scheduledDate": scheduled_at * 1000,  # Metricool uses milliseconds
        }

        if media_urls:
            payload["mediaUrls"] = media_urls

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/scheduler/posts",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "id": data.get("id", ""),
                    "status": "scheduled",
                    "scheduled_at": scheduled_at,
                    "platform": platform,
                }
        except httpx.HTTPStatusError as e:
            return {
                "error": f"Metricool API error: {e.response.status_code}",
                "status": "failed",
                "detail": e.response.text[:500],
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    async def get_scheduled_posts(self, platform: Optional[str] = None) -> list[dict]:
        """Fetch posts currently in Metricool's schedule queue."""
        if not self.is_configured():
            return []

        try:
            params: dict = {}
            if platform:
                params["network"] = platform

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/scheduler/posts",
                    headers=self._headers,
                    params=params,
                )
                resp.raise_for_status()
                return resp.json().get("posts", [])
        except Exception:
            return []

    async def delete_scheduled_post(self, post_id: str) -> bool:
        """Cancel a scheduled post in Metricool."""
        if not self.is_configured():
            return False

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.delete(
                    f"{self.BASE_URL}/scheduler/posts/{post_id}",
                    headers=self._headers,
                )
                return resp.status_code in (200, 204)
        except Exception:
            return False

    async def get_analytics(self, platform: str, days: int = 7) -> dict:
        """Pull engagement analytics from Metricool for a platform."""
        if not self.is_configured():
            return {}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/analytics/{platform}",
                    headers=self._headers,
                    params={"days": days},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            return {}
