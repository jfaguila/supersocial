"""
SuperSocial Tool Server — expone a George como herramientas REST.

Cualquier agente (OpenClaw, LangChain, CrewAI, etc.) puede llamar
a George a través de estos endpoints HTTP.

Arrancar:
    uvicorn tools_server.main:app --host 0.0.0.0 --port 8000 --reload
"""
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from tools_server.schemas import (
    RunCycleRequest,
    RunCycleResponse,
    AgentStatusResponse,
    PlatformMetricsResponse,
    PendingPostsResponse,
    ApiHealthResponse,
    ApprovePostRequest,
    CycleSummaryResponse,
    ChatRequest,
    ChatResponse,
    SignalWebhookRequest,
    PipelineWorkflowResponse,
    GenerateContentRequest,
    ReviewDraftRequest,
    DraftListResponse,
    TrendListResponse,
)
from tools_server.api_checker import ApiChecker
from tools_server.cycle_runner import BackgroundCycleRunner


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runner = BackgroundCycleRunner()
    app.state.checker = ApiChecker()
    yield


app = FastAPI(
    title="SuperSocial — George Tool Server",
    description="Expone las capacidades del agente George como herramientas REST para OpenClaw.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_DASHBOARD_HTML = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "dashboard", "templates", "index.html",
)


# ─────────────────────────────────────────────────────────────
# DASHBOARD — Panel de control web
# ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def dashboard():
    """Sirve el panel de control interactivo de George."""
    return FileResponse(_DASHBOARD_HTML, media_type="text/html")


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 1 — Ejecutar ciclo semanal completo
# ─────────────────────────────────────────────────────────────

@app.post(
    "/george/run-weekly-cycle",
    response_model=RunCycleResponse,
    summary="Ejecuta el ciclo semanal completo de George",
    tags=["Ciclos"],
)
async def run_weekly_cycle(
    request: RunCycleRequest,
    background_tasks: BackgroundTasks,
):
    """
    George analiza tendencias, genera contenido para 7 días,
    crea scripts de video y programa publicaciones.

    **Parámetros:**
    - `strategic_prompt`: Instrucción opcional para orientar el contenido esta semana.
    - `dry_run`: Si es True, genera contenido pero NO publica.

    **Ejemplo de uso desde OpenClaw:**
    ```json
    {
      "strategic_prompt": "Esta semana foco en libertad financiera y anti-sistema",
      "dry_run": false
    }
    ```
    """
    runner = app.state.runner
    if runner.is_running:
        raise HTTPException(
            status_code=409,
            detail="George ya está ejecutando un ciclo. Espera a que termine."
        )

    job_id = runner.start_weekly(
        strategic_prompt=request.strategic_prompt,
        dry_run=request.dry_run,
        background_tasks=background_tasks,
    )

    return RunCycleResponse(
        job_id=job_id,
        status="started",
        cycle_type="weekly",
        message=f"Ciclo semanal iniciado. Usa GET /george/status para seguir el progreso.",
        started_at=int(time.time()),
    )


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 2 — Ejecutar ciclo diario (publicar posts del día)
# ─────────────────────────────────────────────────────────────

@app.post(
    "/george/run-daily-cycle",
    response_model=RunCycleResponse,
    summary="Publica los posts programados para hoy",
    tags=["Ciclos"],
)
async def run_daily_cycle(background_tasks: BackgroundTasks):
    """
    George publica los posts que estaban programados para hoy
    y recoge métricas de los posts de ayer.
    """
    runner = app.state.runner
    if runner.is_running:
        raise HTTPException(status_code=409, detail="George ya está ocupado.")

    job_id = runner.start_daily(background_tasks=background_tasks)
    return RunCycleResponse(
        job_id=job_id,
        status="started",
        cycle_type="daily",
        message="Ciclo diario iniciado.",
        started_at=int(time.time()),
    )


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 3 — Estado actual de George
# ─────────────────────────────────────────────────────────────

@app.get(
    "/george/status",
    response_model=AgentStatusResponse,
    summary="Estado actual del agente y último ciclo",
    tags=["Estado"],
)
async def get_status():
    """
    Devuelve:
    - Si George está ejecutando un ciclo ahora mismo
    - La fase actual (trend_fetch, content_generate, etc.)
    - Resumen del último ciclo completado
    """
    runner = app.state.runner
    return AgentStatusResponse(
        is_running=runner.is_running,
        current_phase=runner.current_phase,
        current_job_id=runner.current_job_id,
        last_cycle_summary=runner.last_summary,
        checked_at=int(time.time()),
    )


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 4 — Posts pendientes de revisión
# ─────────────────────────────────────────────────────────────

