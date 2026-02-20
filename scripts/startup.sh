#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# SuperSocial — Script de arranque y verificación
# ─────────────────────────────────────────────────────────────
# Uso:  bash scripts/startup.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m"

info()  { echo -e "${BOLD}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

API="http://localhost:8000"

# ── 1. Verificar .env ──────────────────────────────────────
info "Verificando fichero .env..."
if [ ! -f .env ]; then
    warn "No existe .env — copiando desde .env.example"
    cp .env.example .env
    warn "EDITA el fichero .env con tus API keys antes de continuar"
    warn "Mínimo: OPENAI_API_KEY y POSTGRES_PASSWORD"
    exit 1
fi
ok ".env existe"

# ── 2. Levantar infraestructura ────────────────────────────
info "Levantando PostgreSQL + Redis..."
docker compose up -d postgres redis
sleep 3

info "Esperando a que PostgreSQL esté sano..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U supersocial > /dev/null 2>&1; then
        ok "PostgreSQL listo"
        break
    fi
    if [ "$i" -eq 30 ]; then
        fail "PostgreSQL no respondió en 30 intentos"
        exit 1
    fi
    sleep 1
done

# ── 3. Migrar DB ──────────────────────────────────────────
info "Ejecutando migraciones (alembic upgrade head)..."
docker compose run --rm migrate
ok "Migraciones completadas"

# ── 4. Levantar Tool Server ────────────────────────────────
info "Levantando Tool Server en puerto 8000..."
docker compose up -d tool-server
sleep 5

info "Verificando health del servidor..."
for i in $(seq 1 20); do
    if curl -sf "$API/health" > /dev/null 2>&1; then
        ok "Tool Server activo en $API"
        break
    fi
    if [ "$i" -eq 20 ]; then
        fail "Tool Server no respondió"
        docker compose logs tool-server --tail=20
        exit 1
    fi
    sleep 2
done

# ── 5. Test rápido del pipeline ────────────────────────────
echo ""
info "=========================================="
info "  PIPELINE — TEST RÁPIDO"
info "=========================================="
echo ""

info "[Capa 1] Capturando señales (Google Trends + RSS + YouTube)..."
CAPTURE=$(curl -sf -X POST "$API/pipeline/capture" -H "Content-Type: application/json")
CAPTURE_COUNT=$(echo "$CAPTURE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('items_created',0))" 2>/dev/null || echo "?")
ok "Señales capturadas: $CAPTURE_COUNT"

echo ""
info "[Capa 2+3] Analizando con IA + generando contenido..."
info "(Esto tarda 30-60s — la IA está trabajando...)"
GENERATE=$(curl -sf -X POST "$API/pipeline/generate" \
    -H "Content-Type: application/json" \
    -d '{"min_score": 40, "max_signals": 3}')
GEN_SCORED=$(echo "$GENERATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('details',{}).get('signals_scored',0))" 2>/dev/null || echo "?")
GEN_DRAFTS=$(echo "$GENERATE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('items_created',0))" 2>/dev/null || echo "?")
ok "Señales puntuadas: $GEN_SCORED | Borradores generados: $GEN_DRAFTS"

echo ""
info "[Capa 4] Borradores pendientes de revisión:"
DRAFTS=$(curl -sf "$API/pipeline/drafts")
DRAFT_COUNT=$(echo "$DRAFTS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "?")
ok "Borradores pendientes: $DRAFT_COUNT"

echo ""
info "[Capa 5] Tendencias analizadas:"
TRENDS=$(curl -sf "$API/pipeline/trends")
TREND_COUNT=$(echo "$TRENDS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "?")
ok "Tendencias con score: $TREND_COUNT"

echo ""
echo -e "${GREEN}${BOLD}=========================================="
echo "  SISTEMA ACTIVO"
echo "==========================================${NC}"
echo ""
echo "  Panel:     $API"
echo "  API docs:  $API/docs"
echo "  Health:    $API/health"
echo ""
echo "  Próximos pasos:"
echo "    1. Revisa borradores:  curl $API/pipeline/drafts"
echo "    2. Aprueba uno:        curl -X POST $API/pipeline/drafts/{id}/review -d '{\"approved\":true}'"
echo "    3. Publica aprobados:  curl -X POST $API/pipeline/publish"
echo ""
echo "  Para levantar George + Scheduler:"
echo "    docker compose up -d george scheduler"
echo ""
