"""
George — The Autonomous Content Engine Agent.

George is a task-oriented OpenClaw-style agent that orchestrates
the full content production lifecycle for SuperSocial.

He is NOT a content creator. He is a systems operator.
"""
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config.credentials import CredentialManager
from config.settings import get_settings

from memory.repository import Repository
from memory.session import _SessionFactory

from data_layer.twitter_connector import TwitterConnector
from data_layer.tiktok_connector import TikTokConnector
from data_layer.linkedin_connector import LinkedInConnector
from data_layer.instagram_connector import InstagramConnector

from analysis.engagement import EngagementAnalyzer
from analysis.hook_detector import HookDetector
from analysis.emotion_cluster import EmotionCluster
from analysis.format_recognizer import FormatRecognizer
from analysis.trend_detector import TrendDetector

from strategy.narrative_selector import NarrativeSelector
from strategy.emotion_selector import EmotionSelector
from strategy.authority_selector import AuthoritySelector
from strategy.distribution_planner import DistributionPlanner

from content.llm_client import LLMClient
from content.prompt_builder import PromptBuilder
from content.platform_formatter import PlatformFormatter
from content.deduplication import DeduplicationGuard

from video.script_formatter import ScriptFormatter
from video.srt_generator import SRTGenerator
from video.render_exporter import RenderExporter

from feedback.metrics_puller import MetricsPuller
from feedback.cycle_comparator import CycleComparator
from feedback.strategy_updater import StrategyUpdater

from .state import AgentState, CyclePhase
from .logger import GeorgeLogger


PLATFORM_CONNECTORS = {
    "twitter": TwitterConnector,
    "tiktok": TikTokConnector,
    "linkedin": LinkedInConnector,
    "instagram": InstagramConnector,
}


