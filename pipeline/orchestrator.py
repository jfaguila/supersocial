"""
Pipeline orchestrator — 3 clean workflows.

This is the brain of the 5-layer architecture.
Instead of 20 scattered flows, there are exactly 3:

  Workflow 1: capture_signals  — Capa 1
  Workflow 2: generate_content — Capa 2 + 3
  Workflow 3: publish_approved — Capa 4 + 5

Each workflow is independently triggerable via:
  - n8n webhooks
  - REST API endpoints
  - Scheduled cron jobs
  - George agent cycles
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from content.llm_client import LLMClient
from integrations.metricool import MetricoolClient
from memory.models import ContentDraft, TrendSignal
from pipeline.content_generator import ContentGenerator
from pipeline.trend_scorer import TrendScorer
from signals.aggregator import SignalAggregator


@dataclass
class WorkflowResult:
    """Unified result for any workflow execution."""
    workflow: str
    status: str               # ok | partial | error
    items_processed: int = 0
    items_created: int = 0
    errors: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    started_at: int = 0
    completed_at: int = 0

    @property
    def duration_ms(self) -> int:
        return (self.completed_at - self.started_at) * 1000 if self.completed_at else 0

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "status": self.status,
            "items_processed": self.items_processed,
            "items_created": self.items_created,
            "errors": self.errors,
            "details": self.details,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


class PipelineOrchestrator:
    """Orchestrates the 3 core workflows of the content pipeline."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        metricool: Optional[MetricoolClient] = None,
    ):
        settings = get_settings()
        self.llm = llm or LLMClient()
        self.metricool = metricool or MetricoolClient(
            api_token=getattr(settings, "metricool_api_token", ""),
            user_token=getattr(settings, "metricool_user_token", ""),
        )
        self.settings = settings

    # ────────────────────────────────────────────────────────────
    # WORKFLOW 1: Capture Signals (Capa 1)
    # ────────────────────────────────────────────────────────────

    async def capture_signals(self, session: AsyncSession) -> WorkflowResult:
        """Fetch signals from all external sources and save to DB.

        Triggered by: n8n daily cron, or POST /pipeline/capture
        """
        result = WorkflowResult(workflow="capture_signals", started_at=int(time.time()))

        try:
            aggregator = SignalAggregator(
                geo=getattr(self.settings, "signal_geo", "US"),
                youtube_api_key=getattr(self.settings, "youtube_api_key", ""),
                niches=self.settings.niches,
            )
            signals = await aggregator.capture(session)
            result.items_created = len(signals)
            result.status = "ok"
            result.details = {
                "sources": list({s.source for s in signals}),
                "keywords_sample": [s.keyword for s in signals[:5]],
            }
        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))

        result.completed_at = int(time.time())
        return result

    async def capture_from_webhook(
        self, session: AsyncSession, payload: list[dict]
    ) -> WorkflowResult:
        """Persist signals pushed from n8n or external systems.

        Triggered by: POST /pipeline/signals (n8n webhook)
        """
        result = WorkflowResult(workflow="capture_signals_webhook", started_at=int(time.time()))

        try:
            aggregator = SignalAggregator(niches=self.settings.niches)
            signals = await aggregator.capture_from_webhook(session, payload)
            result.items_created = len(signals)
            result.status = "ok"
        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))

        result.completed_at = int(time.time())
        return result

    # ────────────────────────────────────────────────────────────
    # WORKFLOW 2: Generate Content (Capa 2 + 3)
    # ────────────────────────────────────────────────────────────

    async def generate_content(
        self,
        session: AsyncSession,
        min_score: float = 60.0,
        max_signals: int = 5,
        platforms: Optional[list[str]] = None,
    ) -> WorkflowResult:
        """Score raw signals with AI, then generate content for top opportunities.

        Triggered by: n8n after capture, or POST /pipeline/generate
        """
        result = WorkflowResult(workflow="generate_content", started_at=int(time.time()))

        try:
            # Step 1: Score raw signals (Capa 2)
            scorer = TrendScorer(llm=self.llm)
            scored_count = await scorer.score_batch(session)
            result.details["signals_scored"] = scored_count

            # Step 2: Get top opportunities
            top_signals = await scorer.get_top_opportunities(
                session, min_score=min_score, limit=max_signals
            )
            result.items_processed = len(top_signals)

            if not top_signals:
                result.status = "ok"
                result.details["note"] = "No signals met the minimum score threshold"
                result.completed_at = int(time.time())
                return result

            # Step 3: Generate content for each platform (Capa 3)
            generator = ContentGenerator(
                llm=self.llm,
                platforms=platforms or ["instagram", "tiktok", "linkedin", "twitter"],
                language=self.settings.content_languages.split(",")[0].strip(),
            )
            drafts = await generator.generate_from_signals(session, top_signals)
            result.items_created = len(drafts)
            result.status = "ok"
            result.details["platforms"] = list({d.platform for d in drafts})
            result.details["drafts_by_platform"] = {}
            for d in drafts:
                result.details["drafts_by_platform"][d.platform] = (
                    result.details["drafts_by_platform"].get(d.platform, 0) + 1
                )

        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))

        result.completed_at = int(time.time())
        return result

    # ────────────────────────────────────────────────────────────
    # WORKFLOW 3: Publish Approved (Capa 4 + 5)
    # ────────────────────────────────────────────────────────────

    async def publish_approved(self, session: AsyncSession) -> WorkflowResult:
        """Send approved drafts to Metricool for scheduling.

        Triggered by: n8n after manual review, or POST /pipeline/publish
        """
        result = WorkflowResult(workflow="publish_approved", started_at=int(time.time()))

        try:
            # Fetch all approved drafts
            query = (
                select(ContentDraft)
                .where(ContentDraft.status == "approved")
                .order_by(ContentDraft.created_at.asc())
            )
            rows = await session.execute(query)
            drafts = list(rows.scalars().all())
            result.items_processed = len(drafts)

            if not drafts:
                result.status = "ok"
                result.details["note"] = "No approved drafts to publish"
                result.completed_at = int(time.time())
                return result

            now = int(time.time())
            published = 0
            failed = 0

            for draft in drafts:
                scheduled_time = draft.scheduled_at or (now + 3600)  # default: 1 hour from now

                if self.metricool.is_configured():
                    # Send to Metricool
                    metricool_result = await self.metricool.schedule_post(
                        platform=draft.platform,
                        content=draft.content_text,
                        scheduled_at=scheduled_time,
                    )

                    if metricool_result.get("status") == "scheduled":
                        draft.status = "scheduled"
                        draft.metricool_id = metricool_result.get("id", "")
                        draft.scheduled_at = scheduled_time
                        draft.updated_at = now
                        published += 1
                    else:
                        draft.status = "failed"
                        draft.reviewer_note = metricool_result.get("error", "Unknown error")
                        draft.updated_at = now
                        failed += 1
                        result.errors.append(
                            f"{draft.platform}: {metricool_result.get('error', '')}"
                        )
                else:
                    # No Metricool — mark as scheduled (manual publish)
                    draft.status = "scheduled"
                    draft.scheduled_at = scheduled_time
                    draft.updated_at = now
                    published += 1

            await session.flush()
            result.items_created = published
            result.status = "ok" if failed == 0 else "partial"
            result.details["published"] = published
            result.details["failed"] = failed

        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))

        result.completed_at = int(time.time())
        return result

    # ────────────────────────────────────────────────────────────
    # REVIEW helpers (Capa 4)
    # ────────────────────────────────────────────────────────────

    async def review_draft(
        self,
        session: AsyncSession,
        draft_id: str,
        approved: bool,
        note: str = "",
        scheduled_at: Optional[int] = None,
    ) -> dict:
        """Approve or reject a content draft."""
        result = await session.execute(
            select(ContentDraft).where(ContentDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            return {"error": "Draft not found", "draft_id": draft_id}

        now = int(time.time())
        draft.status = "approved" if approved else "rejected"
        draft.reviewer_note = note
        draft.reviewed_at = now
        draft.updated_at = now
        if scheduled_at and approved:
            draft.scheduled_at = scheduled_at

        await session.flush()

        return {
            "draft_id": draft_id,
            "action": "approved" if approved else "rejected",
            "note": note,
            "timestamp": now,
        }

    async def get_drafts_for_review(
        self,
        session: AsyncSession,
        platform: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get all drafts pending review."""
        q = (
            select(ContentDraft)
            .where(ContentDraft.status == "pending_review")
            .order_by(ContentDraft.created_at.desc())
            .limit(limit)
        )
        if platform:
            q = q.where(ContentDraft.platform == platform)

        result = await session.execute(q)
        drafts = result.scalars().all()

        return [
            {
                "draft_id": d.id,
                "platform": d.platform,
                "content_type": d.content_type,
                "content_preview": (d.content_text or "")[:300],
                "hook": d.hook_text,
                "hashtags": d.hashtags,
                "emotional_tone": d.emotional_tone,
                "char_count": d.char_count,
                "signal_id": d.signal_id,
                "created_at": d.created_at,
            }
            for d in drafts
        ]

    async def get_trends_summary(
        self, session: AsyncSession, limit: int = 20
    ) -> list[dict]:
        """Get analyzed trends for dashboard display."""
        result = await session.execute(
            select(TrendSignal)
            .where(TrendSignal.status.in_(["analyzed", "used"]))
            .order_by(TrendSignal.ai_score.desc())
            .limit(limit)
        )
        signals = result.scalars().all()

        return [
            {
                "signal_id": s.id,
                "keyword": s.keyword,
                "source": s.source,
                "ai_score": s.ai_score,
                "ideal_client": s.ideal_client,
                "recommended_format": s.recommended_format,
                "viral_angle": s.viral_angle,
                "volume": s.volume,
                "status": s.status,
                "captured_at": s.captured_at,
            }
            for s in signals
        ]
