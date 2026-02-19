"""
Data access repository — all DB operations go through here.
Keeps SQL out of business logic.
"""
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AgentCycle,
    AgentLog,
    EmotionalTrigger,
    GrowthMetric,
    HookPattern,
    PerformanceMetric,
    PostHistory,
    StrategyWeight,
)


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Agent Cycles
    # ------------------------------------------------------------------ #

    async def create_cycle(self, cycle_type: str, strategic_prompt: Optional[str] = None) -> AgentCycle:
        cycle = AgentCycle(cycle_type=cycle_type, strategic_prompt=strategic_prompt)
        self.session.add(cycle)
        await self.session.flush()
        return cycle

    async def complete_cycle(self, cycle_id: str, summary: dict, error_log: Optional[dict] = None) -> None:
        await self.session.execute(
            update(AgentCycle)
            .where(AgentCycle.id == cycle_id)
            .values(
                status="failed" if error_log else "completed",
                completed_at=int(datetime.utcnow().timestamp()),
                summary=summary,
                error_log=error_log,
            )
        )

    async def get_last_cycle(self, cycle_type: str) -> Optional[AgentCycle]:
        result = await self.session.execute(
            select(AgentCycle)
            .where(AgentCycle.cycle_type == cycle_type)
            .where(AgentCycle.status == "completed")
            .order_by(AgentCycle.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #

    async def log(
        self,
        cycle_id: str,
        level: str,
        component: str,
        action: str,
        payload: Optional[dict] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        log_entry = AgentLog(
            cycle_id=cycle_id,
            level=level,
            component=component,
            action=action,
            payload=payload,
            duration_ms=duration_ms,
        )
        self.session.add(log_entry)
        await self.session.flush()

    # ------------------------------------------------------------------ #
    # Posts
    # ------------------------------------------------------------------ #

    async def create_post(self, **kwargs) -> PostHistory:
        post = PostHistory(**kwargs)
        self.session.add(post)
        await self.session.flush()
        return post

    async def get_post_by_hash(self, content_hash: str) -> Optional[PostHistory]:
        result = await self.session.execute(
            select(PostHistory).where(PostHistory.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def update_post_status(
        self, post_id: str, status: str, external_id: Optional[str] = None
    ) -> None:
        values: dict[str, Any] = {
            "status": status,
            "updated_at": int(datetime.utcnow().timestamp()),
        }
        if external_id:
            values["external_id"] = external_id
        if status == "published":
            values["published_at"] = int(datetime.utcnow().timestamp())
        await self.session.execute(
            update(PostHistory).where(PostHistory.id == post_id).values(**values)
        )

    async def get_posts_for_platform(self, platform: str, status: str = "scheduled") -> list[PostHistory]:
        result = await self.session.execute(
            select(PostHistory)
            .where(PostHistory.platform == platform)
            .where(PostHistory.status == status)
            .order_by(PostHistory.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_published_posts_since(self, since_ts: int) -> list[PostHistory]:
        result = await self.session.execute(
            select(PostHistory)
            .where(PostHistory.status == "published")
            .where(PostHistory.published_at >= since_ts)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # Performance Metrics
    # ------------------------------------------------------------------ #

    async def save_metrics(self, **kwargs) -> PerformanceMetric:
        metric = PerformanceMetric(**kwargs)
        self.session.add(metric)
        await self.session.flush()
        return metric

    async def get_metrics_for_post(self, post_id: str, window_hours: Optional[int] = None) -> list[PerformanceMetric]:
        q = select(PerformanceMetric).where(PerformanceMetric.post_id == post_id)
        if window_hours:
            q = q.where(PerformanceMetric.window_hours == window_hours)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # Hook Patterns
    # ------------------------------------------------------------------ #

    async def upsert_hook_pattern(self, pattern_text: str, pattern_type: str, engagement: float) -> HookPattern:
        result = await self.session.execute(
            select(HookPattern).where(HookPattern.pattern_text == pattern_text)
        )
        hook = result.scalar_one_or_none()
        if hook:
            hook.use_count += 1
            hook.avg_engagement = (hook.avg_engagement * (hook.use_count - 1) + engagement) / hook.use_count
            hook.updated_at = int(datetime.utcnow().timestamp())
        else:
            hook = HookPattern(
                pattern_text=pattern_text,
                pattern_type=pattern_type,
                avg_engagement=engagement,
                use_count=1,
            )
            self.session.add(hook)
        await self.session.flush()
        return hook

    async def get_top_hooks(self, limit: int = 10) -> list[HookPattern]:
        result = await self.session.execute(
            select(HookPattern).order_by(HookPattern.avg_engagement.desc()).limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # Emotional Triggers
    # ------------------------------------------------------------------ #

    async def get_top_triggers(self, platform: Optional[str] = None, limit: int = 10) -> list[EmotionalTrigger]:
        q = select(EmotionalTrigger).order_by(EmotionalTrigger.avg_engagement.desc())
        if platform:
            q = q.where(EmotionalTrigger.best_platform == platform)
        result = await self.session.execute(q.limit(limit))
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # Strategy Weights
    # ------------------------------------------------------------------ #

    async def get_weight(self, platform: str, weight_key: str) -> float:
        result = await self.session.execute(
            select(StrategyWeight)
            .where(StrategyWeight.platform == platform)
            .where(StrategyWeight.weight_key == weight_key)
        )
        row = result.scalar_one_or_none()
        return row.weight_value if row else 1.0

    async def set_weight(self, platform: str, weight_key: str, value: float, reason: str = "") -> None:
        result = await self.session.execute(
            select(StrategyWeight)
            .where(StrategyWeight.platform == platform)
            .where(StrategyWeight.weight_key == weight_key)
        )
        row = result.scalar_one_or_none()
        now = int(datetime.utcnow().timestamp())
        if row:
            row.weight_value = value
            row.updated_at = now
            row.updated_reason = reason
        else:
            row = StrategyWeight(
                platform=platform,
                weight_key=weight_key,
                weight_value=value,
                updated_reason=reason,
            )
            self.session.add(row)
        await self.session.flush()

    async def get_all_weights(self, platform: str) -> dict[str, float]:
        result = await self.session.execute(
            select(StrategyWeight).where(StrategyWeight.platform == platform)
        )
        return {row.weight_key: row.weight_value for row in result.scalars().all()}

    # ------------------------------------------------------------------ #
    # Growth Metrics
    # ------------------------------------------------------------------ #

    async def save_growth_metric(self, **kwargs) -> GrowthMetric:
        metric = GrowthMetric(**kwargs)
        self.session.add(metric)
        await self.session.flush()
        return metric

    async def get_growth_history(self, platform: str, weeks: int = 4) -> list[GrowthMetric]:
        result = await self.session.execute(
            select(GrowthMetric)
            .where(GrowthMetric.platform == platform)
            .order_by(GrowthMetric.week_start.desc())
            .limit(weeks)
        )
        return list(result.scalars().all())
