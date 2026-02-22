"""
Pydantic schemas para el Tool Server.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class RunCycleRequest(BaseModel):
    strategic_prompt: Optional[str] = Field(
        None,
        description="Instrucción semanal opcional. Ej: 'Foco en anti-sistema esta semana'",
        example="Enfoca en libertad financiera y cuestiona el sistema educativo",
    )
    dry_run: bool = Field(
        False,
        description="Si True, genera contenido pero no publica. Útil para revisar primero.",
    )


class RunCycleResponse(BaseModel):
    job_id: str
    status: str
    cycle_type: str
    message: str
    started_at: int


class AgentStatusResponse(BaseModel):
    is_running: bool
    current_phase: Optional[str]
    current_job_id: Optional[str]
    last_cycle_summary: Optional[dict]
    checked_at: int


class PendingPostsResponse(BaseModel):
    posts: list[dict]
    total: int


class PlatformMetricsResponse(BaseModel):
    platform: str
    weeks_of_data: int
    history: list[dict]


class CycleSummaryResponse(BaseModel):
    cycle_id: str
    cycle_type: str
    status: str
    strategic_prompt: Optional[str]
    summary: dict
    started_at: Optional[int]
    completed_at: Optional[int]


class ApprovePostRequest(BaseModel):
    approved: bool
    note: Optional[str] = None


# ─── API Health ────────────────────────────────────────────

class PlatformApiStatus(BaseModel):
    platform: str
    configured: bool
    missing_keys: list[str]
    can_read: bool        # puede leer/buscar contenido
    can_publish: bool     # puede publicar
    notes: Optional[str] = None


class ApiHealthResponse(BaseModel):
    overall_ready: bool
    platforms: list[PlatformApiStatus]
    llm_configured: bool
    llm_model: str
    database_configured: bool
    redis_configured: bool
    warnings: list[str]
    setup_guide_url: str = "/docs/api-setup"


# ─── Chat Asistente ────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="Historial de la conversación")
    chat_key: Optional[str] = Field(
        None,
        description="Clave Gemini temporal para el chat (si no está en el .env). Se usa solo en memoria, nunca se persiste.",
    )


class ChatResponse(BaseModel):
    reply: str
    model: str = "claude-opus-4-6"


# ─── YouTube Factory ─────────────────────────────────────────────────────

class YouTubeChannelSummary(BaseModel):
    channel_id: str
    name: str
    niche: str
    language: str
    tone: str
    videos_per_week: int
    target_duration_minutes: int
    privacy_status: str
    is_active: bool
    total_videos_published: int
    total_views: int
    subscriber_count: int
    character_name: Optional[str] = None
    created_at: Optional[int] = None


class YouTubeChannelsResponse(BaseModel):
    channels: list[YouTubeChannelSummary]
    total: int


class YouTubeCharacterSummary(BaseModel):
    character_id: str
    name: str
    physical_description: str
    art_style: str
    color_palette: str
    voice_id: str
    is_active: bool
    videos_generated: int
    channels_count: int = 0


class YouTubeCharactersResponse(BaseModel):
    characters: list[YouTubeCharacterSummary]
    total: int


class YouTubeVideoSummary(BaseModel):
    video_id: str
    channel_id: str
    channel_name: Optional[str] = None
    topic: str
    title: Optional[str] = None
    youtube_url: Optional[str] = None
    status: str
    duration_seconds: Optional[float] = None
    scenes_count: int = 0
    views: int = 0
    likes: int = 0
    comments_count: int = 0
    ctr: float = 0.0
    created_at: Optional[int] = None
    published_at: Optional[int] = None


class YouTubeVideosResponse(BaseModel):
    videos: list[YouTubeVideoSummary]
    total: int


class YouTubeStatsResponse(BaseModel):
    total_channels: int
    active_channels: int
    total_characters: int
    total_videos: int
    published_videos: int
    total_views: int
    total_likes: int
    avg_ctr: float
    videos_by_status: dict[str, int]
