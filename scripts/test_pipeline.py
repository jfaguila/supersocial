#!/usr/bin/env python3
"""
SuperSocial — Test de pipeline sin APIs externas.

Uso:
  docker compose exec tool-server python scripts/test_pipeline.py

Verifica:
  1. Imports de todos los módulos
  2. Conexión a PostgreSQL
  3. Tablas del pipeline creadas
  4. CRUD básico: insertar señal → crear borrador → consultar
"""
import asyncio
import sys
import os
import time
import uuid

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BOLD = "\033[1m"
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
NC = "\033[0m"

passed = 0
failed = 0


def ok(msg):
    global passed
    passed += 1
    print(f"{GREEN}  [OK]{NC} {msg}")


def fail(msg, err=None):
    global failed
    failed += 1
    detail = f" — {err}" if err else ""
    print(f"{RED}[FAIL]{NC} {msg}{detail}")


def section(title):
    print(f"\n{BOLD}── {title} ──{NC}")


# ── 1. IMPORTS ──────────────────────────────────────────────
section("1. Verificando imports")

try:
    from memory.models import Base, TrendSignal, ContentDraft
    ok("memory.models (TrendSignal, ContentDraft)")
except Exception as e:
    fail("memory.models", e)

try:
    from signals.google_trends import GoogleTrendsSource
    from signals.rss_reader import RSSSource
    from signals.youtube_trends import YouTubeTrendsSource
    from signals.aggregator import SignalAggregator
    ok("signals (GoogleTrends, RSS, YouTube, Aggregator)")
except Exception as e:
    fail("signals", e)

try:
    from pipeline.trend_scorer import TrendScorer
    from pipeline.content_generator import ContentGenerator
    from pipeline.orchestrator import PipelineOrchestrator
    ok("pipeline (TrendScorer, ContentGenerator, Orchestrator)")
except Exception as e:
    fail("pipeline", e)

try:
    from integrations.metricool import MetricoolClient
    ok("integrations.metricool")
except Exception as e:
    fail("integrations.metricool", e)

try:
    from config.settings import get_settings
    settings = get_settings()
    ok(f"config.settings (geo={settings.signal_geo})")
except Exception as e:
    fail("config.settings", e)


# ── 2. DATABASE ─────────────────────────────────────────────
section("2. Verificando base de datos")


async def test_database():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text, inspect
    from memory.models import Base, TrendSignal, ContentDraft

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    # Test connection
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        ok("Conexión a PostgreSQL")
    except Exception as e:
        fail("Conexión a PostgreSQL", e)
        return

    # Check tables exist
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            )
            tables = [row[0] for row in result.fetchall()]

        if "trend_signals" in tables:
            ok("Tabla trend_signals existe")
        else:
            fail("Tabla trend_signals NO existe — ejecuta: alembic upgrade head")

        if "content_drafts" in tables:
            ok("Tabla content_drafts existe")
        else:
            fail("Tabla content_drafts NO existe — ejecuta: alembic upgrade head")

        # Check video columns
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='content_drafts' AND column_name='video_path'")
            )
            if result.fetchone():
                ok("Columna video_path en content_drafts")
            else:
                fail("Columna video_path NO existe — necesita migration 002")

    except Exception as e:
        fail("Verificación de tablas", e)
        return

    # ── 3. CRUD TEST ────────────────────────────────────────
    section("3. Test CRUD (insertar señal → borrador → consultar)")

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    test_id = str(uuid.uuid4())

    try:
        async with Session() as session:
            # Insert a test signal
            signal = TrendSignal(
                id=test_id,
                source="test",
                keyword="test_pipeline_run",
                volume=1000,
                trending_score=75.0,
                region="US",
                category="technology",
                raw_data={"test": True},
                status="raw",
            )
            session.add(signal)
            await session.commit()
            ok("INSERT TrendSignal")

            # Insert a test draft linked to signal
            draft_id = str(uuid.uuid4())
            draft = ContentDraft(
                id=draft_id,
                signal_id=test_id,
                platform="instagram",
                content_type="carousel",
                content_text="Test post about AI trends #test",
                hook_text="Did you know AI is changing everything?",
                hashtags="#ai #test #supersocial",
                emotional_tone="inspirational",
                char_count=35,
                status="generated",
            )
            session.add(draft)
            await session.commit()
            ok("INSERT ContentDraft")

            # Query back
            from sqlalchemy import select
            result = await session.execute(
                select(ContentDraft).where(ContentDraft.id == draft_id)
            )
            fetched = result.scalar_one_or_none()
            assert fetched is not None
            assert fetched.platform == "instagram"
            assert fetched.signal_id == test_id
            ok("SELECT + verificación de relación signal→draft")

            # Cleanup test data
            await session.delete(fetched)
            signal_obj = await session.get(TrendSignal, test_id)
            if signal_obj:
                await session.delete(signal_obj)
            await session.commit()
            ok("DELETE test data (limpieza)")

    except Exception as e:
        fail("CRUD test", e)

    await engine.dispose()


