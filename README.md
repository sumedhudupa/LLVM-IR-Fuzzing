# LLVM IR Fuzzing Pipeline

> AI-driven LLVM IR mutation, validity filtering, and differential testing using Ollama LLMs.

## Project Overview

This tool uses large language models (via Ollama) to mutate LLVM IR seed files, validates the output with `llvm-as` and `opt -passes=verify`, then runs differential testing (`-O0` vs `-O2`) to discover compiler bugs. The system features three mutation strategies (LLM-guided, grammar-based, and random), comprehensive validation with rule-based pre-checks, IR deduplication, and a React-based dashboard for monitoring and analysis.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Quick Start](#quick-start)
- [Mutation Strategies](#mutation-strategies)
- [Frontend Dashboard](#frontend-dashboard)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before running this project, ensure you have:

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Python** 3.9+ (for local development/testing)
- **Node.js** 18+ and **npm** (for frontend development)
- **LLVM 17** (included in Docker containers)
- **Ollama** with `qwen2.5:1.5b` model (or your preferred LLM)

## Architecture

The project follows a modular microservices architecture:

### Backend (FastAPI)
```
backend/api/app/
├── main.py                  # FastAPI application entry point
├── config.py                # Centralized configuration
├── generate_mutants.py      # Mutation orchestration
├── filter_valid.py          # Validation pipeline
├── comparison.py            # Metrics computation
├── models/                  # Pydantic schemas
│   ├── mutants.py          # Mutant request/response models
│   ├── differential.py     # Differential testing models
│   ├── seeds.py            # Seed file models
│   └── analysis.py         # Analysis and study models
├── routes/                  # API route handlers
│   ├── mutants.py          # Mutant generation/validation endpoints
│   ├── differential.py     # Differential testing endpoints
│   ├── seeds.py            # Seed management endpoints
│   └── analysis.py         # Analysis and study endpoints
├── services/                # Business logic layer
│   ├── mutant_service.py   # Mutation orchestration
│   ├── manifest_service.py # Manifest tracking and metadata
│   ├── differential_service.py # Differential testing logic
│   ├── analysis_service.py # Study history and seed sensitivity
│   └── seed_service.py     # Seed file management
└── utils/                   # Utility modules
    ├── rule_validation.py  # RuleValidator (7 structural checks)
    ├── ir_helpers.py       # IR extraction, hashing, deduplication
    ├── semantic_helpers.py # Semantic analysis utilities
    ├── fs_helpers.py       # File system operations
    └── logger.py           # Logging configuration
```

### Data Flow
1. **Mutation**: Seeds → LLMMutator/GrammarMutator/RandomMutator → Raw mutants
2. **Pre-validation**: RuleValidator checks (7 structural rules)
3. **Validation**: llvm-as + opt -passes=verify → Valid/Invalid classification
4. **Deduplication**: IR hash computation → Duplicate detection
5. **Differential Testing**: Compile with -O0 and -O2 → Compare outputs
6. **Analysis**: Aggregate metrics, study history, seed sensitivity

### Frontend (React + Vite)
```
frontend/src/
├── main.jsx                 # Application entry point
├── App.jsx                  # Root component with routing
├── api.js                   # API client wrapper
└── pages/
    ├── SeedList.jsx        # Browse and manage seed files
    ├── MutationJobForm.jsx # Configure and trigger mutation jobs
    ├── ValidationStatus.jsx # View validation results
    ├── DifferentialDashboard.jsx # Differential testing results
    └── ComparisonView.jsx  # Compare mutator strategies
```

## Folder Structure

```
.
├── .env                     # Root environment variables
├── docker-compose.yml       # Orchestrates ollama, backend, llvm-tester, frontend
│
├── backend/                 # Backend services and data
│   ├── api/                # FastAPI application
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/            # Application code (see Architecture)
│   │   └── tests/          # Test suites
│   │       ├── test_phase3.py      # Manifest tests (16 tests)
│   │       ├── test_phase4.py      # Integration tests (38 tests)
│   │       └── verify_mutators.py  # Mutator verification
│   ├── llvm-tester/        # LLVM 17 validation container
│   │   ├── Dockerfile
│   │   └── docker-run.sh
│   ├── data/               # Runtime data directories
│   │   ├── seeds/          # Place seed .ll files here
│   │   ├── mutants_llm/    # LLM-generated mutants
│   │   ├── mutants_grammar/ # Grammar-based mutants
│   │   ├── mutants_random/ # Random baseline mutants
│   │   ├── valid_mutants/  # Validated mutants
│   │   ├── invalid_mutants/ # Failed validation
│   │   └── logs/           # CSV/JSON logs + manifest.json
│   └── test_data/          # Test fixtures and outputs
│
└── frontend/               # React dashboard
    ├── Dockerfile
    ├── package.json
    └── src/                # Frontend source (see Architecture)
```

## Quick Start

### Option 1: Docker Compose (Recommended)

1. **Start Ollama and pull the model**
```bash
# Start Ollama service
ollama serve

# Pull the LLM model
ollama pull qwen2.5:1.5b
```

2. **Place seed IR files**
```bash
# Copy your LLVM IR seed files to the backend data directory
cp my_test.ll backend/data/seeds/
```

3. **Build and run all services**
```bash
# Build all containers
docker-compose build

# Start all services (ollama, backend, llvm-tester, frontend)
docker-compose up
```

4. **Access the services**
- **Frontend Dashboard**: http://localhost:4000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Ollama**: http://localhost:11434

### Option 2: Local Development

#### Backend Setup
```bash
cd backend/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or use .env file)
export OLLAMA_HOST=http://localhost:11434
export LLM_MODEL=qwen2.5:1.5b
export SEED_DIR=../data/seeds
export MUTANT_DIR=../data/mutants_llm
# ... (see Environment Variables section)

# Run the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Set API base URL
export VITE_API_BASE_URL=http://localhost:8000

# Run development server
npm run dev
# → http://localhost:5173

# Build for production
npm run build
npm run preview
```

### Quick API Test

```bash
# List available seeds
curl http://localhost:8000/api/v1/seeds

# Generate mutants
curl -X POST http://localhost:8000/api/v1/mutants/generate \
  -H "Content-Type: application/json" \
  -d '{
    "seed_names": ["seed_arith.ll"],
    "mutator_type": "llm",
    "count": 5
  }'

# Validate mutants
curl -X POST http://localhost:8000/api/v1/mutants/validate \
  -H "Content-Type: application/json" \
  -d '{
    "mutant_ids": ["seed_arith_llm_mut_0", "seed_arith_llm_mut_1"]
  }'

# Get manifest
curl http://localhost:8000/api/v1/manifest
```

## Mutation Strategies

The system implements three complementary mutation approaches to maximize bug discovery:

### LLM Mutator (5 strategies)
Uses Ollama LLMs (qwen2.5:1.5b) to generate semantically-aware mutations:

1. **arithmetic_substitution** - Replace arithmetic instructions (add→sub, mul→sdiv)
2. **constant_mutation** - Intelligently modify integer constants
3. **icmp_predicate_change** - Flip comparison predicates (eq→ne, slt→sgt, ult→ugt)
4. **nop_insertion** - Insert no-op instructions at strategic points
5. **branch_condition_flip** - Negate branch conditions

**Features:**
- Context-aware mutations using LLM understanding
- Optional refinement loop (configurable via `ENABLE_REFINEMENT`)
- Tightly scoped prompts optimized for small models
- Error-guided refinement with up to 3 attempts

### Grammar Mutator (3 strategies)
Deterministic rule-based mutations following LLVM IR grammar:

1. **arithmetic_substitution** - Systematic arithmetic operator replacement
2. **icmp_predicate_flip** - Predicate inversion following LLVM semantics
3. **constant_perturbation** - Controlled constant value perturbation (±1 to ±3)

**Features:**
- Guaranteed syntactic validity
- Deterministic and reproducible
- Fast generation (no LLM overhead)
- Baseline for comparing LLM effectiveness

### Random Mutator (5 strategies)
Non-grammar-aware baseline for comparison:

1. **random_char_flip** - Flip single characters to different characters
2. **random_line_delete** - Remove random lines from IR
3. **random_line_duplicate** - Duplicate random lines
4. **random_line_swap** - Swap adjacent lines
5. **random_word_replace** - Replace LLVM keywords with similar-looking words

**Features:**
- Stress-tests validator robustness
- Generates high invalid rate (expected)
- Baseline for measuring mutation quality
- Useful for finding parser edge cases

## Frontend Dashboard

The React-based dashboard provides comprehensive monitoring and analysis:

### Pages

#### 1. Seed List (`/seeds`)
- Browse all available seed IR files
- View seed metadata (size, lines, functions)
- Upload new seed files
- Delete or download seeds

#### 2. Mutation Job Form (`/mutate`)
- Configure mutation jobs
- Select seeds and mutator type (LLM/Grammar/Random)
- Set mutation count per seed
- Trigger batch mutation generation
- Real-time job status updates

#### 3. Validation Status (`/validate`)
- View validation results for all mutants
- Filter by validity status (valid/invalid/pending)
- See error classifications and types
- Inspect individual mutant IR code
- Batch validation operations

#### 4. Differential Dashboard (`/differential`)
- Configure differential testing runs
- Select optimization levels (-O0, -O1, -O2, -O3)
- View mismatch detection results
- Analyze output differences
- Export results for further analysis

#### 5. Comparison View (`/comparison`)
- Compare mutator effectiveness (LLM vs Grammar vs Random)
- Validity rate analysis by mutator type
- Seed sensitivity analysis (validity vs seed size)
- Per-strategy breakdown and metrics
- Study history and trends
- Export comparison reports

### Features
- **Real-time updates**: Live status monitoring
- **Responsive design**: Works on desktop and mobile
- **Data visualization**: Charts and graphs for metrics
- **Export capabilities**: Download results as CSV/JSON
- **Error handling**: User-friendly error messages

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API URL |
| `LLM_MODEL` | `qwen2.5:1.5b` | Model for IR mutation |
| `SEED_DIR` | `./seeds` | Seed IR directory |
| `MUTANT_DIR` | `./mutants_llm` | LLM mutant output dir |
| `GRAMMAR_DIR` | `./mutants_grammar` | Grammar mutant dir |
| `RANDOM_DIR` | `./mutants_random` | Random mutant dir |
| `VALID_DIR` | `./valid_mutants` | Verified-valid mutants |
| `INVALID_DIR` | `./invalid_mutants` | Failed mutants |
| `LOGS_DIR` | `./logs` | CSV/JSON logs |
| `VALIDATION_TIMEOUT` | `30` | Subprocess timeout (seconds) |
| `ENABLE_RULE_VALIDATION` | `true` | Enable pre-validation checks |
| `ENABLE_DEDUPLICATION` | `true` | Enable IR deduplication |
| `ENABLE_REFINEMENT` | `false` | Enable LLM refinement loop |

## Testing

```bash
# Run all tests
cd llm-mutator
python -m pytest tests/ -v

# Phase 3 manifest tests (16 tests)
python -m pytest tests/test_phase3.py -v

# Phase 4 integration tests (38 tests)
python -m pytest tests/test_phase4.py -v
```

## API Endpoints

### Manifest Tracking (`GET /api/v1/manifest`)
Returns comprehensive manifest with all mutant metadata:
- Per-mutant entries: mutant_id, source, mutation_type, is_valid, trivial, is_duplicate
- Summary statistics: total_generated, valid_count, invalid_count, trivial_count
- Breakdown by mutator_type and error_type

### Study History (`GET /api/v1/analysis/study-history`)
Returns past controlled study runs with:
- run_id, started_at, completed_at
- Settings (seeds, count, optimization levels)
- Aggregate metrics (validity_rate, mismatch_rate)

### Seed Sensitivity (`GET /api/v1/analysis/seed-sensitivity`)
Returns validity rates grouped by seed file:
- seed_name, seed_size_bytes
- LLM: generated, validity_rate
- Grammar: generated, validity_rate

## Differential Testing

The pipeline compares LLM vs Grammar vs Random mutants:
1. Generate mutants from diverse seed files
2. Validate with LLVM tools (llvm-as + opt -passes=verify)
3. Run differential testing (-O0 vs -O2)
4. Compare mismatch rates across mutator types
