#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — Build the LLVM IR Fuzzing Pipeline
#
# Usage:
#   ./scripts/build.sh          # Build all Docker containers
#   ./scripts/build.sh --no-cache   # Force rebuild without Docker cache
#
# Prerequisites:
#   - Docker (v20.10+) and Docker Compose (v2.0+) installed
#   - Ollama installed locally (https://ollama.ai)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  LLVM IR Fuzzing Pipeline — Build${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"

# ── Step 1: Check prerequisites ─────────────────────────────────────────────
echo -e "\n${YELLOW}[1/5] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    echo "  → https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "  ${GREEN}✓ Docker found:${NC} $(docker --version)"

if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    exit 1
fi

COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
fi
echo -e "  ${GREEN}✓ Docker Compose found${NC}"

# ── Step 2: Create data directories ────────────────────────────────────────
echo -e "\n${YELLOW}[2/5] Creating data directories...${NC}"

DATA_DIRS=(
    "backend/data/seeds"
    "backend/data/mutants_llm"
    "backend/data/mutants_grammar"
    "backend/data/mutants_random"
    "backend/data/valid_mutants"
    "backend/data/invalid_mutants"
    "backend/data/logs"
)

for dir in "${DATA_DIRS[@]}"; do
    mkdir -p "$PROJECT_ROOT/$dir"
    echo -e "  ${GREEN}✓${NC} $dir"
done

# ── Step 3: Copy seed test cases ───────────────────────────────────────────
echo -e "\n${YELLOW}[3/5] Deploying seed test cases...${NC}"

SEED_DIR="$PROJECT_ROOT/backend/data/seeds"
TESTCASE_DIR="$PROJECT_ROOT/testcases"

if [ -d "$TESTCASE_DIR" ] && [ "$(ls -A "$TESTCASE_DIR"/*.ll 2>/dev/null)" ]; then
    cp "$TESTCASE_DIR"/*.ll "$SEED_DIR/" 2>/dev/null || true
    SEED_COUNT=$(ls "$SEED_DIR"/*.ll 2>/dev/null | wc -l)
    echo -e "  ${GREEN}✓${NC} $SEED_COUNT seed files deployed to $SEED_DIR"
else
    echo -e "  ${YELLOW}⚠ No .ll files found in testcases/. Seeds directory may be empty.${NC}"
fi

# ── Step 4: Build Docker images ───────────────────────────────────────────
echo -e "\n${YELLOW}[4/5] Building Docker images...${NC}"

BUILD_ARGS=""
if [[ "${1:-}" == "--no-cache" ]]; then
    BUILD_ARGS="--no-cache"
    echo -e "  ${YELLOW}Building with --no-cache${NC}"
fi

cd "$PROJECT_ROOT"
$COMPOSE_CMD build $BUILD_ARGS

echo -e "  ${GREEN}✓ All Docker images built successfully${NC}"

# ── Step 5: Pull LLM model ───────────────────────────────────────────────
echo -e "\n${YELLOW}[5/5] Checking Ollama LLM model...${NC}"

LLM_MODEL="${LLM_MODEL:-qwen2.5:1.5b}"

if command -v ollama &> /dev/null; then
    if ollama list 2>/dev/null | grep -q "$LLM_MODEL"; then
        echo -e "  ${GREEN}✓ Model '$LLM_MODEL' already available${NC}"
    else
        echo -e "  ${YELLOW}Pulling model '$LLM_MODEL'... (this may take a few minutes)${NC}"
        ollama pull "$LLM_MODEL" || echo -e "  ${YELLOW}⚠ Could not pull model. Pull manually: ollama pull $LLM_MODEL${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ Ollama not found locally. The Docker Compose stack includes an Ollama container.${NC}"
    echo -e "  ${YELLOW}  After 'docker compose up', pull the model inside the container:${NC}"
    echo -e "  ${YELLOW}  docker exec -it ollama ollama pull $LLM_MODEL${NC}"
fi

# ── Done ─────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Build complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Next steps:"
echo -e "  ${BLUE}./scripts/run.sh${NC}            — Start all services"
echo -e "  ${BLUE}./scripts/run.sh --eval${NC}     — Start services + run evaluation"
echo ""
