"""
George's state machine.
Defines all cycle phases and the current execution state.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class CyclePhase(str, Enum):
    IDLE = "idle"
    CYCLE_START = "cycle_start"
    TREND_FETCH = "trend_fetch"
    TREND_ANALYZE = "trend_analyze"
    METRICS_PULL = "metrics_pull"
    FEEDBACK_ANALYZE = "feedback_analyze"
    STRATEGY_SELECT = "strategy_select"
    CONTENT_GENERATE = "content_generate"
    CONTENT_VALIDATE = "content_validate"
    VIDEO_PIPELINE = "video_pipeline"
    SCHEDULE_PUBLISH = "schedule_publish"
    PUBLISH_EXECUTE = "publish_execute"
    CYCLE_COMPLETE = "cycle_complete"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class AgentState:
    cycle_id: Optional[str] = None
    cycle_type: str = "weekly"                    # weekly|daily
    phase: CyclePhase = CyclePhase.IDLE
    strategic_prompt: Optional[str] = None

    # Data collected during cycle
    trend_posts: dict[str, list] = field(default_factory=dict)      # platform -> posts
    trend_report: Optional[Any] = None
    comparisons: dict[str, Any] = field(default_factory=dict)       # platform -> CycleComparison
    weekly_plan: dict[str, list] = field(default_factory=dict)      # platform -> [SelectedNarrative]
    generated_content: list[dict] = field(default_factory=list)     # ready-to-publish posts
    video_bundles: list[dict] = field(default_factory=list)         # video file paths
    scheduled_posts: list[dict] = field(default_factory=list)       # posts with timestamps
    published_results: list[dict] = field(default_factory=list)     # publish outcomes

    # Error tracking
    errors: list[dict] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)

    # Metrics
    posts_generated: int = 0
    posts_published: int = 0
    posts_failed: int = 0
    api_calls_made: int = 0
    llm_tokens_used: int = 0

    def transition(self, new_phase: CyclePhase) -> None:
        self.phase = new_phase

    def record_error(self, component: str, error: str, fatal: bool = False) -> None:
        self.errors.append({
            "component": component,
            "error": error,
            "fatal": fatal,
            "phase": self.phase.value,
        })

    def increment_retry(self, key: str) -> int:
        self.retry_counts[key] = self.retry_counts.get(key, 0) + 1
        return self.retry_counts[key]

    def to_summary(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "cycle_type": self.cycle_type,
            "posts_generated": self.posts_generated,
            "posts_published": self.posts_published,
            "posts_failed": self.posts_failed,
            "api_calls_made": self.api_calls_made,
            "llm_tokens_used": self.llm_tokens_used,
            "errors_count": len(self.errors),
            "phases_completed": self.phase.value,
        }