class GeorgeAgent:
    """
    George's main agent loop.

    Usage:
        agent = GeorgeAgent()
        await agent.run_weekly_cycle(strategic_prompt="Focus on financial freedom this week")
        await agent.run_daily_cycle()
    """

    def __init__(self):
        self._settings = get_settings()
        self._creds = CredentialManager()
        self._state = AgentState()

        # Analysis tools
        self._engagement_analyzer = EngagementAnalyzer()
        self._hook_detector = HookDetector()
        self._emotion_cluster = EmotionCluster()
        self._format_recognizer = FormatRecognizer()
        self._trend_detector = TrendDetector()

        # Content tools
        self._llm = LLMClient()
        self._prompt_builder = PromptBuilder()
        self._formatter = PlatformFormatter()
        self._script_formatter = ScriptFormatter()
        self._render_exporter = RenderExporter()

    async def run_weekly_cycle(self, strategic_prompt: Optional[str] = None) -> dict:
        """Full 7-day content cycle. Returns cycle summary."""
        async with _SessionFactory() as session:
            repo = Repository(session)
            logger = GeorgeLogger(repo)
            return await self._execute_weekly_cycle(repo, logger, strategic_prompt)

    async def run_daily_cycle(self) -> dict:
        """Lightweight daily cycle: publish scheduled posts + pull metrics."""
        async with _SessionFactory() as session:
            repo = Repository(session)
            logger = GeorgeLogger(repo)
            return await self._execute_daily_cycle(repo, logger)

    # ------------------------------------------------------------------ #
    # WEEKLY CYCLE
    # ------------------------------------------------------------------ #

    async def _execute_weekly_cycle(
        self,
        repo: Repository,
        logger: GeorgeLogger,
        strategic_prompt: Optional[str],
    ) -> dict:
        state = AgentState(cycle_type="weekly", strategic_prompt=strategic_prompt)

        # --- PHASE: CYCLE_START ---
        state.transition(CyclePhase.CYCLE_START)
        cycle = await repo.create_cycle("weekly", strategic_prompt)
        state.cycle_id = cycle.id
        logger.set_cycle_id(cycle.id)
        await logger.info("agent", "weekly_cycle_started", {"strategic_prompt": strategic_prompt})

        platforms = self._creds.get_configured_platforms()
        if not platforms:
            await logger.warn("agent", "no_platforms_configured")
            await repo.complete_cycle(cycle.id, {"warning": "no platforms configured"})
            return {"status": "no_platforms"}

        try:
            # --- PHASE: METRICS_PULL (pull previous cycle data first) ---
            state.transition(CyclePhase.METRICS_PULL)
            await logger.info("feedback", "pulling_7day_metrics")
            puller = MetricsPuller(repo)
            metric_counts = await puller.pull_7day_metrics(cycle.id)
            await logger.info("feedback", "metrics_pulled", metric_counts)

            # --- PHASE: FEEDBACK_ANALYZE ---
            state.transition(CyclePhase.FEEDBACK_ANALYZE)
            comparator = CycleComparator(repo)
            updater = StrategyUpdater(repo)

            for platform in platforms:
                comparison = await comparator.compare(platform, cycle.id)
                state.comparisons[platform] = comparison
                weight_changes = await updater.update(comparison)
                await logger.info(
                    "feedback",
                    "strategy_weights_updated",
                    {
                        "platform": platform,
                        "engagement_delta": comparison.engagement_delta_pct,
                        "weight_changes": len(weight_changes),
                        "recommendations": comparison.recommendations,
                    },
                )

            # --- PHASE: TREND_FETCH ---
            state.transition(CyclePhase.TREND_FETCH)
            niches = self._settings.niches
            all_posts = []

            for platform in platforms:
                await logger.info("data_layer", f"fetching_trends_{platform}")
                connector_class = PLATFORM_CONNECTORS.get(platform)
                if not connector_class:
                    continue
                try:
                    async with connector_class() as connector:
                        posts = await connector.fetch_trending_posts(niches, limit=50)
                        state.trend_posts[platform] = posts
                        all_posts.extend(posts)
                        state.api_calls_made += 1
                        await logger.info("data_layer", "trends_fetched", {
                            "platform": platform, "count": len(posts)
                        })
                except Exception as e:
                    state.record_error("data_layer", str(e))
                    await logger.error("data_layer", f"trend_fetch_failed_{platform}", {"error": str(e)})

            # --- PHASE: TREND_ANALYZE ---
            state.transition(CyclePhase.TREND_ANALYZE)
            if all_posts:
                trend_report = self._trend_detector.detect(all_posts)
                state.trend_report = trend_report
                eng_scores = self._engagement_analyzer.analyze(all_posts)
                hook_analyses = self._hook_detector.analyze_batch(all_posts)
                emotion_analyses = self._emotion_cluster.analyze_batch(all_posts)

                await logger.info("analysis", "trend_analysis_complete", {
                    "total_posts": len(all_posts),
                    "top_keywords": [kw for kw, _ in trend_report.top_keywords[:5]],
                    "top_hooks": self._hook_detector.summarize_patterns(hook_analyses),
                    "top_emotions": self._emotion_cluster.dominant_emotions(emotion_analyses),
                })

                # Persist learned hook patterns
                for ha in hook_analyses[:20]:
                    if ha.hook_type != "unknown":
                        eng_score = next(
                            (s.normalized_score for s in eng_scores if s.post_id == ha.post_id),
                            0.5,
                        )
                        await repo.upsert_hook_pattern(ha.hook_text, ha.hook_type, eng_score)

            # --- PHASE: STRATEGY_SELECT ---
            state.transition(CyclePhase.STRATEGY_SELECT)
            narrative_selector = NarrativeSelector(repo)
            emotion_selector = EmotionSelector(repo)
            authority_selector = AuthoritySelector()
            distribution_planner = DistributionPlanner(repo)

            weekly_plan = await narrative_selector.select_weekly_plan(
                platforms=platforms,
                days=7,
                strategic_prompt=strategic_prompt,
            )
            state.weekly_plan = weekly_plan

            schedule = await distribution_planner.plan_week(
                platforms=platforms,
                posts_per_platform_per_day=self._settings.max_posts_per_platform_per_day,
            )
            await logger.info("strategy", "weekly_plan_selected", {
                "platforms": platforms,
                "total_slots": sum(len(slots) for slots in schedule.values()),
            })

            # --- PHASE: CONTENT_GENERATE ---
            state.transition(CyclePhase.CONTENT_GENERATE)
            dedup_guard = DeduplicationGuard(repo)
            generated = []

            for platform, narratives in weekly_plan.items():
                platform_slots = schedule.get(platform, [])

                for i, narrative in enumerate(narratives):
                    if i >= len(platform_slots):
                        break
                    slot = platform_slots[i]

                    emotion = await emotion_selector.select(platform, narrative.narrative_key)
                    authority = authority_selector.select(platform, narrative.narrative_key)
                    prompt = self._prompt_builder.build(
                        platform=platform,
                        narrative=narrative,
                        emotion=emotion,
                        authority=authority,
                        trend_report=state.trend_report,
                        niches=niches,
                        strategic_prompt=strategic_prompt,
                        content_type=narrative.content_type,
                    )

                    try:
                        llm_response = await self._llm.generate(
                            system_prompt=prompt.system_prompt,
                            user_prompt=prompt.user_prompt,
                            temperature=0.82,
                            max_tokens=800,
                        )
                        state.llm_tokens_used += llm_response.prompt_tokens + llm_response.completion_tokens

                        raw_content = llm_response.content.strip()

                        # Format for platform
                        formatted = self._formatter.format(platform, raw_content)
                        if not formatted.is_valid:
                            await logger.warn("content", "format_invalid", {
                                "platform": platform, "warnings": formatted.warnings
                            })
                            continue

                        # Deduplication check
                        is_dup, reason = await dedup_guard.is_duplicate(formatted.text)
                        if is_dup:
                            await logger.warn("content", "duplicate_detected", {
                                "platform": platform, "reason": reason
                            })
                            continue

                        content_hash = dedup_guard.register(formatted.text)

                        # Save to DB
                        post = await repo.create_post(
                            platform=platform,
                            content_hash=content_hash,
                            content_text=formatted.text,
                            content_type=narrative.content_type,
                            hook_text=self._hook_detector.extract_hook(formatted.text),
                            emotional_tone=emotion.emotion_key,
                            narrative_type=narrative.narrative_key,
                            authority_angle=authority.angle_key,
                            status="scheduled",
                            scheduled_at=slot.unix_timestamp,
                            cycle_id=cycle.id,
                        )

                        generated.append({
                            "post_id": post.id,
                            "platform": platform,
                            "content_type": narrative.content_type,
                            "scheduled_at": slot.unix_timestamp,
                            "is_video": narrative.content_type == "video_script",
                        })
                        state.posts_generated += 1

                    except Exception as e:
                        state.record_error("content_generate", str(e))
                        await logger.error("content", "generation_failed", {
                            "platform": platform, "error": str(e)
                        })

            state.generated_content = generated
            await logger.info("content", "content_generation_complete", {
                "posts_generated": state.posts_generated,
                "platforms": list(weekly_plan.keys()),
            })

            # --- PHASE: VIDEO_PIPELINE ---
            state.transition(CyclePhase.VIDEO_PIPELINE)
            video_posts = [p for p in generated if p.get("is_video")]

            for vp in video_posts:
                try:
                    # Re-fetch content text from DB
                    post_record = await repo.session.get(
                        __import__("memory.models", fromlist=["PostHistory"]).PostHistory,
                        vp["post_id"]
                    )
                    if not post_record:
                        continue

                    script = self._script_formatter.format(
                        raw_script=post_record.content_text,
                        platform=vp["platform"],
                        title=f"{vp['platform'].capitalize()} Video",
                    )
                    bundle_paths = self._render_exporter.export_bundle(
                        script=script,
                        output_dir=f"/data/video_exports/{cycle.id}",
                    )
                    state.video_bundles.append({
                        "post_id": vp["post_id"],
                        "platform": vp["platform"],
                        "paths": bundle_paths,
                    })
                    await logger.info("video", "video_bundle_exported", {
                        "post_id": vp["post_id"],
                        "files": list(bundle_paths.keys()),
                    })
                except Exception as e:
                    state.record_error("video_pipeline", str(e))
                    await logger.error("video", "video_export_failed", {"error": str(e)})

            # --- PHASE: PUBLISH_EXECUTE (only in full-auto mode) ---
            if not self._settings.is_semi_autonomous:
                state.transition(CyclePhase.PUBLISH_EXECUTE)
                await self._publish_due_posts(repo, logger, state, platforms)
            else:
                await logger.info("agent", "semi_autonomous_mode_pause", {
                    "action_required": "Human review required before publish",
                    "posts_ready": state.posts_generated,
                })

            # --- PHASE: CYCLE_COMPLETE ---
            state.transition(CyclePhase.CYCLE_COMPLETE)
            summary = state.to_summary()
            await repo.complete_cycle(cycle.id, summary)
            await logger.info("agent", "weekly_cycle_complete", summary)
            await session.commit()
            return summary

        except Exception as e:
            state.record_error("agent", str(e), fatal=True)
            await logger.error("agent", "weekly_cycle_fatal_error", {"error": str(e), "phase": state.phase.value})
            try:
                await repo.complete_cycle(cycle.id, state.to_summary(), error_log={"errors": state.errors})
                await session.commit()
            except Exception:
                pass
            raise

    # ------------------------------------------------------------------ #
    # DAILY CYCLE
    # ------------------------------------------------------------------ #

    async def _execute_daily_cycle(self, repo: Repository, logger: GeorgeLogger) -> dict:
        state = AgentState(cycle_type="daily")
        cycle = await repo.create_cycle("daily")
        state.cycle_id = cycle.id
        logger.set_cycle_id(cycle.id)
        await logger.info("agent", "daily_cycle_started")

        platforms = self._creds.get_configured_platforms()

        try:
            # Pull 24h metrics for yesterday's posts
            puller = MetricsPuller(repo)
            yesterday_ts = int(time.time()) - 86400
            posts = await repo.get_published_posts_since(yesterday_ts)
            await logger.info("feedback", "daily_metrics_check", {"posts_to_check": len(posts)})

            # Publish any due scheduled posts
            await self._publish_due_posts(repo, logger, state, platforms)

            summary = state.to_summary()
            await repo.complete_cycle(cycle.id, summary)
            await logger.info("agent", "daily_cycle_complete", summary)
            return summary

        except Exception as e:
            await logger.error("agent", "daily_cycle_error", {"error": str(e)})
            await repo.complete_cycle(cycle.id, state.to_summary(), error_log={"error": str(e)})
            raise

    # ------------------------------------------------------------------ #
    # PUBLISH HELPER
    # ------------------------------------------------------------------ #

    async def _publish_due_posts(
        self,
        repo: Repository,
        logger: GeorgeLogger,
        state: AgentState,
        platforms: list[str],
    ) -> None:
        now = int(time.time())

        for platform in platforms:
            due_posts = await repo.get_posts_for_platform(platform, status="scheduled")
            due_posts = [p for p in due_posts if p.scheduled_at and p.scheduled_at <= now]

            connector_class = PLATFORM_CONNECTORS.get(platform)
            if not connector_class:
                continue

            async with connector_class() as connector:
                for post in due_posts:
                    try:
                        result = await connector.publish_post({
                            "text": post.content_text,
                            "media_type": post.content_type.upper() if post.content_type != "text" else None,
                        })
                        await repo.update_post_status(
                            post.id, "published", external_id=result.get("external_id")
                        )
                        state.posts_published += 1
                        state.api_calls_made += 1
                        await logger.info("publish", "post_published", {
                            "post_id": post.id,
                            "platform": platform,
                            "external_id": result.get("external_id"),
                        })
                    except Exception as e:
                        await repo.update_post_status(post.id, "failed")
                        state.posts_failed += 1
                        state.record_error("publish", str(e))
                        await logger.error("publish", "publish_failed", {
                            "post_id": post.id,
                            "platform": platform,
                            "error": str(e),
                        })
