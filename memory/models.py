"""
SQLAlchemy ORM models matching the database schema.

Tables:
  Original (George engine):
    - agent_cycles, agent_logs, posts_history, performance_metrics,
      hook_patterns, emotional_triggers, growth_metrics, strategy_weights

  Pipeline (5-layer architecture):
    - trend_signals   — Capa 1: raw signals captured from external sources
    - content_drafts  — Capa 3-4: generated content awaiting review
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


class PostHistory(Base):
    __tablename__ = "posts_history"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    platform = Column(String(20), nullable=False, index=True)
    external_id = Column(String(255), index=True)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    content_text = Column(Text)
    content_type = Column(String(30), nullable=False)
    hook_text = Column(Text)
    emotional_tone = Column(String(50))
    narrative_type = Column(String(50))
    authority_angle = Column(String(50))
    status = Column(String(20), default="draft", index=True)
    scheduled_at = Column(BigInteger)  # Unix timestamp
    published_at = Column(BigInteger)
    cycle_id = Column(UUID(as_uuid=False), ForeignKey("agent_cycles.id"), index=True)
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))

    metrics = relationship("PerformanceMetric", back_populates="post", lazy="dynamic")
    cycle = relationship("AgentCycle", back_populates="posts")


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    post_id = Column(UUID(as_uuid=False), ForeignKey("posts_history.id"), nullable=False, index=True)
    platform = Column(String(20), nullable=False)
    measured_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    window_hours = Column(Integer, nullable=False)  # 24, 48, 168
    impressions = Column(BigInteger, default=0)
    reach = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)
    shares = Column(BigInteger, default=0)
    saves = Column(BigInteger, default=0)
    profile_visits = Column(BigInteger, default=0)
    watch_time_avg = Column(Float)
    retention_rate = Column(Float)
    engagement_rate = Column(Float)
    virality_score = Column(Float)

    post = relationship("PostHistory", back_populates="metrics")


class HookPattern(Base):
    __tablename__ = "hook_patterns"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pattern_text = Column(Text, nullable=False)
    pattern_type = Column(String(50))  # question|shock|promise|story|contrast
    avg_engagement = Column(Float, default=0.0)
    use_count = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    platforms = Column(String(100))  # comma-separated
    last_used_at = Column(BigInteger)
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))


class EmotionalTrigger(Base):
    __tablename__ = "emotional_triggers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    trigger_name = Column(String(100), nullable=False)
    trigger_type = Column(String(50))  # fear|aspiration|anger|identity|hope
    description = Column(Text)
    avg_engagement = Column(Float, default=0.0)
    use_count = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    best_platform = Column(String(20))
    best_content_type = Column(String(30))
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))


class GrowthMetric(Base):
    __tablename__ = "growth_metrics"
    __table_args__ = (UniqueConstraint("platform", "week_start"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    platform = Column(String(20), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    follower_count = Column(BigInteger, default=0)
    follower_delta = Column(BigInteger, default=0)
    avg_reach = Column(BigInteger, default=0)
    avg_engagement = Column(Float, default=0.0)
    top_post_id = Column(UUID(as_uuid=False), ForeignKey("posts_history.id"))
    worst_post_id = Column(UUID(as_uuid=False), ForeignKey("posts_history.id"))
    posts_published = Column(Integer, default=0)
    cycle_id = Column(UUID(as_uuid=False), ForeignKey("agent_cycles.id"))
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))


class StrategyWeight(Base):
    __tablename__ = "strategy_weights"
    __table_args__ = (UniqueConstraint("platform", "weight_key"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    platform = Column(String(20), nullable=False, index=True)
    weight_key = Column(String(100), nullable=False)
    weight_value = Column(Float, nullable=False, default=1.0)
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_reason = Column(Text)


class AgentCycle(Base):
    __tablename__ = "agent_cycles"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    cycle_type = Column(String(20), nullable=False)  # weekly|daily
    started_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    completed_at = Column(BigInteger)
    status = Column(String(20), default="running")  # running|completed|failed
    strategic_prompt = Column(Text)
    summary = Column(JSONB)
    error_log = Column(JSONB)

    posts = relationship("PostHistory", back_populates="cycle", lazy="dynamic")
    logs = relationship("AgentLog", back_populates="cycle", lazy="dynamic")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    cycle_id = Column(UUID(as_uuid=False), ForeignKey("agent_cycles.id"), index=True)
    logged_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    level = Column(String(10), nullable=False)  # INFO|WARN|ERROR|DEBUG
    component = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    payload = Column(JSONB)
    duration_ms = Column(Integer)

    cycle = relationship("AgentCycle", back_populates="logs")


# ================================================================== #
# PIPELINE — 5-Layer Architecture
# ================================================================== #


class TrendSignal(Base):
    """Capa 1: Raw signal captured from an external source.

    Sources: google_trends, rss, youtube, twitter, tiktok, n8n_webhook.
    Each row = one detected trend or keyword opportunity.
    """
    __tablename__ = "trend_signals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    source = Column(String(50), nullable=False, index=True)      # google_trends|rss|youtube|twitter|n8n_webhook
    keyword = Column(String(255), nullable=False, index=True)
    volume = Column(BigInteger, default=0)                        # search volume / view count
    trending_score = Column(Float, default=0.0)                   # 0-100 raw popularity score
    region = Column(String(10), default="global")                 # country code or "global"
    category = Column(String(100))                                # tech, business, ai, etc.
    raw_data = Column(JSONB)                                      # original payload from source
    captured_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))

    # Capa 2: AI analysis fields (filled after scoring)
    ai_score = Column(Float)                                      # 0-100 opportunity score from LLM
    ideal_client = Column(String(255))                            # B2B, solopreneurs, etc.
    recommended_format = Column(String(50))                       # video|carousel|thread|post
    viral_angle = Column(Text)                                    # suggested hook / angle
    analyzed_at = Column(BigInteger)
    status = Column(String(20), default="raw", index=True)       # raw|analyzed|used|discarded

    drafts = relationship("ContentDraft", back_populates="signal", lazy="dynamic")


class ContentDraft(Base):
    """Capa 3-4: Generated content piece awaiting human review.

    Lifecycle: generated -> pending_review -> approved -> scheduled -> published
               generated -> pending_review -> rejected
    """
    __tablename__ = "content_drafts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    signal_id = Column(UUID(as_uuid=False), ForeignKey("trend_signals.id"), index=True)
    platform = Column(String(20), nullable=False, index=True)    # instagram|tiktok|linkedin|twitter|youtube
    content_type = Column(String(30), nullable=False)             # post|script|thread|carousel|idea
    content_text = Column(Text, nullable=False)
    hook_text = Column(Text)
    hashtags = Column(Text)                                       # comma-separated
    emotional_tone = Column(String(50))
    narrative_type = Column(String(50))
    char_count = Column(Integer, default=0)

    # Review workflow (Capa 4)
    status = Column(String(20), default="generated", index=True)  # generated|pending_review|approved|rejected|scheduled|published|failed
    reviewer_note = Column(Text)
    reviewed_at = Column(BigInteger)

    # Publishing (Capa 5)
    metricool_id = Column(String(255))                            # ID in Metricool after scheduling
    external_id = Column(String(255))                             # post ID on the platform
    scheduled_at = Column(BigInteger)
    published_at = Column(BigInteger)

    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()))

    signal = relationship("TrendSignal", back_populates="drafts")
