# SuperSocial — Autonomous Multi-Platform Content Engine
## Technical Architecture Document v2.0

---

## 1. SYSTEM OVERVIEW

SuperSocial is a fully autonomous AI-driven content growth engine. The human operator provides one optional weekly strategic prompt. Everything else — trend detection, analysis, content generation, publishing, and self-optimization — is executed autonomously by **George**, an OpenClaw-based AI agent.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SUPERSOCIAL SYSTEM                           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    GEORGE (OpenClaw Agent)                    │  │
│  │                                                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │  │
│  │  │  State   │  │  Tools   │  │  Memory  │  │  Logger  │   │  │
│  │  │ Manager  │  │  Router  │  │  Bridge  │  │          │   │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘   │  │
│  │       └─────────────┴─────────────┘                         │  │
│  │                         │                                    │  │
│  └─────────────────────────┼────────────────────────────────────┘  │
│                            │                                        │
│            ┌───────────────┼───────────────┐                       │
│            ▼               ▼               ▼                       │
│  ┌─────────────────┐ ┌───────────┐ ┌─────────────────┐            │
│  │   DATA LAYER    │ │  ANALYSIS │ │ CONTENT ENGINE  │            │
│  │                 │ │  ENGINE   │ │                 │            │
│  │ ┌─────────────┐ │ │           │ │ ┌─────────────┐ │            │
│  │ │ X Connector │ │ │ Engagement│ │ │Prompt Builder│ │            │
│  │ │  TikTok API │ │ │  Ratio    │ │ │  LLM Client │ │            │
│  │ │ LinkedIn API│ │ │  Hook     │ │ │  Dedup Logic│ │            │
│  │ │ Instagram   │ │ │  Detector │ │ │  Formatter  │ │            │
│  │ │  Graph API  │ │ │  Emotion  │ │ └─────────────┘ │            │
│  │ │ Rate Limiter│ │ │  Cluster  │ │                 │            │
│  │ └─────────────┘ │ │  Trend    │ └─────────────────┘            │
│  └─────────────────┘ │  Detector │                                 │
│                       └───────────┘                                 │
│                                                                     │
│  ┌─────────────────┐ ┌───────────┐ ┌─────────────────┐            │
│  │  MEMORY SYSTEM  │ │ STRATEGY  │ │  VIDEO PIPELINE │            │
│  │  (PostgreSQL)   │ │  MODULE   │ │                 │            │
│  │                 │ │           │ │ Script Formatter│            │
│  │ posts_history   │ │ Narrative │ │ SRT Generator   │            │
│  │ perf_metrics    │ │ Selector  │ │ JSON Exporter   │            │
│  │ hook_patterns   │ │ Emotion   │ │ (HeyGen/Runway) │            │
│  │ emot_triggers   │ │ Selector  │ │                 │            │
│  │ growth_metrics  │ │ Authority │ │                 │            │
│  │ strategy_weights│ │ Planner   │ └─────────────────┘            │
│  └─────────────────┘ └───────────┘                                 │
│                                                                     │
│  ┌─────────────────┐ ┌───────────┐                                 │
│  │   SCHEDULER     │ │ FEEDBACK  │                                 │
│  │                 │ │  LOOP     │                                 │
│  │ Weekly Cycle    │ │           │                                 │
│  │ Daily Micro     │ │ Metrics   │                                 │
│  │ Smart Timeslot  │ │ Comparator│                                 │
│  │ Allocator       │ │ Strategy  │                                 │
│  │                 │ │ Updater   │                                 │
│  └─────────────────┘ └───────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. FOLDER STRUCTURE