asyncio.run(test_database())

# ── 4. API ENDPOINTS ────────────────────────────────────────
section("4. Verificando API endpoints (si el servidor está activo)")

try:
    import httpx

    resp = httpx.get("http://localhost:8000/health", timeout=3)
    if resp.status_code == 200:
        ok("GET /health")

        # Test pipeline endpoints exist
        for endpoint in [
            ("GET", "/pipeline/drafts"),
            ("GET", "/pipeline/trends"),
        ]:
            method, path = endpoint
            r = httpx.request(method, f"http://localhost:8000{path}", timeout=5)
            if r.status_code < 500:
                ok(f"{method} {path} (status {r.status_code})")
            else:
                fail(f"{method} {path}", f"status {r.status_code}")

        # Test docs
        r = httpx.get("http://localhost:8000/docs", timeout=5)
        if r.status_code == 200:
            ok("GET /docs (Swagger UI)")
        else:
            fail("GET /docs", f"status {r.status_code}")
    else:
        print(f"{YELLOW}  [SKIP]{NC} Servidor no activo en :8000 — esto es normal si ejecutas el test fuera de Docker")
except Exception:
    print(f"{YELLOW}  [SKIP]{NC} Servidor no activo en :8000 — esto es normal si ejecutas el test fuera de Docker")


# ── 5. API KEYS CHECK ───────────────────────────────────────
section("5. Verificando API keys configuradas")

settings = get_settings()

keys = {
    "OPENAI_API_KEY": settings.openai_api_key,
    "METRICOOL_API_TOKEN": settings.metricool_api_token,
    "RUNWAYML_API_KEY": os.getenv("RUNWAYML_API_KEY", ""),
    "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY", ""),
    "YOUTUBE_API_KEY": settings.youtube_api_key,
}

for name, value in keys.items():
    if value and not value.startswith("sk-...") and value != "":
        ok(f"{name} configurada")
    else:
        level = "WARN" if name in ("RUNWAYML_API_KEY", "ELEVENLABS_API_KEY", "YOUTUBE_API_KEY") else "FAIL"
        if level == "WARN":
            print(f"{YELLOW}  [OPT]{NC} {name} no configurada (opcional)")
        else:
            fail(f"{name} NO configurada — necesaria para el pipeline")


# ── SUMMARY ─────────────────────────────────────────────────
print(f"\n{BOLD}{'=' * 50}{NC}")
if failed == 0:
    print(f"{GREEN}{BOLD}  TODOS LOS TESTS PASARON ({passed}/{passed}){NC}")
else:
    print(f"{RED}{BOLD}  {failed} TESTS FALLARON{NC} — {GREEN}{passed} pasaron{NC}")
print(f"{BOLD}{'=' * 50}{NC}\n")

sys.exit(1 if failed > 0 else 0)
