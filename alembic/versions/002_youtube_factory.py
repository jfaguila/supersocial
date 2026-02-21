"""YouTube Factory tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- YouTube Characters ---
    op.create_table(
        "youtube_characters",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("physical_description", sa.Text(), nullable=False),
        sa.Column("clothing_description", sa.Text(), server_default=""),
        sa.Column("art_style", sa.Text(), server_default="photorealistic, cinematic lighting, shallow depth of field, 4K"),
        sa.Column("color_palette", sa.Text(), server_default="deep blues, warm oranges, dark backgrounds"),
        sa.Column("default_environment", sa.Text(), server_default="modern minimalist office, large window with city view"),
        sa.Column("negative_prompt", sa.Text(), server_default="cartoon, anime, deformed, blurry, low quality, multiple people, text, watermark"),
        sa.Column("elevenlabs_voice_id", sa.String(50), server_default=""),
        sa.Column("voice_stability", sa.Float(), server_default="0.5"),
        sa.Column("voice_similarity_boost", sa.Float(), server_default="0.75"),
        sa.Column("voice_style", sa.Float(), server_default="0.4"),
        sa.Column("voice_speaking_rate", sa.Float(), server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("videos_generated", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    # --- YouTube Channels ---
    op.create_table(
        "youtube_channels",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("youtube_channel_id", sa.String(50), unique=True),
        sa.Column("niche", sa.String(100), nullable=False),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("tone", sa.String(100), server_default="professional, authoritative"),
        sa.Column("target_duration_minutes", sa.Integer(), server_default="5"),
        sa.Column("videos_per_week", sa.Integer(), server_default="3"),
        sa.Column("google_client_id", sa.Text(), server_default=""),
        sa.Column("google_client_secret", sa.Text(), server_default=""),
        sa.Column("google_refresh_token", sa.Text(), server_default=""),
        sa.Column("publish_schedule_cron", sa.String(50), server_default="0 14 * * 1,3,5"),
        sa.Column("privacy_status", sa.String(20), server_default="unlisted"),
        sa.Column("default_category_id", sa.String(5), server_default="28"),
        sa.Column("made_for_kids", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("total_videos_published", sa.Integer(), server_default="0"),
        sa.Column("total_views", sa.BigInteger(), server_default="0"),
        sa.Column("subscriber_count", sa.BigInteger(), server_default="0"),
        sa.Column("character_id", UUID(as_uuid=False), sa.ForeignKey("youtube_characters.id")),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )
    op.create_index("ix_youtube_channels_channel_id", "youtube_channels", ["youtube_channel_id"])

    # --- YouTube Videos ---
    op.create_table(
        "youtube_videos",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("channel_id", UUID(as_uuid=False), sa.ForeignKey("youtube_channels.id"), nullable=False),
        sa.Column("youtube_video_id", sa.String(20), unique=True),
        sa.Column("youtube_url", sa.String(100)),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("script_json", JSONB()),
        sa.Column("title", sa.String(100)),
        sa.Column("description", sa.Text()),
        sa.Column("tags", JSONB()),
        sa.Column("hashtags", JSONB()),
        sa.Column("category_id", sa.String(5)),
        sa.Column("video_file_path", sa.Text()),
        sa.Column("thumbnail_file_path", sa.Text()),
        sa.Column("voiceover_file_path", sa.Text()),
        sa.Column("srt_file_path", sa.Text()),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("resolution", sa.String(20), server_default="1920x1080"),
        sa.Column("scenes_count", sa.Integer(), server_default="5"),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("error_message", sa.Text()),
        sa.Column("is_ai_generated", sa.Boolean(), server_default="true"),
        sa.Column("scheduled_publish_at", sa.BigInteger()),
        sa.Column("published_at", sa.BigInteger()),
        sa.Column("privacy_status", sa.String(20), server_default="unlisted"),
        sa.Column("views", sa.BigInteger(), server_default="0"),
        sa.Column("likes", sa.BigInteger(), server_default="0"),
        sa.Column("comments_count", sa.BigInteger(), server_default="0"),
        sa.Column("watch_time_hours", sa.Float(), server_default="0.0"),
        sa.Column("avg_view_duration_seconds", sa.Float(), server_default="0.0"),
        sa.Column("ctr", sa.Float(), server_default="0.0"),
        sa.Column("cycle_id", UUID(as_uuid=False), sa.ForeignKey("agent_cycles.id")),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )
    op.create_index("ix_youtube_videos_channel_id", "youtube_videos", ["channel_id"])
    op.create_index("ix_youtube_videos_status", "youtube_videos", ["status"])
    op.create_index("ix_youtube_videos_youtube_id", "youtube_videos", ["youtube_video_id"])


def downgrade() -> None:
    op.drop_table("youtube_videos")
    op.drop_table("youtube_channels")
    op.drop_table("youtube_characters")