```
supersocial/
├── ARCHITECTURE.md
├── README.md
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── alembic.ini
│
├── alembic/                        # DB migrations
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
│
├── config/                         # Configuration layer
│   ├── __init__.py
│   ├── settings.py                 # Pydantic settings
│   └── credentials.py             # Vault/env credential manager
│
├── george/                         # George OpenClaw agent
│   ├── __init__.py
│   ├── agent.py                   # Main agent loop
│   ├── state.py                   # State machine
│   ├── logger.py                  # Structured logging
│   └── tools/
│       ├── __init__.py
│       ├── base.py                # Tool base class
│       ├── api_tool.py            # API interaction tools
│       ├── analysis_tool.py       # Analysis tools
│       ├── content_tool.py        # Content generation tools
│       └── storage_tool.py        # DB tools
│
├── data_layer/                    # Platform API connectors
│   ├── __init__.py
│   ├── base_connector.py
│   ├── twitter_connector.py
│   ├── tiktok_connector.py
│   ├── linkedin_connector.py
│   ├── instagram_connector.py
│   └── rate_limiter.py
│
├── analysis/                      # Analysis engine
│   ├── __init__.py
│   ├── engagement.py
│   ├── hook_detector.py
│   ├── emotion_cluster.py
│   ├── format_recognizer.py
│   └── trend_detector.py
│
├── memory/                        # Persistence layer
│   ├── __init__.py
│   ├── models.py                  # SQLAlchemy models
│   ├── repository.py             # Data access layer
│   └── session.py                # DB session management
│
├── strategy/                      # Strategy module
│   ├── __init__.py
│   ├── narrative_selector.py
│   ├── emotion_selector.py
│   ├── authority_selector.py
│   └── distribution_planner.py
│
├── content/                       # Content generation
│   ├── __init__.py
│   ├── prompt_builder.py
│   ├── platform_formatter.py
│   ├── deduplication.py
│   └── llm_client.py
│
├── video/                         # Video pipeline
│   ├── __init__.py
│   ├── script_formatter.py
│   ├── srt_generator.py
│   └── render_exporter.py
│
├── scheduler/                     # Task scheduling
│   ├── __init__.py
│   ├── weekly_cycle.py
│   ├── daily_cycle.py
│   └── time_slot_allocator.py
│
├── feedback/                      # Performance feedback loop
│   ├── __init__.py
│   ├── metrics_puller.py
│   ├── cycle_comparator.py
│   └── strategy_updater.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_data_layer.py
    ├── test_analysis.py
    ├── test_content.py
    ├── test_video.py
    └── test_george.py
```

---

## 3. DATABASE SCHEMA

