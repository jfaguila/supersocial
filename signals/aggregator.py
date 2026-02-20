"""
Signal aggregator — Capa 1 orchestrator.

Runs all signal sources in parallel and deduplicates results
before persisting to the trend_signals table.
"""
import asyncio
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from memory.models import TrendSignal
from signals.google_trends import GoogleTrendsSource
from signals.rss_reader import RSSSource
from signals.youtube_trends import YouTubeTrendsSource


class SignalAggregator:
    """Collect signals from all external sources and persist them."""

    def __init__(
        self,
        geo: str = "US",
        youtube_api_key: str = "",
        rss_feeds: Optional[list[dict[str, str]]] = None,
        niches: Optional[list[str]] = None,
    ):
        self.google = GoogleTrendsSource(geo=geo)
        self.rss = RSSSource(feeds=rss_feeds)
        self.youtube = YouTubeTrendsSource(api_key=youtube_api_key, region_code=geo)
        self.niches = niches or []

    async def capture(self, session: AsyncSession) -> list[TrendSignal]:
        """Run all sources, deduplicate, and save to DB. Returns created rows."""
        # Fetch from all sources concurrently
        results = await asyncio.gather(
            self.google.fetch_daily(categories=self.niches),
            self.rss.fetch(),
            self.youtube.fetch(niches=self.niches),
            return_exceptions=True,
        )

        all_signals: list[dict] = []
        for result in results:
            if isinstance(result, list):
                all_signals.extend(result)

        # Deduplicate by normalized keyword
        seen: set[str] = set()
        unique: list[dict] = []
        for sig in all_signals:
            key = sig["keyword"].strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(sig)

        # Persist
        created: list[TrendSignal] = []
        for sig in unique:
            row = TrendSignal(
                source=sig["source"],
                keyword=sig["keyword"],
                volume=sig.get("volume", 0),
                trending_score=sig.get("trending_score", 0.0),
                region=sig.get("region", "global"),
                category=sig.get("category", "general"),
                raw_data=sig.get("raw_data"),
                captured_at=sig.get("captured_at", int(time.time())),
                status="raw",
            )
            session.add(row)
            created.append(row)

        await session.flush()
        return created

    async def capture_from_webhook(
        self, session: AsyncSession, payload: list[dict]
    ) -> list[TrendSignal]:
        """Persist signals pushed from n8n or external webhooks."""
        created: list[TrendSignal] = []
        now = int(time.time())

        for item in payload:
            row = TrendSignal(
                source=item.get("source", "n8n_webhook"),
                keyword=item.get("keyword", ""),
                volume=item.get("volume", 0),
                trending_score=item.get("trending_score", 50.0),
                region=item.get("region", "global"),
                category=item.get("category", "general"),
                raw_data=item.get("raw_data"),
                captured_at=now,
                status="raw",
            )
            session.add(row)
            created.append(row)

        await session.flush()
        return created
