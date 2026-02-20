"""
Google Trends signal source.

Uses the unofficial pytrends API to fetch daily trending searches
and interest-over-time data for configured niches.
"""
import time
from typing import Optional

import httpx


class GoogleTrendsSource:
    """Fetch trending searches from Google Trends via public endpoints."""

    DAILY_TRENDS_URL = "https://trends.google.com/trends/api/dailytrends"
    REALTIME_URL = "https://trends.google.com/trending/rss"

    def __init__(self, geo: str = "US", hl: str = "en-US"):
        self.geo = geo
        self.hl = hl

    async def fetch_daily(self, categories: Optional[list[str]] = None) -> list[dict]:
        """Return a list of SignalRecord dicts from Google daily trends.

        Each record has the shape expected by TrendSignal:
            source, keyword, volume, trending_score, region, category, raw_data
        """
        signals: list[dict] = []
        now = int(time.time())

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    self.DAILY_TRENDS_URL,
                    params={"hl": self.hl, "tz": "-300", "geo": self.geo, "ns": 15},
                )
                # Google prepends ")]}'" to the JSON response
                raw_text = resp.text.lstrip(")]}'")
                import json
                data = json.loads(raw_text)

                days = data.get("default", {}).get("trendingSearchesDays", [])
                for day in days[:2]:  # last 2 days
                    for item in day.get("trendingSearches", []):
                        title = item.get("title", {}).get("query", "")
                        traffic = item.get("formattedTraffic", "0")
                        # Parse "100K+" -> 100000
                        volume = self._parse_traffic(traffic)

                        signals.append({
                            "source": "google_trends",
                            "keyword": title,
                            "volume": volume,
                            "trending_score": min(100.0, volume / 1000),
                            "region": self.geo,
                            "category": self._match_category(title, categories),
                            "raw_data": {
                                "traffic": traffic,
                                "related": [
                                    q.get("query", "")
                                    for q in item.get("relatedQueries", [])
                                ],
                                "articles": [
                                    a.get("url", "")
                                    for a in item.get("articles", [])[:3]
                                ],
                            },
                            "captured_at": now,
                        })
        except Exception:
            # Non-critical — other sources can compensate
            pass

        return signals

    def _parse_traffic(self, traffic: str) -> int:
        """Convert '200K+' or '1M+' to integer."""
        cleaned = traffic.replace("+", "").replace(",", "").strip()
        multiplier = 1
        if cleaned.endswith("K"):
            multiplier = 1_000
            cleaned = cleaned[:-1]
        elif cleaned.endswith("M"):
            multiplier = 1_000_000
            cleaned = cleaned[:-1]
        try:
            return int(float(cleaned) * multiplier)
        except (ValueError, TypeError):
            return 0

    def _match_category(self, keyword: str, categories: Optional[list[str]]) -> str:
        if not categories:
            return "general"
        kw_lower = keyword.lower()
        for cat in categories:
            if cat.lower() in kw_lower:
                return cat
        return "general"
