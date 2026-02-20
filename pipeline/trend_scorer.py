"""
Capa 2 — AI trend analysis and scoring.

Takes raw TrendSignal rows, sends them to LLM for structured analysis,
and writes back: ai_score, ideal_client, recommended_format, viral_angle.
"""
import time
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from content.llm_client import LLMClient
from memory.models import TrendSignal

SCORER_SYSTEM_PROMPT = """You are a strategic analyst for a B2B AI agency.
You receive raw trend signals (keywords, volumes, sources) and must evaluate each one.

For EACH trend, output a JSON object with:
- "ai_score": integer 0-100 (opportunity level for our agency)
- "ideal_client": string (who would benefit from content about this)
- "recommended_format": one of "video", "carousel", "thread", "post", "story"
- "viral_angle": string (1-2 sentence hook/angle to make content go viral)

Focus on B2B AI agency opportunities. Score higher if:
- The trend intersects AI, automation, or digital transformation
- There's a clear pain point we can address
- The topic has controversy or emotional charge
- It's timely (news-driven) rather than evergreen

Score lower if:
- Too generic (e.g., "weather today")
- No business angle
- Already saturated topic with no fresh angle

Return valid JSON: {"trends": [{"keyword": "...", "ai_score": ..., ...}]}"""


class TrendScorer:
    """Score raw signals using LLM analysis."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    async def score_batch(
        self, session: AsyncSession, batch_size: int = 30
    ) -> int:
        """Score unanalyzed signals. Returns number scored."""
        # Fetch raw (unscored) signals
        result = await session.execute(
            select(TrendSignal)
            .where(TrendSignal.status == "raw")
            .order_by(TrendSignal.trending_score.desc())
            .limit(batch_size)
        )
        signals = list(result.scalars().all())
        if not signals:
            return 0

        # Build prompt with all signals
        trend_list = "\n".join(
            f"- [{s.source}] \"{s.keyword}\" (volume: {s.volume}, score: {s.trending_score}, category: {s.category})"
            for s in signals
        )

        user_prompt = f"""Analyze these {len(signals)} trend signals and score each one:

{trend_list}

Return JSON with scores for ALL trends listed above."""

        response = await self.llm.generate_json(SCORER_SYSTEM_PROMPT, user_prompt)

        # Parse and update
        scored_trends = response.get("trends", [])
        scored_map: dict[str, dict] = {}
        for t in scored_trends:
            key = t.get("keyword", "").strip().lower()
            if key:
                scored_map[key] = t

        now = int(time.time())
        count = 0

        for signal in signals:
            key = signal.keyword.strip().lower()
            scoring = scored_map.get(key, {})

            signal.ai_score = scoring.get("ai_score", 30.0)
            signal.ideal_client = scoring.get("ideal_client", "")
            signal.recommended_format = scoring.get("recommended_format", "post")
            signal.viral_angle = scoring.get("viral_angle", "")
            signal.analyzed_at = now
            signal.status = "analyzed"
            count += 1

        await session.flush()
        return count

    async def get_top_opportunities(
        self, session: AsyncSession, min_score: float = 60.0, limit: int = 10
    ) -> list[TrendSignal]:
        """Return top-scoring analyzed signals ready for content generation."""
        result = await session.execute(
            select(TrendSignal)
            .where(TrendSignal.status == "analyzed")
            .where(TrendSignal.ai_score >= min_score)
            .order_by(TrendSignal.ai_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
