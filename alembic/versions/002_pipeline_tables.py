"""Add pipeline tables (trend_signals, content_drafts)

Revision ID: 002
Revises: 001
Create Date: 2026-02-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── trend_signals ─────────────────────────────────────────
    op.create_table(
        "trend_signals",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("volume", sa.BigInteger(), default=0),
        sa.Column("trending_score", sa.Float(), default=0.0),
        sa.Column("region", sa.String(10), default="global"),
        sa.Column("category", sa.String(100)),
        sa.Column("raw_data", JSONB()),
        sa.Column("captured_at", sa.BigInteger()),
        # AI analysis fields
        sa.Column("ai_score", sa.Float()),
        sa.Column("ideal_client", sa.String(255)),
        sa.Column("recommended_format", sa.String(50)),
        sa.Column("viral_angle", sa.Text()),
        sa.Column("analyzed_at", sa.BigInteger()),
        sa.Column("status", sa.String(20), default="raw"),
    )
    op.create_index("ix_trend_signals_source", "trend_signals", ["source"])
    op.create_index("ix_trend_signals_keyword", "trend_signals", ["keyword"])
    op.create_index("ix_trend_signals_status", "trend_signals", ["status"])

    # ── content_drafts ────────────────────────────────────────
    op.create_table(
        "content_drafts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("signal_id", UUID(as_uuid=False), sa.ForeignKey("trend_signals.id")),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("hook_text", sa.Text()),
        sa.Column("hashtags", sa.Text()),
        sa.Column("emotional_tone", sa.String(50)),
        sa.Column("narrative_type", sa.String(50)),
        sa.Column("char_count", sa.Integer(), default=0),
        # Video (for TikTok/YouTube/Reels)
        sa.Column("video_path", sa.String(500)),
        sa.Column("video_srt_path", sa.String(500)),
        sa.Column("video_status", sa.String(20)),
        # Review workflow
        sa.Column("status", sa.String(20), default="generated"),
        sa.Column("reviewer_note", sa.Text()),
        sa.Column("reviewed_at", sa.BigInteger()),
        # Publishing
        sa.Column("metricool_id", sa.String(255)),
        sa.Column("external_id", sa.String(255)),
        sa.Column("scheduled_at", sa.BigInteger()),
        sa.Column("published_at", sa.BigInteger()),
        # Timestamps
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )
    op.create_index("ix_content_drafts_signal_id", "content_drafts", ["signal_id"])
    op.create_index("ix_content_drafts_platform", "content_drafts", ["platform"])
    op.create_index("ix_content_drafts_status", "content_drafts", ["status"])


def downgrade() -> None:
    op.drop_table("content_drafts")
    op.drop_table("trend_signals")