@app.get(
    "/george/posts/pending",
    response_model=PendingPostsResponse,
    summary="Posts generados pendientes de publicación",
    tags=["Contenido"],
)
async def get_pending_posts(platform: Optional[str] = None, limit: int = 20):
    """
    Muestra los posts que George generó y están esperando
    para ser publicados (estado: 'scheduled').

    Útil en modo semi-autónomo para revisar antes de publicar.
    """
    from memory.session import _SessionFactory
    from memory.repository import Repository
    from memory.models import PostHistory
    from sqlalchemy import select

    async with _SessionFactory() as session:
        repo = Repository(session)
        q = select(PostHistory).where(PostHistory.status == "scheduled")
        if platform:
            q = q.where(PostHistory.platform == platform)
        q = q.order_by(PostHistory.scheduled_at.asc()).limit(limit)
        result = await session.execute(q)
        posts = result.scalars().all()

    return PendingPostsResponse(
        posts=[
            {
                "post_id": p.id,
                "platform": p.platform,
                "content_type": p.content_type,
                "preview": (p.content_text or "")[:200],
                "hook": p.hook_text,
                "emotion": p.emotional_tone,
                "narrative": p.narrative_type,
                "scheduled_at": p.scheduled_at,
                "char_count": len(p.content_text or ""),
            }
            for p in posts
        ],
        total=len(posts),
    )


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 5 — Métricas por plataforma
# ─────────────────────────────────────────────────────────────

@app.get(
    "/george/metrics/{platform}",
    response_model=PlatformMetricsResponse,
    summary="Métricas de crecimiento de una plataforma",
    tags=["Métricas"],
)
async def get_platform_metrics(platform: str, weeks: int = 4):
    """
    Histórico de crecimiento: seguidores, engagement, alcance.
    Plataformas: twitter | tiktok | linkedin | instagram
    """
    valid = {"twitter", "tiktok", "linkedin", "instagram"}
    if platform not in valid:
        raise HTTPException(status_code=400, detail=f"Plataforma no válida. Usa: {valid}")

    from memory.session import _SessionFactory
    from memory.repository import Repository

    async with _SessionFactory() as session:
        repo = Repository(session)
        history = await repo.get_growth_history(platform, weeks=weeks)

    return PlatformMetricsResponse(
        platform=platform,
        weeks_of_data=len(history),
        history=[
            {
                "week_start": str(h.week_start),
                "follower_count": h.follower_count,
                "follower_delta": h.follower_delta,
                "avg_engagement": h.avg_engagement,
                "avg_reach": h.avg_reach,
                "posts_published": h.posts_published,
            }
            for h in history
        ],
    )


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 6 — Último ciclo completado
# ─────────────────────────────────────────────────────────────

@app.get(
    "/george/cycles/last",
    response_model=CycleSummaryResponse,
    summary="Resumen del último ciclo completado",
    tags=["Ciclos"],
)
async def get_last_cycle(cycle_type: str = "weekly"):
    """
    Devuelve el resumen del último ciclo: posts generados,
    publicados, fallidos, tokens usados, errores.
    """
    from memory.session import _SessionFactory
    from memory.repository import Repository

    async with _SessionFactory() as session:
        repo = Repository(session)
        cycle = await repo.get_last_cycle(cycle_type)

    if not cycle:
        raise HTTPException(status_code=404, detail="No hay ciclos completados todavía.")

    return CycleSummaryResponse(
        cycle_id=cycle.id,
        cycle_type=cycle.cycle_type,
        status=cycle.status,
        strategic_prompt=cycle.strategic_prompt,
        summary=cycle.summary or {},
        started_at=cycle.started_at,
        completed_at=cycle.completed_at,
    )


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 7 — Aprobar/rechazar post (modo semi-autónomo)
# ─────────────────────────────────────────────────────────────

@app.post(
    "/george/posts/{post_id}/approve",
    summary="Aprobar un post para que George lo publique",
    tags=["Contenido"],
)
async def approve_post(post_id: str, request: ApprovePostRequest):
    """
    En modo semi-autónomo: aprueba o rechaza un post generado.
    - `approved=True` → George lo publica en el siguiente ciclo diario.
    - `approved=False` → Se marca como rechazado, no se publica.
    """
    from memory.session import _SessionFactory
    from memory.repository import Repository

    async with _SessionFactory() as session:
        repo = Repository(session)
        new_status = "scheduled" if request.approved else "rejected"
        await repo.update_post_status(post_id, new_status)

    return {
        "post_id": post_id,
        "action": "approved" if request.approved else "rejected",
        "note": request.note,
        "timestamp": int(time.time()),
    }


