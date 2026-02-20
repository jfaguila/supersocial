"""
YouTube Data API signal source.

Fetches trending videos and search suggestions for configured niches.
Requires YOUTUBE_API_KEY in env (optional — falls back to suggestions endpoint).
"""
import time
from typing import Optional

import httpx


class YouTubeTrendsSource:
    """Capture trending topics from YouTube."""

    TRENDING_URL = "https://www.googleapis.com/youtube/v3/videos"
    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    SUGGEST_URL = "https://suggestqueries.google.com/complete/search"

    def __init__(self, api_key: str = "", region_code: str = "US"):
        self.api_key = api_key
        self.region_code = region_code

    async def fetch(self, niches: Optional[list[str]] = None) -> list[dict]:
        """Return SignalRecord dicts from YouTube."""
        signals: list[dict] = []

        if self.api_key:
            signals.extend(await self._fetch_trending())
            if niches:
                for niche in niches[:3]:
                    signals.extend(await self._fetch_search(niche))
        else:
            # Free fallback: Google suggest for YouTube
            keywords = niches or ["artificial intelligence", "entrepreneurship"]
            for kw in keywords[:3]:
                signals.extend(await self._fetch_suggestions(kw))

        return signals

    async def _fetch_trending(self) -> list[dict]:
        """Fetch YouTube trending videos (requires API key)."""
        signals: list[dict] = []
        now = int(time.time())

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    self.TRENDING_URL,
                    params={
                        "part": "snippet,statistics",
                        "chart": "mostPopular",
                        "regionCode": self.region_code,
                        "maxResults": 20,
                        "key": self.api_key,
                    },
                )
                data = resp.json()
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    stats = item.get("statistics", {})
                    title = snippet.get("title", "")
                    views = int(stats.get("viewCount", 0))

                    signals.append({
                        "source": "youtube",
                        "keyword": title,
                        "volume": views,
                        "trending_score": min(100.0, views / 100_000),
                        "region": self.region_code,
                        "category": snippet.get("categoryId", "general"),
                        "raw_data": {
                            "video_id": item.get("id", ""),
                            "channel": snippet.get("channelTitle", ""),
                            "views": views,
                            "likes": int(stats.get("likeCount", 0)),
                            "comments": int(stats.get("commentCount", 0)),
                            "tags": snippet.get("tags", [])[:10],
                        },
                        "captured_at": now,
                    })
        except Exception:
            pass

        return signals

    async def _fetch_search(self, query: str) -> list[dict]:
        """Search YouTube for a niche keyword (requires API key)."""
        signals: list[dict] = []
        now = int(time.time())

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    self.SEARCH_URL,
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "order": "viewCount",
                        "publishedAfter": self._days_ago_rfc(7),
                        "maxResults": 10,
                        "key": self.api_key,
                    },
                )
                data = resp.json()
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    signals.append({
                        "source": "youtube",
                        "keyword": snippet.get("title", ""),
                        "volume": 0,
                        "trending_score": 60.0,
                        "region": self.region_code,
                        "category": query,
                        "raw_data": {
                            "video_id": item.get("id", {}).get("videoId", ""),
                            "channel": snippet.get("channelTitle", ""),
                            "query": query,
                        },
                        "captured_at": now,
                    })
        except Exception:
            pass

        return signals

    async def _fetch_suggestions(self, query: str) -> list[dict]:
        """Free fallback: Google Suggest for YouTube queries."""
        signals: list[dict] = []
        now = int(time.time())

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    self.SUGGEST_URL,
                    params={"client": "youtube", "ds": "yt", "q": query},
                )
                # Response is JSONP-like: window.google.ac.h(...)
                text = resp.text
                import json
                # Extract JSON array from response
                start = text.index("[")
                data = json.loads(text[start:])
                suggestions = data[1] if len(data) > 1 else []
                for suggestion in suggestions[:8]:
                    kw = suggestion[0] if isinstance(suggestion, list) else str(suggestion)
                    signals.append({
                        "source": "youtube",
                        "keyword": kw,
                        "volume": 0,
                        "trending_score": 40.0,
                        "region": self.region_code,
                        "category": query,
                        "raw_data": {"query": query, "type": "suggestion"},
                        "captured_at": now,
                    })
        except Exception:
            pass

        return signals

    @staticmethod
    def _days_ago_rfc(days: int) -> str:
        from datetime import datetime, timedelta, timezone
        dt = datetime.now(timezone.utc) - timedelta(days=days)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
