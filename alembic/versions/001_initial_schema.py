"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_cycles",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("cycle_type", sa.String(20), nullable=False),
        sa.Column("started_at", sa.BigInteger()),
        sa.Column("completed_at", sa.BigInteger()),
        sa.Column("status", sa.String(20), default="running"),
        sa.Column("strategic_prompt", sa.Text()),
        sa.Column("summary", JSONB()),
        sa.Column("error_log", JSONB()),
    )

    op.create_table(
        "posts_history",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("content_text", sa.Text()),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("hook_text", sa.Text()),
        sa.Column("emotional_tone", sa.String(50)),
        sa.Column("narrative_type", sa.String(50)),
        sa.Column("authority_angle", sa.String(50)),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("scheduled_at", sa.BigInteger()),
        sa.Column("published_at", sa.BigInteger()),
        sa.Column("cycle_id", UUID(as_uuid=False), sa.ForeignKey("agent_cycles.id")),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )
    op.create_index("ix_posts_history_platform", "posts_history", ["platform"])
    op.create_index("ix_posts_history_content_hash", "posts_history", ["content_hash"])
    op.create_index("ix_posts_history_status", "posts_history", ["status"])

    op.create_table(
        "performance_metrics",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("post_id", UUID(as_uuid=False), sa.ForeignKey("posts_history.id"), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("measured_at", sa.BigInteger()),
        sa.Column("window_hours", sa.Integer(), nullable=False),
        sa.Column("impressions", sa.BigInteger(), default=0),
        sa.Column("reach", sa.BigInteger(), default=0),
        sa.Column("likes", sa.BigInteger(), default=0),
        sa.Column("comments", sa.BigInteger(), default=0),
        sa.Column("shares", sa.BigInteger(), default=0),
        sa.Column("saves", sa.BigInteger(), default=0),
        sa.Column("profile_visits", sa.BigInteger(), default=0),
        sa.Column("watch_time_avg", sa.Float()),
        sa.Column("retention_rate", sa.Float()),
        sa.Column("engagement_rate", sa.Float()),
        sa.Column("virality_score", sa.Float()),
    )
    op.create_index("ix_performance_metrics_post_id", "performance_metrics", ["post_id"])

    op.create_table(
        "hook_patterns",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("pattern_text", sa.Text(), nullable=False),
        sa.Column("pattern_type", sa.String(50)),
        sa.Column("avg_engagement", sa.Float(), default=0.0),
        sa.Column("use_count", sa.Integer(), default=0),
        sa.Column("win_rate", sa.Float(), default=0.0),
        sa.Column("platforms", sa.String(100)),
        sa.Column("last_used_at", sa.BigInteger()),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    op.create_table(
        "emotional_triggers",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("trigger_name", sa.String(100), nullable=False),
        sa.Column("trigger_type", sa.String(50)),
        sa.Column("description", sa.Text()),
        sa.Column("avg_engagement", sa.Float(), default=0.0),
        sa.Column("use_count", sa.Integer(), default=0),
        sa.Column("win_rate", sa.Float(), default=0.0),
        sa.Column("best_platform", sa.String(20)),
        sa.Column("best_content_type", sa.String(30)),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    op.create_table(
        "growth_metrics",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("follower_count", sa.BigInteger(), default=0),
        sa.Column("follower_delta", sa.BigInteger(), default=0),
        sa.Column("avg_reach", sa.BigInteger(), default=0),
        sa.Column("avg_engagement", sa.Float(), default=0.0),
        sa.Column("top_post_id", UUID(as_uuid=False), sa.ForeignKey("posts_history.id")),
        sa.Column("worst_post_id", UUID(as_uuid=False), sa.ForeignKey("posts_history.id")),
        sa.Column("posts_published", sa.Integer(), default=0),
        sa.Column("cycle_id", UUID(as_uuid=False), sa.ForeignKey("agent_cycles.id")),
        sa.Column("created_at", sa.BigInteger()),
        sa.UniqueConstraint("platform", "week_start", name="uq_growth_platform_week"),
    )

    op.create_table(
        "strategy_weights",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("weight_key", sa.String(100), nullable=False),
        sa.Column("weight_value", sa.Float(), nullable=False, default=1.0),
        sa.Column("updated_at", sa.BigInteger()),
        sa.Column("updated_reason", sa.Text()),
        sa.UniqueConstraint("platform", "weight_key", name="uq_strategy_platform_key"),
    )

    op.create_table(
        "agent_logs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("cycle_id", UUID(as_uuid=False), sa.ForeignKey("agent_cycles.id")),
        sa.Column("logged_at", sa.BigInteger()),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("component", sa.String(50), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("payload", JSONB()),
        sa.Column("duration_ms", sa.Integer()),
    )
    op.create_index("ix_agent_logs_cycle_id", "agent_logs", ["cycle_id"])


def downgrade() -> None:
    op.drop_table("agent_logs")
    op.drop_table("strategy_weights")
    op.drop_table("growth_metrics")
    op.drop_table("emotional_triggers")
    op.drop_table("hook_patterns")
    op.drop_table("performance_metrics")
    op.drop_table("posts_history")
    op.drop_table("agent_cycles")
