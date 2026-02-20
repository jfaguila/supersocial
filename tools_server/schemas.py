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
        description="Clave Anthropic temporal para el chat (si no está en el .env). Se usa solo en memoria, nunca se persiste.",
    )


class ChatResponse(BaseModel):
    reply: str
    model: str = "claude-opus-4-6"
