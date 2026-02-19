"""
SuperSocial Tool Server — expone a George como herramientas REST.

Cualquier agente (OpenClaw, LangChain, CrewAI, etc.) puede llamar
a George a través de estos endpoints HTTP.

Arrancar:
    uvicorn tools_server.main:app --host 0.0.0.0 --port 8000 --reload
"""
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from tools_server.schemas import (
    RunCycleRequest,
    RunCycleResponse,
    AgentStatusResponse,
    PlatformMetricsResponse,
    PendingPostsResponse,
    ApiHealthResponse,
    ApprovePostRequest,
    CycleSummaryResponse,
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
# HEALTHCHECK del servidor
# ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "ok", "agent": "george", "timestamp": int(time.time())}


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
        ]
    }