```sql
-- posts_history: every piece of content George publishes
CREATE TABLE posts_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        VARCHAR(20) NOT NULL,          -- 'twitter','tiktok','linkedin','instagram'
    external_id     VARCHAR(255),                  -- platform post ID after publish
    content_hash    VARCHAR(64) NOT NULL,           -- SHA-256 for deduplication
    content_text    TEXT,
    content_type    VARCHAR(30) NOT NULL,           -- 'text','reel','carousel','video'
    hook_text       TEXT,
    emotional_tone  VARCHAR(50),
    narrative_type  VARCHAR(50),
    authority_angle VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'draft',   -- draft|scheduled|published|failed
    scheduled_at    TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,
    cycle_id        UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- performance_metrics: per-post engagement data (pulled 24h, 48h, 7d)
CREATE TABLE performance_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id         UUID REFERENCES posts_history(id),
    platform        VARCHAR(20) NOT NULL,
    measured_at     TIMESTAMPTZ DEFAULT NOW(),
    window_hours    INTEGER NOT NULL,              -- 24, 48, 168 (7d)
    impressions     BIGINT DEFAULT 0,
    reach           BIGINT DEFAULT 0,
    likes           BIGINT DEFAULT 0,
    comments        BIGINT DEFAULT 0,
    shares          BIGINT DEFAULT 0,
    saves           BIGINT DEFAULT 0,
    profile_visits  BIGINT DEFAULT 0,
    watch_time_avg  FLOAT,                         -- seconds, video only
    retention_rate  FLOAT,                         -- 0.0–1.0
    engagement_rate FLOAT,                         -- computed
    virality_score  FLOAT                          -- computed
);

-- hook_patterns: learned high-performing hook structures
CREATE TABLE hook_patterns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_text    TEXT NOT NULL,
    pattern_type    VARCHAR(50),                   -- 'question','shock','promise','story'
    avg_engagement  FLOAT DEFAULT 0,
    use_count       INTEGER DEFAULT 0,
    win_rate        FLOAT DEFAULT 0,               -- % times above avg performance
    platforms       VARCHAR(100),                  -- comma-separated platforms
    last_used_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- emotional_triggers: catalogued emotional angles with performance data
CREATE TABLE emotional_triggers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_name    VARCHAR(100) NOT NULL,
    trigger_type    VARCHAR(50),                   -- 'fear','aspiration','anger','identity'
    description     TEXT,
    avg_engagement  FLOAT DEFAULT 0,
    use_count       INTEGER DEFAULT 0,
    win_rate        FLOAT DEFAULT 0,
    best_platform   VARCHAR(20),
    best_content_type VARCHAR(30),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- growth_metrics: account-level weekly snapshots
CREATE TABLE growth_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        VARCHAR(20) NOT NULL,
    week_start      DATE NOT NULL,
    follower_count  BIGINT DEFAULT 0,
    follower_delta  BIGINT DEFAULT 0,
    avg_reach       BIGINT DEFAULT 0,
    avg_engagement  FLOAT DEFAULT 0,
    top_post_id     UUID REFERENCES posts_history(id),
    worst_post_id   UUID REFERENCES posts_history(id),
    posts_published INTEGER DEFAULT 0,
    cycle_id        UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, week_start)
);

-- strategy_weights: George's evolving strategy configuration
CREATE TABLE strategy_weights (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        VARCHAR(20) NOT NULL,
    weight_key      VARCHAR(100) NOT NULL,          -- e.g. 'hook_type.question'
    weight_value    FLOAT NOT NULL DEFAULT 1.0,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_reason  TEXT,
    UNIQUE(platform, weight_key)
);

-- agent_cycles: tracks each full execution cycle
CREATE TABLE agent_cycles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_type      VARCHAR(20) NOT NULL,           -- 'weekly','daily'
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'running',  -- running|completed|failed
    strategic_prompt TEXT,                          -- human input if provided
    summary         JSONB,
    error_log       JSONB
);

-- agent_logs: structured log of every George action
CREATE TABLE agent_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id        UUID REFERENCES agent_cycles(id),
    logged_at       TIMESTAMPTZ DEFAULT NOW(),
    level           VARCHAR(10) NOT NULL,           -- INFO|WARN|ERROR|DEBUG
    component       VARCHAR(50) NOT NULL,
    action          VARCHAR(100) NOT NULL,
    payload         JSONB,
    duration_ms     INTEGER
);
```

---

## 4. GEORGE AGENT BEHAVIOR DEFINITION

### Identity
George is a task-oriented autonomous agent built on the OpenClaw framework. He is NOT a content creator — he is a **systems operator** that orchestrates tools to achieve platform growth objectives.

### State Machine

```
IDLE
  │
  ▼
CYCLE_START ──► (load strategic prompt if available)
  │
  ▼
TREND_FETCH ──► (call API tools for each platform)
  │
  ▼
TREND_ANALYZE ──► (engagement ratios, hooks, emotions)
  │
  ▼
STRATEGY_SELECT ──► (narrative + emotion + authority + format)
  │
  ▼
CONTENT_GENERATE ──► (LLM calls with structured prompts)
  │
  ▼
CONTENT_VALIDATE ──► (dedup check, platform rule check)
  │
  ▼
VIDEO_PIPELINE ──► (script, SRT, JSON export if video content)
  │
  ▼
SCHEDULE_PUBLISH ──► (allocate slots, queue posts)
  │
  ▼
PUBLISH_EXECUTE ──► (API publish, record external IDs)
  │
  ▼
METRICS_PULL ──► (7-day lookback on previous cycle posts)
  │
  ▼
FEEDBACK_ANALYZE ──► (compare cycles, update weights)
  │
  ▼
CYCLE_COMPLETE ──► log summary, IDLE
```

### Error Handling Protocol
```
1. API errors       → retry with exponential backoff (3 attempts: 2s, 8s, 32s)
2. Rate limit hit   → park task, schedule retry after window
3. LLM failures     → fallback to template-based generation
4. Publish failures → mark post as 'failed', alert log, continue cycle
5. DB errors        → rollback transaction, log full traceback
6. Unknown errors   → quarantine cycle step, log, continue with next step
```

---

## 5. EXECUTION LIFECYCLE

