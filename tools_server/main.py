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
    YouTubeChannelsResponse,
    YouTubeCharactersResponse,
    YouTubeVideosResponse,
    YouTubeStatsResponse,
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
# YOUTUBE FACTORY — Canales, personajes y vídeos
# ─────────────────────────────────────────────────────────────

@app.get(
    "/george/youtube/stats",
    response_model=YouTubeStatsResponse,
    summary="Estadísticas globales de YouTube Factory",
    tags=["YouTube Factory"],
)
async def youtube_stats():
    """Resumen general: canales, personajes, vídeos producidos, views, CTR."""
    from memory.session import _SessionFactory
    from youtube.models import YouTubeChannel, YouTubeCharacter, YouTubeVideo
    from sqlalchemy import select, func

    async with _SessionFactory() as session:
        ch_total = (await session.execute(select(func.count(YouTubeChannel.id)))).scalar() or 0
        ch_active = (await session.execute(
            select(func.count(YouTubeChannel.id)).where(YouTubeChannel.is_active.is_(True))
        )).scalar() or 0
        char_total = (await session.execute(select(func.count(YouTubeCharacter.id)))).scalar() or 0
        vid_total = (await session.execute(select(func.count(YouTubeVideo.id)))).scalar() or 0
        vid_published = (await session.execute(
            select(func.count(YouTubeVideo.id)).where(YouTubeVideo.status == "published")
        )).scalar() or 0
        total_views = (await session.execute(select(func.coalesce(func.sum(YouTubeVideo.views), 0)))).scalar() or 0
        total_likes = (await session.execute(select(func.coalesce(func.sum(YouTubeVideo.likes), 0)))).scalar() or 0
        avg_ctr = (await session.execute(select(func.coalesce(func.avg(YouTubeVideo.ctr), 0.0)))).scalar() or 0.0

        # Videos by status
        status_rows = (await session.execute(
            select(YouTubeVideo.status, func.count(YouTubeVideo.id)).group_by(YouTubeVideo.status)
        )).all()
        videos_by_status = {row[0]: row[1] for row in status_rows}

    return YouTubeStatsResponse(
        total_channels=ch_total,
        active_channels=ch_active,
        total_characters=char_total,
        total_videos=vid_total,
        published_videos=vid_published,
        total_views=int(total_views),
        total_likes=int(total_likes),
        avg_ctr=round(float(avg_ctr), 4),
        videos_by_status=videos_by_status,
    )


@app.get(
    "/george/youtube/channels",
    response_model=YouTubeChannelsResponse,
    summary="Lista de canales YouTube configurados",
    tags=["YouTube Factory"],
)
async def youtube_channels():
    """Devuelve todos los canales YouTube configurados con sus estadísticas."""
    from memory.session import _SessionFactory
    from youtube.models import YouTubeChannel, YouTubeCharacter
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with _SessionFactory() as session:
        result = await session.execute(
            select(YouTubeChannel).options(selectinload(YouTubeChannel.character))
        )
        channels = result.scalars().all()

    return YouTubeChannelsResponse(
        channels=[
            {
                "channel_id": ch.id,
                "name": ch.name,
                "niche": ch.niche,
                "language": ch.language,
                "tone": ch.tone,
                "videos_per_week": ch.videos_per_week,
                "target_duration_minutes": ch.target_duration_minutes,
                "privacy_status": ch.privacy_status,
                "is_active": ch.is_active,
                "total_videos_published": ch.total_videos_published,
                "total_views": ch.total_views,
                "subscriber_count": ch.subscriber_count,
                "character_name": ch.character.name if ch.character else None,
                "created_at": ch.created_at,
            }
            for ch in channels
        ],
        total=len(channels),
    )


@app.get(
    "/george/youtube/characters",
    response_model=YouTubeCharactersResponse,
    summary="Personajes IA configurados para YouTube",
    tags=["YouTube Factory"],
)
async def youtube_characters():
    """Devuelve todos los personajes IA con su identidad visual y de voz."""
    from memory.session import _SessionFactory
    from youtube.models import YouTubeCharacter, YouTubeChannel
    from sqlalchemy import select, func

    async with _SessionFactory() as session:
        result = await session.execute(select(YouTubeCharacter))
        characters = result.scalars().all()

        # Count channels per character
        ch_counts = {}
        count_rows = (await session.execute(
            select(YouTubeChannel.character_id, func.count(YouTubeChannel.id))
            .group_by(YouTubeChannel.character_id)
        )).all()
        for row in count_rows:
            if row[0]:
                ch_counts[row[0]] = row[1]

    return YouTubeCharactersResponse(
        characters=[
            {
                "character_id": c.id,
                "name": c.name,
                "physical_description": c.physical_description,
                "art_style": c.art_style,
                "color_palette": c.color_palette,
                "voice_id": c.elevenlabs_voice_id or "",
                "is_active": c.is_active,
                "videos_generated": c.videos_generated,
                "channels_count": ch_counts.get(c.id, 0),
            }
            for c in characters
        ],
        total=len(characters),
    )


@app.get(
    "/george/youtube/videos",
    response_model=YouTubeVideosResponse,
    summary="Vídeos producidos por YouTube Factory",
    tags=["YouTube Factory"],
)
async def youtube_videos(
    channel_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """
    Lista los vídeos producidos. Filtra por canal o estado.
    Estados: draft, rendering, rendered, uploading, published, failed
    """
    from memory.session import _SessionFactory
    from youtube.models import YouTubeVideo, YouTubeChannel
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with _SessionFactory() as session:
        q = select(YouTubeVideo).options(
            selectinload(YouTubeVideo.channel)
        ).order_by(YouTubeVideo.created_at.desc()).limit(limit)

        if channel_id:
            q = q.where(YouTubeVideo.channel_id == channel_id)
        if status:
            q = q.where(YouTubeVideo.status == status)

        result = await session.execute(q)
        videos = result.scalars().all()

    return YouTubeVideosResponse(
        videos=[
            {
                "video_id": v.id,
                "channel_id": v.channel_id,
                "channel_name": v.channel.name if v.channel else None,
                "topic": v.topic,
                "title": v.title,
                "youtube_url": v.youtube_url,
                "status": v.status,
                "duration_seconds": v.duration_seconds,
                "scenes_count": v.scenes_count,
                "views": v.views or 0,
                "likes": v.likes or 0,
                "comments_count": v.comments_count or 0,
                "ctr": v.ctr or 0.0,
                "created_at": v.created_at,
                "published_at": v.published_at,
            }
            for v in videos
        ],
        total=len(videos),
    )


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