# ─────────────────────────────────────────────────────────────
# HERRAMIENTA 8 — Salud de las APIs de plataformas
# ─────────────────────────────────────────────────────────────

@app.get(
    "/george/api-health",
    response_model=ApiHealthResponse,
    summary="Estado de configuración de todas las APIs",
    tags=["Diagnóstico"],
)
async def check_api_health():
    """
    Verifica cuáles APIs están configuradas y cuáles faltan.
    Muestra exactamente qué credenciales faltan por plataforma.
    Útil para saber qué hay que configurar antes de arrancar.
    """
    checker = app.state.checker
    report = checker.check_all()
    return report


# ─────────────────────────────────────────────────────────────
# CHAT — Asistente IA de configuración
# ─────────────────────────────────────────────────────────────

@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat con el asistente IA de configuración",
    tags=["Asistente"],
)
async def chat_endpoint(request: ChatRequest):
    """
    Conversación con el asistente IA que lee y escribe el `.env` automáticamente.

    El usuario puede decirle sus API keys en lenguaje natural y el asistente
    las guarda directamente. Ideal para configurar SuperSocial sin tocar ficheros.

    - `messages`: historial de la conversación [{role, content}]
    - `chat_key`: clave Gemini temporal (si no está en el .env aún)
    """
    from tools_server.chat_handler import chat_with_assistant, resolve_api_key

    api_key = resolve_api_key(request.chat_key)
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail=(
                "No hay clave Gemini disponible. "
                "Pega tu clave de https://aistudio.google.com/apikey en el campo 'Clave del chat' "
                "o añade GEMINI_API_KEY al fichero .env y reinicia."
            ),
        )

    try:
        msgs = [{"role": m.role, "content": m.content} for m in request.messages]
        reply = chat_with_assistant(msgs, api_key)
        return ChatResponse(reply=reply)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error del asistente: {exc}")


# ─────────────────────────────────────────────────────────────
# HEALTHCHECK del servidor
# ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "ok", "agent": "george", "timestamp": int(time.time())}


# ═════════════════════════════════════════════════════════════
# PIPELINE — Arquitectura de 5 capas
# n8n y cualquier orquestador externo conectan aquí.
# ═════════════════════════════════════════════════════════════

# ─── CAPA 1: Captura de señales ─────────────────────────────

@app.post(
    "/pipeline/signals",
    response_model=PipelineWorkflowResponse,
    summary="Recibir señales desde n8n u otro webhook externo",
    tags=["Pipeline"],
)
async def receive_signals(request: SignalWebhookRequest):
    """
    **Webhook para n8n.**

    n8n envía señales capturadas (Google Trends, RSS, YouTube, etc.)
    y SuperSocial las guarda en la base de datos para análisis.

    Ejemplo de payload desde n8n:
    ```json
    {
      "signals": [
        {"keyword": "AI agents 2026", "source": "google_trends", "volume": 150000},
        {"keyword": "OpenAI launches new model", "source": "rss", "category": "ai"}
      ]
    }
    ```
    """
    from memory.session import _SessionFactory
    from pipeline.orchestrator import PipelineOrchestrator

    async with _SessionFactory() as session:
        orch = PipelineOrchestrator()
        payload = [item.model_dump() for item in request.signals]
        result = await orch.capture_from_webhook(session, payload)
        await session.commit()

    return PipelineWorkflowResponse(**result.to_dict())


@app.post(
    "/pipeline/capture",
    response_model=PipelineWorkflowResponse,
    summary="Ejecutar captura automática de señales de todas las fuentes",
    tags=["Pipeline"],
)
async def capture_signals():
    """
    Ejecuta la captura de señales desde todas las fuentes configuradas:
    Google Trends, RSS feeds, YouTube.

    Equivalente a lo que n8n ejecutaría diariamente como cron.
    """
    from memory.session import _SessionFactory
    from pipeline.orchestrator import PipelineOrchestrator

    async with _SessionFactory() as session:
        orch = PipelineOrchestrator()
        result = await orch.capture_signals(session)
        await session.commit()

    return PipelineWorkflowResponse(**result.to_dict())


# ─── CAPA 2+3: Análisis IA + Generación de contenido ───────