### Weekly Full Cycle (Sunday 00:00 UTC)
```
00:00  Cycle start — load config + human prompt (if any)
00:05  Fetch 7-day trends: X, TikTok, LinkedIn, Instagram
00:25  Run analysis engine on fetched data
00:40  Pull previous cycle performance metrics
00:45  Run feedback loop — update strategy weights
01:00  Strategy selection for next 7 days
01:10  Generate content batch (7 days × platforms)
01:50  Video pipeline for video-format posts
02:10  Schedule all content to optimal time slots
02:15  Log cycle summary to DB
02:20  Cycle complete — George returns to IDLE
```

### Daily Micro Cycle (06:00 UTC)
```
06:00  Pull 24h metrics on yesterday's posts
06:10  Detect underperforming slots (adjust if needed)
06:15  Execute scheduled posts for today
06:20  Monitor for engagement spikes (repost/boost signal)
06:25  Log micro-cycle summary
```

---

## 6. DEPLOYMENT (Docker)

```
docker-compose up -d
```

Services:
- `george` — main agent container (Python)
- `postgres` — database
- `redis` — task queue + rate limit counters
- `scheduler` — cron container (triggers George cycles)

---

## 7. PHASE ROLLOUT

### Phase 1 — Semi-Autonomous
- Human reviews generated content before publish
- Human approves strategy weights
- George fetches, analyzes, generates → pauses for approval

### Phase 2 — Full Automation
- George publishes autonomously
- Human receives weekly digest email only
- Strategy updates applied automatically

### Phase 3 — Self-Optimizing Growth Engine
- George runs A/B tests autonomously
- Discovers new hook patterns from scratch
- Adjusts posting frequency per platform independently
- Generates platform-specific persona variations

---

## 8. PIPELINE — ARQUITECTURA DE 5 CAPAS

La arquitectura de 5 capas complementa a George con un pipeline estructurado
que separa responsabilidades y permite integración con orquestadores externos (n8n).

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE — 5 CAPAS                                     │
│                                                                           │
│   CAPA 1              CAPA 2            CAPA 3                            │
│   Captura             Análisis IA       Generación                        │
│   ┌──────────┐       ┌──────────┐      ┌──────────────┐                  │
│   │ Google   │──┐    │  LLM     │      │  Instagram   │                  │
│   │ Trends   │  │    │  Scorer  │      │  TikTok      │                  │
│   ├──────────┤  │    │          │      │  LinkedIn    │                  │
│   │ RSS      │  ├──► │ ai_score │──►   │  Twitter/X   │                  │
│   │ Feeds    │  │    │ cliente  │      │  YouTube     │                  │
│   ├──────────┤  │    │ formato  │      └──────┬───────┘                  │
│   │ YouTube  │  │    │ ángulo   │             │                           │
│   │ API      │──┘    └──────────┘             │                           │
│   ├──────────┤                                ▼                           │
│   │ n8n      │                        ┌──────────────┐                    │
│   │ Webhook  │                        │ content_     │                    │
│   └──────────┘                        │ drafts DB    │                    │
│       │                               └──────┬───────┘                    │
│       ▼                                      │                           │
│   ┌──────────┐          CAPA 4               ▼           CAPA 5          │
│   │ trend_   │       ┌──────────────┐   ┌──────────────┐                 │
│   │ signals  │       │ Panel de     │   │  Metricool   │                 │
│   │ DB       │       │ Revisión     │──►│  API         │                 │
│   └──────────┘       │ Humana       │   │              │                 │
│                      │ Aprobar /    │   │ Programar /  │                 │
│                      │ Rechazar     │   │ Publicar     │                 │
│                      └──────────────┘   └──────────────┘                 │
└───────────────────────────────────────────────────────────────────────────┘
```

### 3 Workflows (no 20 flujos)

| Workflow | Trigger | Qué hace |
|----------|---------|----------|
| **1. capture_signals** | n8n cron diario / POST /pipeline/capture | Fetcha Google Trends, RSS, YouTube. Guarda en `trend_signals`. |
| **2. generate_content** | n8n post-captura / POST /pipeline/generate | Puntúa señales con IA (Capa 2). Genera contenido multi-plataforma (Capa 3). |
| **3. publish_approved** | n8n post-revisión / POST /pipeline/publish | Envía borradores aprobados a Metricool para scheduling. |

### Pipeline DB Tables

```sql
-- trend_signals: señales externas capturadas (Capa 1)
CREATE TABLE trend_signals (
    id                  UUID PRIMARY KEY,
    source              VARCHAR(50) NOT NULL,     -- google_trends|rss|youtube|n8n_webhook
    keyword             VARCHAR(255) NOT NULL,
    volume              BIGINT DEFAULT 0,
    trending_score      FLOAT DEFAULT 0.0,        -- 0-100 raw popularity
    region              VARCHAR(10) DEFAULT 'global',
    category            VARCHAR(100),
    raw_data            JSONB,
    captured_at         BIGINT,
    -- AI analysis (Capa 2)
    ai_score            FLOAT,                    -- 0-100 opportunity score
    ideal_client        VARCHAR(255),
    recommended_format  VARCHAR(50),              -- video|carousel|thread|post
    viral_angle         TEXT,
    analyzed_at         BIGINT,
    status              VARCHAR(20) DEFAULT 'raw' -- raw|analyzed|used|discarded
);

