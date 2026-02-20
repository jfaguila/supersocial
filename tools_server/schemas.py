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


# ─── Pipeline (5-layer architecture) ─────────────────────────────────────

class SignalWebhookItem(BaseModel):
    """Single signal from n8n or external source."""
    keyword: str = Field(..., description="Keyword o tema detectado")
    source: str = Field("n8n_webhook", description="Fuente: google_trends|rss|youtube|twitter|n8n_webhook")
    volume: int = Field(0, description="Volumen de búsqueda o views")
    trending_score: float = Field(50.0, description="Score de tendencia 0-100")
    region: str = Field("global", description="Código de país o 'global'")
    category: str = Field("general", description="Categoría: tech, business, ai, etc.")
    raw_data: Optional[dict] = Field(None, description="Datos originales de la fuente")


class SignalWebhookRequest(BaseModel):
    """Payload from n8n webhook with one or more signals."""
    signals: list[SignalWebhookItem] = Field(..., description="Lista de señales detectadas")


class PipelineWorkflowResponse(BaseModel):
    """Unified response for any pipeline workflow."""
    workflow: str
    status: str
    items_processed: int = 0
    items_created: int = 0
    errors: list[str] = []
    details: dict = {}
    started_at: int = 0
    completed_at: int = 0
    duration_ms: int = 0


class GenerateContentRequest(BaseModel):
    """Parameters for content generation workflow."""
    min_score: float = Field(60.0, description="Score mínimo de oportunidad (0-100)")
    max_signals: int = Field(5, description="Máximo de señales a procesar")
    platforms: Optional[list[str]] = Field(
        None,
        description="Plataformas destino. Por defecto: instagram, tiktok, linkedin, twitter",
    )


class ReviewDraftRequest(BaseModel):
    """Approve or reject a content draft."""
    approved: bool = Field(..., description="True = aprobar, False = rechazar")
    note: str = Field("", description="Nota del revisor")
    scheduled_at: Optional[int] = Field(
        None, description="Unix timestamp para programar (solo si aprobado)"
    )


class DraftListResponse(BaseModel):
    """List of content drafts for review."""
    drafts: list[dict]
    total: int


class TrendListResponse(BaseModel):
    """List of analyzed trend signals."""
    trends: list[dict]
    total: int