@app.post(
    "/pipeline/generate",
    response_model=PipelineWorkflowResponse,
    summary="Analizar tendencias con IA y generar contenido multi-plataforma",
    tags=["Pipeline"],
)
async def generate_content(request: GenerateContentRequest = GenerateContentRequest()):
    """
    **Workflow 2: Análisis + Generación.**

    1. Puntúa las señales crudas con IA (oportunidad, cliente ideal, ángulo viral)
    2. Selecciona las mejores oportunidades (min_score)
    3. Genera contenido para cada plataforma

    Todo el contenido generado queda en estado `pending_review`.
    """
    from memory.session import _SessionFactory
    from pipeline.orchestrator import PipelineOrchestrator

    async with _SessionFactory() as session:
        orch = PipelineOrchestrator()
        result = await orch.generate_content(
            session,
            min_score=request.min_score,
            max_signals=request.max_signals,
            platforms=request.platforms,
        )
        await session.commit()

    return PipelineWorkflowResponse(**result.to_dict())


# ─── CAPA 4: Revisión humana ───────────────────────────────

@app.get(
    "/pipeline/drafts",
    response_model=DraftListResponse,
    summary="Borradores pendientes de revisión",
    tags=["Pipeline"],
)
async def get_drafts(platform: Optional[str] = None, limit: int = 50):
    """
    Devuelve todos los borradores de contenido pendientes de aprobación.
    Aquí es donde el humano revisa, ajusta y decide.
    """
    from memory.session import _SessionFactory
    from pipeline.orchestrator import PipelineOrchestrator

    async with _SessionFactory() as session:
        orch = PipelineOrchestrator()
        drafts = await orch.get_drafts_for_review(session, platform=platform, limit=limit)

    return DraftListResponse(drafts=drafts, total=len(drafts))


@app.post(
    "/pipeline/drafts/{draft_id}/review",
    summary="Aprobar o rechazar un borrador de contenido",
    tags=["Pipeline"],
)
async def review_draft(draft_id: str, request: ReviewDraftRequest):
    """
    **Revisión manual (Capa 4).**

    - `approved=true` → El borrador pasa a estado 'approved', listo para publicar.
    - `approved=false` → Se marca como rechazado, no se publica.

    Opcionalmente incluye `scheduled_at` (unix timestamp) para programar la publicación.
    """
    from memory.session import _SessionFactory
    from pipeline.orchestrator import PipelineOrchestrator

    async with _SessionFactory() as session:
        orch = PipelineOrchestrator()
        result = await orch.review_draft(
            session,
            draft_id=draft_id,
            approved=request.approved,
            note=request.note,
            scheduled_at=request.scheduled_at,
        )
        await session.commit()

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── CAPA 5: Publicación vía Metricool ─────────────────────

@app.post(
    "/pipeline/publish",
    response_model=PipelineWorkflowResponse,
    summary="Publicar borradores aprobados vía Metricool",
    tags=["Pipeline"],
)
async def publish_approved():
    """
    **Workflow 3: Publicación.**

    Envía todos los borradores con estado 'approved' a Metricool
    para programación y publicación automática.

    Si Metricool no está configurado, los borradores se marcan como
    'scheduled' para publicación manual.
    """
    from memory.session import _SessionFactory
    from pipeline.orchestrator import PipelineOrchestrator

    async with _SessionFactory() as session:
        orch = PipelineOrchestrator()
        result = await orch.publish_approved(session)
        await session.commit()

    return PipelineWorkflowResponse(**result.to_dict())


# ─── Vista de tendencias ────────────────────────────────────

@app.get(
    "/pipeline/trends",
    response_model=TrendListResponse,
    summary="Tendencias analizadas con score IA",
    tags=["Pipeline"],
)
async def get_trends(limit: int = 20):
    """
    Devuelve las tendencias ya analizadas por la IA,
    ordenadas por score de oportunidad.
    """
    from memory.session import _SessionFactory
    from pipeline.orchestrator import PipelineOrchestrator

    async with _SessionFactory() as session:
        orch = PipelineOrchestrator()
        trends = await orch.get_trends_summary(session, limit=limit)

    return TrendListResponse(trends=trends, total=len(trends))


# ─────────────────────────────────────────────────────────────
# SCHEMA de herramientas para OpenClaw (autodescubrimiento)
# ─────────────────────────────────────────────────────────────