-- content_drafts: contenido generado pendiente de revisión (Capa 3-4)
CREATE TABLE content_drafts (
    id              UUID PRIMARY KEY,
    signal_id       UUID REFERENCES trend_signals(id),
    platform        VARCHAR(20) NOT NULL,         -- instagram|tiktok|linkedin|twitter|youtube
    content_type    VARCHAR(30) NOT NULL,          -- post|script|thread|carousel|idea
    content_text    TEXT NOT NULL,
    hook_text       TEXT,
    hashtags        TEXT,
    emotional_tone  VARCHAR(50),
    narrative_type  VARCHAR(50),
    char_count      INTEGER DEFAULT 0,
    -- Review (Capa 4)
    status          VARCHAR(20) DEFAULT 'generated',  -- generated|pending_review|approved|rejected|scheduled|published|failed
    reviewer_note   TEXT,
    reviewed_at     BIGINT,
    -- Publishing (Capa 5)
    metricool_id    VARCHAR(255),
    external_id     VARCHAR(255),
    scheduled_at    BIGINT,
    published_at    BIGINT,
    created_at      BIGINT,
    updated_at      BIGINT
);
```

### Pipeline API Endpoints

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/pipeline/signals` | Webhook n8n: recibir señales externas |
| POST | `/pipeline/capture` | Captura automática de todas las fuentes |
| POST | `/pipeline/generate` | Analizar + generar contenido |
| GET  | `/pipeline/drafts` | Borradores pendientes de revisión |
| POST | `/pipeline/drafts/{id}/review` | Aprobar / rechazar borrador |
| POST | `/pipeline/publish` | Publicar aprobados vía Metricool |
| GET  | `/pipeline/trends` | Tendencias analizadas con score IA |

### Integración con n8n

```
n8n Workflow 1 (Cron: cada día 08:00):
  [Google Trends] ──► [HTTP POST /pipeline/signals]
  [RSS Reader]    ──► [HTTP POST /pipeline/signals]
  [YouTube API]   ──► [HTTP POST /pipeline/signals]
  ──► [HTTP POST /pipeline/generate]

n8n Workflow 2 (Trigger: humano aprueba):
  [Webhook] ──► [HTTP POST /pipeline/publish]
```

### Nuevo directorio de ficheros

```
supersocial/
├── signals/                          # Capa 1 — Signal capture
│   ├── __init__.py
│   ├── google_trends.py              # Google Trends API client
│   ├── rss_reader.py                 # RSS/Atom feed reader
│   ├── youtube_trends.py             # YouTube Data API client
│   └── aggregator.py                 # Combines all sources + dedup
│
├── pipeline/                         # Orchestration — 3 workflows
│   ├── __init__.py
│   ├── trend_scorer.py               # Capa 2 — AI analysis + scoring
│   ├── content_generator.py          # Capa 3 — Multi-platform generation
│   └── orchestrator.py               # 3 unified workflows
│
├── integrations/                     # External service clients
│   ├── __init__.py
│   └── metricool.py                  # Capa 5 — Metricool scheduler API
│
├── alembic/versions/
│   ├── 001_initial_schema.py
│   └── 002_pipeline_tables.py        # trend_signals + content_drafts
```
