"""
YouTube Factory — Database models.

Tables:
    youtube_channels    — Channel configuration and credentials
    youtube_characters  — AI character visual/voice identity
    youtube_videos      — Produced video tracking and metadata
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from memory.models import Base


def _uuid():
    return str(uuid.uuid4())


class YouTubeChannel(Base):
    __tablename__ = "youtube_channels"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False)
    youtube_channel_id = Column(String(50), unique=True, index=True)

    # Niche and content config
    niche = Column(String(100), nullable=False)  # e.g. "artificial_intelligence"
    language = Column(String(10), default="en")
    tone = Column(String(100), default="professional, authoritative")
    target_duration_minutes = Column(Integer, default=5)  # 3-8 min
    videos_per_week = Column(Integer, default=3)

    # YouTube API credentials (per channel / Google Cloud project)
    google_client_id = Column(Text, default="")
    google_client_secret = Column(Text, default="")
    google_refresh_token = Column(Text, default="")

    # Publishing config
    publish_schedule_cron = Column(String(50), default="0 14 * * 1,3,5")  # MWF 14:00
    privacy_status = Column(String(20), default="unlisted")  # unlisted → public
    default_category_id = Column(String(5), default="28")  # Science & Technology
    made_for_kids = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    total_videos_published = Column(Integer, default=0)
    total_views = Column(BigInteger, default=0)
    subscriber_count = Column(BigInteger, default=0)

    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))

    # Relationships
    character_id = Column(UUID(as_uuid=False), ForeignKey("youtube_characters.id"))
    character = relationship("YouTubeCharacter", back_populates="channels")
    videos = relationship("YouTubeVideo", back_populates="channel", lazy="dynamic")


class YouTubeCharacter(Base):
    __tablename__ = "youtube_characters"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False)  # e.g. "George"

    # Visual identity — injected into every image generation prompt
    physical_description = Column(Text, nullable=False)
    # e.g. "30-year-old male, short dark hair, light stubble, sharp jawline, warm brown eyes"

    clothing_description = Column(Text, default="")
    # e.g. "dark fitted t-shirt, minimalist silver watch"

    art_style = Column(Text, default="photorealistic, cinematic lighting, shallow depth of field, 4K")

    color_palette = Column(Text, default="deep blues, warm oranges, dark backgrounds")

    default_environment = Column(Text, default="modern minimalist office, large window with city view")

    negative_prompt = Column(
        Text,
        default="cartoon, anime, deformed, blurry, low quality, multiple people, text, watermark",
    )

    # Voice identity
    elevenlabs_voice_id = Column(String(50), default="")
    voice_stability = Column(Float, default=0.5)
    voice_similarity_boost = Column(Float, default=0.75)
    voice_style = Column(Float, default=0.4)
    voice_speaking_rate = Column(Float, default=1.0)

    # Metadata
    is_active = Column(Boolean, default=True)
    videos_generated = Column(Integer, default=0)
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))

    # Relationships
    channels = relationship("YouTubeChannel", back_populates="character")


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    channel_id = Column(UUID(as_uuid=False), ForeignKey("youtube_channels.id"), nullable=False, index=True)

    # YouTube external data
    youtube_video_id = Column(String(20), unique=True, index=True)
    youtube_url = Column(String(100))

    # Content
    topic = Column(Text, nullable=False)
    script_json = Column(JSONB)  # Full structured script with scenes
    title = Column(String(100))
    description = Column(Text)
    tags = Column(JSONB)  # list[str]
    hashtags = Column(JSONB)  # list[str]
    category_id = Column(String(5))

    # Files
    video_file_path = Column(Text)
    thumbnail_file_path = Column(Text)
    voiceover_file_path = Column(Text)
    srt_file_path = Column(Text)

    # Technical metadata
    duration_seconds = Column(Float)
    resolution = Column(String(20), default="1920x1080")
    scenes_count = Column(Integer, default=5)
    file_size_bytes = Column(BigInteger)

    # Status lifecycle: draft → rendering → rendered → uploading → published → failed
    status = Column(String(20), default="draft", index=True)
    error_message = Column(Text)

    # AI disclosure
    is_ai_generated = Column(Boolean, default=True)

    # Publishing
    scheduled_publish_at = Column(BigInteger)  # Unix timestamp
    published_at = Column(BigInteger)
    privacy_status = Column(String(20), default="unlisted")

    # Performance (pulled from YouTube Analytics)
    views = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments_count = Column(BigInteger, default=0)
    watch_time_hours = Column(Float, default=0.0)
    avg_view_duration_seconds = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)  # Click-through rate (thumbnail)

    # Cycle tracking
    cycle_id = Column(UUID(as_uuid=False), ForeignKey("agent_cycles.id"), index=True)

    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))

    # Relationships
    channel = relationship("YouTubeChannel", back_populates="videos")