@app.get(
    "/george/tools-schema",
    summary="Schema de herramientas en formato OpenClaw / function-calling",
    tags=["Sistema"],
)
async def get_tools_schema():
    """
    Devuelve la definición de todas las herramientas de George
    en formato JSON compatible con OpenAI function-calling y OpenClaw.
    Tu bot puede consumir este endpoint para autodescubrir las tools.
    """
    return {
        "tools": [
            {
                "name": "run_weekly_cycle",
                "description": "Ejecuta el ciclo semanal completo de George: analiza tendencias, genera contenido para 7 días y programa publicaciones.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "strategic_prompt": {
                            "type": "string",
                            "description": "Instrucción estratégica opcional para orientar el contenido esta semana. Ej: 'Enfoca en libertad financiera, tono agresivo'",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "Si es true, genera contenido pero no publica. Por defecto: false",
                            "default": False,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "run_daily_cycle",
                "description": "Publica los posts programados para hoy y recoge métricas de ayer.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_status",
                "description": "Obtiene el estado actual de George: si está corriendo, en qué fase, y resumen del último ciclo.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_pending_posts",
                "description": "Lista los posts generados que esperan publicación. Útil para revisar contenido antes de publicar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "platform": {
                            "type": "string",
                            "enum": ["twitter", "tiktok", "linkedin", "instagram"],
                            "description": "Filtrar por plataforma (opcional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número máximo de posts a devolver",
                            "default": 20,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_platform_metrics",
                "description": "Obtiene métricas de crecimiento de una plataforma: seguidores, engagement, alcance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "platform": {
                            "type": "string",
                            "enum": ["twitter", "tiktok", "linkedin", "instagram"],
                        },
                        "weeks": {
                            "type": "integer",
                            "description": "Semanas de histórico a devolver",
                            "default": 4,
                        },
                    },
                    "required": ["platform"],
                },
            },
            {
                "name": "check_api_health",
                "description": "Verifica el estado de configuración de todas las APIs de plataformas. Muestra qué credenciales faltan.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "approve_post",
                "description": "Aprueba o rechaza un post generado por George (modo semi-autónomo).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string"},
                        "approved": {"type": "boolean"},
                        "note": {"type": "string", "description": "Nota opcional de por qué se aprueba/rechaza"},
                    },
                    "required": ["post_id", "approved"],
                },
            },
            # ─── Pipeline tools ───────────────────
            {
                "name": "pipeline_receive_signals",
                "description": "Recibir señales de tendencias desde n8n u otro webhook. Capa 1 del pipeline.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "signals": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "keyword": {"type": "string"},
                                    "source": {"type": "string", "enum": ["google_trends", "rss", "youtube", "twitter", "n8n_webhook"]},
                                    "volume": {"type": "integer"},
                                    "trending_score": {"type": "number"},
                                    "category": {"type": "string"},
                                },
                                "required": ["keyword"],
                            },
                        },
                    },
                    "required": ["signals"],
                },
            },
            {
                "name": "pipeline_capture_signals",
                "description": "Ejecutar captura automática de señales desde Google Trends, RSS y YouTube.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "pipeline_generate_content",
                "description": "Analizar tendencias con IA y generar contenido multi-plataforma. Combina Capa 2 (análisis) y Capa 3 (generación).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "min_score": {"type": "number", "description": "Score mínimo de oportunidad (0-100)", "default": 60},
                        "max_signals": {"type": "integer", "description": "Máximo de señales a procesar", "default": 5},
                        "platforms": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["instagram", "tiktok", "linkedin", "twitter", "youtube"]},
                            "description": "Plataformas destino",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "pipeline_get_drafts",
                "description": "Lista borradores de contenido pendientes de revisión humana (Capa 4).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "enum": ["instagram", "tiktok", "linkedin", "twitter", "youtube"]},
                        "limit": {"type": "integer", "default": 50},
                    },
                    "required": [],
                },
            },
            {
                "name": "pipeline_review_draft",
                "description": "Aprobar o rechazar un borrador de contenido (Capa 4).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "draft_id": {"type": "string"},
                        "approved": {"type": "boolean"},
                        "note": {"type": "string"},
                        "scheduled_at": {"type": "integer", "description": "Unix timestamp para programar"},
                    },
                    "required": ["draft_id", "approved"],
                },
            },
            {
                "name": "pipeline_publish_approved",
                "description": "Publicar borradores aprobados vía Metricool o publicación manual (Capa 5).",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "pipeline_get_trends",
                "description": "Ver tendencias analizadas con score de oportunidad IA.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": [],
                },
            },
        ]
    }
