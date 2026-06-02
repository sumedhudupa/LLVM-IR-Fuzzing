#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run.sh — Run the LLVM IR Fuzzing Pipeline
#
# Usage:
#   ./scripts/run.sh              # Start all services
#   ./scripts/run.sh --eval       # Start services + run automated evaluation
#   ./scripts/run.sh --stop       # Stop all services
#   ./scripts/run.sh --logs       # Show live logs
#
# Prerequisites:
#   - Run ./scripts/build.sh first to build Docker images
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Docker Compose command detection
COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
fi

cd "$PROJECT_ROOT"

# ── Handle --stop ────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--stop" ]]; then
    echo -e "${YELLOW}Stopping all services...${NC}"
    $COMPOSE_CMD down
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
fi

# ── Handle --logs ────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--logs" ]]; then
    $COMPOSE_CMD logs -f
    exit 0
fi

echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  LLVM IR Fuzzing Pipeline — Run${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"

# ── Step 1: Verify build ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[1/4] Verifying build...${NC}"

if ! docker images | grep -q "llvm-ir-fuzzing"; then
    echo -e "${YELLOW}⚠ Docker images not found. Running build first...${NC}"
    bash "$SCRIPT_DIR/build.sh"
fi
echo -e "  ${GREEN}✓ Docker images found${NC}"

# ── Step 2: Start services ─────────────────────────────────────────────────
echo -e "\n${YELLOW}[2/4] Starting services...${NC}"

$COMPOSE_CMD up -d

echo -e "  ${GREEN}✓ Ollama${NC}    → http://localhost:11434"
echo -e "  ${GREEN}✓ Backend${NC}   → http://localhost:8000"
echo -e "  ${GREEN}✓ Frontend${NC}  → http://localhost:4000"
echo -e "  ${GREEN}✓ API Docs${NC}  → http://localhost:8000/docs"

# ── Step 3: Wait for services ──────────────────────────────────────────────
echo -e "\n${YELLOW}[3/4] Waiting for services to be ready...${NC}"

MAX_RETRIES=30
RETRY_INTERVAL=2

# Wait for backend
echo -n "  Waiting for Backend API"
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "\n  ${GREEN}✓ Backend API is ready${NC}"
        break
    fi
    echo -n "."
    sleep $RETRY_INTERVAL
    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo -e "\n  ${RED}✗ Backend API did not start within $(( MAX_RETRIES * RETRY_INTERVAL ))s${NC}"
        echo -e "  ${YELLOW}Check logs: $COMPOSE_CMD logs backend${NC}"
    fi
done

# ── Step 4: Run evaluation (if --eval flag) ────────────────────────────────
if [[ "${1:-}" == "--eval" ]]; then
    echo -e "\n${YELLOW}[4/4] Running automated evaluation...${NC}"

    API_BASE="http://localhost:8000"
    SEEDS=("seed_arith.ll" "seed_branch.ll" "seed_loop.ll" "seed_multifunction.ll" "seed_bitwise.ll" "seed_memory.ll" "seed_nested_branch.ll")
    MUTATORS=("llm" "grammar" "random")
    COUNT=5

    echo -e "\n${CYAN}── Phase 1: Generating Mutants ──${NC}"
    for seed in "${SEEDS[@]}"; do
        for mutator in "${MUTATORS[@]}"; do
            echo -e "  Generating: ${BLUE}$seed${NC} × ${BLUE}$mutator${NC} × ${BLUE}$COUNT${NC}"
            curl -s -X POST "$API_BASE/api/v1/mutants/generate" \
                -H "Content-Type: application/json" \
                -d "{\"seed_names\": [\"$seed\"], \"mutator_type\": \"$mutator\", \"count\": $COUNT}" \
                > /dev/null 2>&1 || echo -e "    ${YELLOW}⚠ Generation request failed (may need Ollama for LLM)${NC}"
        done
    done

    echo -e "\n${CYAN}── Phase 2: Listing Seeds ──${NC}"
    SEED_RESPONSE=$(curl -s "$API_BASE/api/v1/seeds" 2>/dev/null || echo "{}")
    echo -e "  Seeds: $SEED_RESPONSE" | head -c 200
    echo ""

    echo -e "\n${CYAN}── Phase 3: Getting Comparison Metrics ──${NC}"
    COMPARISON=$(curl -s "$API_BASE/api/v1/analysis/comparison" 2>/dev/null || echo "{}")
    echo -e "  Comparison metrics:"
    echo "$COMPARISON" | python3 -m json.tool 2>/dev/null || echo "$COMPARISON" | head -c 500

    echo -e "\n${CYAN}── Phase 4: Differential Testing ──${NC}"
    DIFF_RESULT=$(curl -s -X POST "$API_BASE/api/v1/differential/run" \
        -H "Content-Type: application/json" \
        -d '{}' 2>/dev/null || echo "{}")
    echo -e "  Differential result: $DIFF_RESULT"

    echo -e "\n${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Evaluation complete!${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Results are available at:"
    echo -e "  ${BLUE}Frontend Dashboard${NC}:  http://localhost:4000"
    echo -e "  ${BLUE}Comparison View${NC}:    http://localhost:4000/comparison"
    echo -e "  ${BLUE}Raw Metrics${NC}:        http://localhost:8000/api/v1/analysis/comparison"
    echo -e "  ${BLUE}Log Files${NC}:          backend/data/logs/"
else
    echo -e "\n${YELLOW}[4/4] Skipping evaluation (use --eval to run)${NC}"
fi

# ── Done ─────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Pipeline is running!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Service URLs:"
echo -e "  ${BLUE}Frontend Dashboard${NC}:  http://localhost:4000"
echo -e "  ${BLUE}Backend API${NC}:         http://localhost:8000"
echo -e "  ${BLUE}API Documentation${NC}:   http://localhost:8000/docs"
echo -e "  ${BLUE}Ollama${NC}:              http://localhost:11434"
echo ""
echo -e "Commands:"
echo -e "  ${CYAN}./scripts/run.sh --logs${NC}    — View live logs"
echo -e "  ${CYAN}./scripts/run.sh --stop${NC}    — Stop all services"
echo -e "  ${CYAN}./scripts/run.sh --eval${NC}    — Run evaluation suite"
echo ""
