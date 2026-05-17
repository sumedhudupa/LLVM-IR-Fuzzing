# LLVM IR Fuzzing Pipeline

> AI-driven LLVM IR mutation, validity filtering, and differential testing using Ollama or Groq LLMs.

## Project Overview

This tool uses large language models (via Ollama or Groq) to mutate LLVM IR seed files, validates the output with `llvm-as` and `opt -passes=verify`, then runs differential testing (`-O0` vs `-O2`) to discover compiler bugs. The system features three mutation strategies (LLM-guided, grammar-based, and random), comprehensive validation with rule-based pre-checks, IR deduplication, and a React-based dashboard for monitoring and analysis.

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

Configure the system using environment variables in `.env` or via Docker Compose:

### Core Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | LLM provider used by `mutator_type="llm"` (`ollama` or `groq`) |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API endpoint URL |
| `LLM_MODEL` | `qwen2.5:1.5b` | LLM model for IR mutation |

### Groq Configuration (when `LLM_PROVIDER=groq`)

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Groq API key (preferred). `GROK_API_KEY` is supported as a legacy alias |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq OpenAI-compatible base URL |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model used for mutation |
| `GROQ_MAX_TOKENS` | `1500` | Max tokens for the mutation response |
| `GROQ_REASONING_FORMAT` | *(empty)* | For Qwen reasoning models set to `hidden` to avoid thinking tokens |
| `GROQ_MAX_RETRIES` | `6` | Retries on rate limit (HTTP 429) and transient 5xx |
| `GROQ_RETRY_BASE_SLEEP_S` | `1.0` | Base sleep seconds for exponential backoff |
| `GROQ_RETRY_MAX_SLEEP_S` | `30.0` | Max sleep seconds per retry (cap) |

Recommended Groq models (ranked for single-edit LLVM IR mutation):
- Tier 1: `qwen/qwen-3-32b` (preview; use `GROQ_REASONING_FORMAT=hidden`), `llama-3.3-70b-versatile` (production), `moonshotai/kimi-k2-instruct-0905` (preview; large context)
- Tier 2: `openai/gpt-oss-20b`, `meta-llama/llama-4-scout-17b-16e-instruct`
- Tier 3 (avoid): `llama-3.1-8b-instant`, `openai/gpt-oss-120b`

### Directory Paths

| Variable | Default | Description |
|---|---|---|
| `SEED_DIR` | `./backend/data/seeds` | Seed IR files directory |
| `MUTANT_DIR` | `./backend/data/mutants_llm` | LLM mutant output directory |
| `GRAMMAR_DIR` | `./backend/data/mutants_grammar` | Grammar mutant output directory |
| `RANDOM_DIR` | `./backend/data/mutants_random` | Random mutant output directory |
| `VALID_DIR` | `./backend/data/valid_mutants` | Validated mutants directory |
| `INVALID_DIR` | `./backend/data/invalid_mutants` | Failed mutants directory |
| `LOGS_DIR` | `./backend/data/logs` | Logs and manifest directory |

### Feature Flags

| Variable | Default | Description |
|---|---|---|
| `ENABLE_RULE_VALIDATION` | `true` | Enable pre-validation structural checks (7 rules) |
| `ENABLE_DEDUPLICATION` | `true` | Enable IR hash-based deduplication |
| `ENABLE_REFINEMENT` | `false` | Enable LLM refinement loop on validation errors |

### Performance & Limits

| Variable | Default | Description |
|---|---|---|
| `VALIDATION_TIMEOUT` | `30` | Subprocess timeout in seconds for validation |
| `MAX_REFINEMENT_ATTEMPTS` | `3` | Maximum LLM refinement iterations |
| `MAX_WORKERS` | `4` | Parallel workers for batch operations |

### Frontend Configuration

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL for frontend |

### Example `.env` File

```bash
# Core
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=qwen2.5:1.5b

# Groq (when LLM_PROVIDER=groq)
# GROQ_API_KEY=your-key-here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MAX_TOKENS=1500
# GROQ_REASONING_FORMAT=hidden

# Groq retry/backoff (handles 429 Too Many Requests)
GROQ_MAX_RETRIES=6
GROQ_RETRY_BASE_SLEEP_S=1.0
GROQ_RETRY_MAX_SLEEP_S=30.0

# Paths (relative to project root)
SEED_DIR=./backend/data/seeds
MUTANT_DIR=./backend/data/mutants_llm
GRAMMAR_DIR=./backend/data/mutants_grammar
RANDOM_DIR=./backend/data/mutants_random
VALID_DIR=./backend/data/valid_mutants
INVALID_DIR=./backend/data/invalid_mutants
LOGS_DIR=./backend/data/logs

# Features
ENABLE_RULE_VALIDATION=true
ENABLE_DEDUPLICATION=true
ENABLE_REFINEMENT=false

# Performance
VALIDATION_TIMEOUT=30
MAX_REFINEMENT_ATTEMPTS=3
MAX_WORKERS=4
```

## Testing

The project includes comprehensive test suites for validation and integration testing.

### Test Structure

```
backend/api/tests/
├── test_phase3.py          # Manifest tracking tests (16 tests)
├── test_phase4.py          # Integration tests (38 tests)
└── verify_mutators.py      # Mutator verification utilities
```

### Running Tests

#### Run All Tests
```bash
cd backend/api
python -m pytest tests/ -v
```

#### Run Specific Test Suites
```bash
# Manifest tracking tests
python -m pytest tests/test_phase3.py -v

# Integration tests
python -m pytest tests/test_phase4.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

#### Run Specific Test Cases
```bash
# Run a specific test function
python -m pytest tests/test_phase3.py::test_manifest_creation -v

# Run tests matching a pattern
python -m pytest tests/ -k "validation" -v
```

### Test Coverage

The test suites cover:

#### Phase 3 Tests (Manifest Tracking)
- Manifest creation and initialization
- Mutant metadata tracking
- Summary statistics computation
- Breakdown by mutator type
- Error type classification
- Duplicate detection
- Trivial mutant identification
- JSON serialization/deserialization

#### Phase 4 Tests (Integration)
- End-to-end mutation pipeline
- LLM mutator integration with Ollama
- Grammar mutator rule application
- Random mutator strategies
- Validation pipeline (llvm-as + opt)
- Rule-based pre-validation (7 structural checks)
- IR deduplication using hash computation
- Differential testing workflow
- API endpoint integration
- Error handling and edge cases

### Test Data

Test fixtures are located in:
```
backend/test_data/
├── seeds/              # Test seed files
├── expected/           # Expected outputs
└── fixtures/           # Test fixtures
```

### Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    cd backend/api
    pip install -r requirements.txt
    pip install pytest pytest-cov
    pytest tests/ -v --cov=app
```

### Writing New Tests

Follow these conventions:

1. **Test file naming**: `test_*.py`
2. **Test function naming**: `test_<feature>_<scenario>`
3. **Use fixtures**: Define reusable fixtures in `conftest.py`
4. **Mock external services**: Mock Ollama API calls for unit tests
5. **Clean up**: Ensure tests clean up generated files

Example test:
```python
import pytest
from app.services.mutant_service import MutantService

def test_generate_llm_mutants_success(mock_ollama):
    """Test successful LLM mutant generation."""
    service = MutantService()
    result = service.generate_mutants(
        seed_names=["test_seed.ll"],
        mutator_type="llm",
        count=5
    )
    assert result["generated"] == 5
    assert len(result["mutant_ids"]) == 5
```

## API Endpoints

### Seeds Management

#### `GET /api/v1/seeds`
List all available seed IR files with metadata.

**Response:**
```json
{
  "seeds": [
    {
      "name": "seed_arith.ll",
      "size_bytes": 1234,
      "path": "/data/seeds/seed_arith.ll"
    }
  ]
}
```

### Mutant Generation

#### `POST /api/v1/mutants/generate`
Generate mutants from seed files.

**Request:**
```json
{
  "seed_names": ["seed_arith.ll", "seed_branch.ll"],
  "mutator_type": "llm",  // "llm", "grammar", or "random"
  "count": 10
}
```

**Response:**
```json
{
  "generated": 20,
  "mutant_ids": ["seed_arith_llm_mut_0", "seed_arith_llm_mut_1", ...],
  "mutator_type": "llm",
  "timestamp": "2026-05-01T12:00:00Z"
}
```

#### `GET /api/v1/mutants`
List all generated mutants with filtering options.

**Query Parameters:**
- `mutator_type`: Filter by mutator (llm/grammar/random)
- `is_valid`: Filter by validation status (true/false)
- `seed_name`: Filter by source seed

### Validation

#### `POST /api/v1/mutants/validate`
Validate mutants using llvm-as and opt.

**Request:**
```json
{
  "mutant_ids": ["seed_arith_llm_mut_0", "seed_arith_llm_mut_1"]
}
```

**Response:**
```json
{
  "results": [
    {
      "mutant_id": "seed_arith_llm_mut_0",
      "is_valid": true,
      "error_type": null,
      "error_message": null,
      "is_trivial": false,
      "is_duplicate": false
    },
    {
      "mutant_id": "seed_arith_llm_mut_1",
      "is_valid": false,
      "error_type": "syntax_error",
      "error_message": "expected instruction opcode",
      "is_trivial": false,
      "is_duplicate": false
    }
  ],
  "summary": {
    "total": 2,
    "valid": 1,
    "invalid": 1
  }
}
```

### Differential Testing

#### `POST /api/v1/differential/run`
Run differential testing on valid mutants.

**Request:**
```json
{
  "mutant_ids": ["seed_arith_llm_mut_0"],
  "optimization_levels": ["-O0", "-O2"],
  "timeout": 30
}
```

**Response:**
```json
{
  "run_id": "diff_run_20260501_120000",
  "total_mutants": 1,
  "completed": 1,
  "mismatches_found": 0,
  "timestamp": "2026-05-01T12:00:00Z"
}
```

#### `GET /api/v1/differential/results`
Get differential testing results.

**Query Parameters:**
- `run_id`: Filter by specific run
- `mismatch_only`: Show only mismatches (true/false)

**Response:**
```json
{
  "results": [
    {
      "mutant_id": "seed_arith_llm_mut_0",
      "optimization_levels": ["-O0", "-O2"],
      "has_mismatch": false,
      "output_o0": "42\n",
      "output_o2": "42\n",
      "mismatch_type": null
    }
  ]
}
```

### Manifest & Tracking

#### `GET /api/v1/manifest`
Get comprehensive manifest with all mutant metadata.

**Response:**
```json
{
  "mutants": [
    {
      "mutant_id": "seed_arith_llm_mut_0",
      "source_seed": "seed_arith.ll",
      "mutator_type": "llm",
      "mutation_strategy": "arithmetic_substitution",
      "is_valid": true,
      "is_trivial": false,
      "is_duplicate": false,
      "error_type": null,
      "generated_at": "2026-05-01T12:00:00Z",
      "validated_at": "2026-05-01T12:01:00Z"
    }
  ],
  "summary": {
    "total_generated": 100,
    "valid_count": 75,
    "invalid_count": 25,
    "trivial_count": 5,
    "duplicate_count": 3,
    "by_mutator": {
      "llm": {"total": 50, "valid": 40, "invalid": 10},
      "grammar": {"total": 30, "valid": 28, "invalid": 2},
      "random": {"total": 20, "valid": 7, "invalid": 13}
    },
    "by_error_type": {
      "syntax_error": 15,
      "type_error": 5,
      "undefined_reference": 3,
      "invalid_operand": 2
    }
  }
}
```

### Analysis & Studies

#### `GET /api/v1/analysis/study-history`
Get history of controlled study runs.

**Response:**
```json
{
  "studies": [
    {
      "run_id": "study_20260501_120000",
      "started_at": "2026-05-01T12:00:00Z",
      "completed_at": "2026-05-01T12:30:00Z",
      "settings": {
        "seeds": ["seed_arith.ll", "seed_branch.ll"],
        "count_per_seed": 10,
        "optimization_levels": ["-O0", "-O2"]
      },
      "metrics": {
        "total_mutants": 20,
        "validity_rate": 0.75,
        "mismatch_rate": 0.05
      }
    }
  ]
}
```

#### `GET /api/v1/analysis/seed-sensitivity`
Analyze validity rates by seed size.

**Response:**
```json
{
  "sensitivity_data": [
    {
      "seed_name": "seed_arith.ll",
      "seed_size_bytes": 1234,
      "llm": {
        "generated": 10,
        "valid": 8,
        "validity_rate": 0.8
      },
      "grammar": {
        "generated": 10,
        "valid": 9,
        "validity_rate": 0.9
      },
      "random": {
        "generated": 10,
        "valid": 3,
        "validity_rate": 0.3
      }
    }
  ]
}
```

#### `GET /api/v1/analysis/comparison`
Get comparison metrics across mutator types.

**Response:**
```json
{
  "llm": {
    "total_generated": 50,
    "validity_rate": 0.80,
    "avg_generation_time_ms": 1500,
    "strategies": {
      "arithmetic_substitution": {"count": 10, "validity_rate": 0.9},
      "constant_mutation": {"count": 10, "validity_rate": 0.8}
    }
  },
  "grammar": {
    "total_generated": 30,
    "validity_rate": 0.93,
    "avg_generation_time_ms": 50
  },
  "random": {
    "total_generated": 20,
    "validity_rate": 0.35,
    "avg_generation_time_ms": 10
  }
}
```

### Health Check

#### `GET /health`
Check service health and dependencies.

**Response:**
```json
{
  "status": "healthy",
  "ollama_connected": true,
  "llvm_available": true,
  "timestamp": "2026-05-01T12:00:00Z"
}
```

## Differential Testing

The pipeline compares LLM vs Grammar vs Random mutants:
1. Generate mutants from diverse seed files
2. Validate with LLVM tools (llvm-as + opt -passes=verify)
3. Run differential testing (-O0 vs -O2)
4. Compare mismatch rates across mutator types

## Advanced Features

### 1. Rule-Based Pre-Validation

The `RuleValidator` performs 7 structural checks before expensive LLVM validation:

1. **Non-empty check**: Ensures IR is not empty
2. **Basic structure**: Verifies presence of essential LLVM IR elements
3. **Balanced braces**: Checks for balanced `{` and `}`
4. **Function definition**: Ensures at least one function is defined
5. **Valid instructions**: Checks for known LLVM instruction opcodes
6. **Type consistency**: Basic type checking for operations
7. **SSA form**: Validates Single Static Assignment properties

**Benefits:**
- Reduces validation time by ~40%
- Catches trivial errors early
- Provides detailed error classification

**Configuration:**
```bash
ENABLE_RULE_VALIDATION=true  # Enable pre-validation
```

### 2. IR Deduplication

The system uses IR hashing to detect duplicate mutants:

**How it works:**
1. Extract normalized IR (strip comments, whitespace)
2. Compute SHA-256 hash of normalized IR
3. Compare against existing hashes in manifest
4. Mark duplicates and skip redundant validation

**Benefits:**
- Eliminates redundant validation work
- Tracks unique vs duplicate mutants
- Improves study quality metrics

**Configuration:**
```bash
ENABLE_DEDUPLICATION=true  # Enable deduplication
```

**Implementation:**
```python
# From app/utils/ir_helpers.py
def compute_ir_hash(ir_code: str) -> str:
    """Compute SHA-256 hash of normalized IR."""
    normalized = normalize_ir(ir_code)
    return hashlib.sha256(normalized.encode()).hexdigest()
```

### 3. LLM Refinement Loop

When enabled, the system attempts to fix invalid mutants using LLM feedback:

**Workflow:**
1. Generate mutant with LLM
2. Validate with llvm-as + opt
3. If invalid, extract error message
4. Send error + original IR back to LLM with refinement prompt
5. Repeat up to `MAX_REFINEMENT_ATTEMPTS` times
6. Accept best valid result or mark as invalid

**Configuration:**
```bash
ENABLE_REFINEMENT=true       # Enable refinement loop
MAX_REFINEMENT_ATTEMPTS=3    # Maximum iterations
```

**Use cases:**
- Improve LLM mutant validity rate
- Learn from validation errors
- Generate higher-quality mutants

**Trade-offs:**
- Increases generation time (3x-5x)
- Higher LLM API usage
- May converge to trivial mutations

### 4. Manifest Tracking

The `ManifestService` maintains comprehensive metadata for all mutants:

**Tracked data:**
- Mutant ID and source seed
- Mutator type and strategy
- Validation status and error details
- Trivial/duplicate flags
- Generation and validation timestamps
- IR hash for deduplication

**Storage:**
```json
// backend/data/logs/manifest.json
{
  "mutants": [...],
  "summary": {
    "total_generated": 100,
    "valid_count": 75,
    "by_mutator": {...},
    "by_error_type": {...}
  },
  "last_updated": "2026-05-01T12:00:00Z"
}
```

### 5. Differential Testing

Compares program outputs across optimization levels to find compiler bugs:

**Process:**
1. Compile valid mutant with multiple optimization levels
2. Execute each binary with same inputs
3. Compare outputs (stdout, stderr, exit code)
4. Classify mismatches by type

**Mismatch types:**
- `output_mismatch`: Different stdout/stderr
- `crash_mismatch`: One crashes, other doesn't
- `timeout_mismatch`: Different execution times
- `exit_code_mismatch`: Different exit codes

**Configuration:**
```python
# Example differential run
{
  "mutant_ids": ["seed_arith_llm_mut_0"],
  "optimization_levels": ["-O0", "-O1", "-O2", "-O3"],
  "timeout": 30
}
```

### 6. Study History & Analysis

The `AnalysisService` tracks controlled study runs for reproducibility:

**Features:**
- Study run metadata (settings, timestamps)
- Aggregate metrics (validity rates, mismatch rates)
- Seed sensitivity analysis (validity vs seed size)
- Mutator comparison (LLM vs Grammar vs Random)
- Historical trends and patterns

**Storage:**
```jsonl
// backend/data/logs/study_runs.jsonl (newline-delimited JSON)
{"run_id": "study_001", "started_at": "...", "metrics": {...}}
{"run_id": "study_002", "started_at": "...", "metrics": {...}}
```

### 7. Semantic Helpers

Utility functions for IR analysis and manipulation:

- **Function extraction**: Parse function definitions from IR
- **Instruction counting**: Count instructions by type
- **Control flow analysis**: Identify branches and loops
- **Type inference**: Infer LLVM types from operations
- **Constant extraction**: Find all constant values

**Example usage:**
```python
from app.utils.semantic_helpers import extract_functions, count_instructions

functions = extract_functions(ir_code)
stats = count_instructions(ir_code)
# stats = {"add": 5, "mul": 3, "icmp": 2, ...}
```

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed

**Symptom:** `Connection refused` or `Ollama not reachable`

**Solutions:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check Docker network (if using Docker)
docker network inspect bridge

# Update OLLAMA_HOST in .env
OLLAMA_HOST=http://host.docker.internal:11434  # For Docker
OLLAMA_HOST=http://localhost:11434             # For local
```

#### 2. Model Not Found

**Symptom:** `Model 'qwen2.5:1.5b' not found`

**Solutions:**
```bash
# Pull the model
ollama pull qwen2.5:1.5b

# List available models
ollama list

# Use a different model
export LLM_MODEL=llama2:7b
```

#### 2b. Groq Rate Limit (HTTP 429)

**Symptom:** `429 Too Many Requests` while generating mutants with `LLM_PROVIDER=groq`

**Solutions:**
- Reduce request volume: lower `count`, increase time between runs
- Reduce token usage: lower `GROQ_MAX_TOKENS` if output truncation is not occurring
- Tune retry/backoff: `GROQ_MAX_RETRIES`, `GROQ_RETRY_BASE_SLEEP_S`, `GROQ_RETRY_MAX_SLEEP_S`

#### 3. LLVM Tools Not Found

**Symptom:** `llvm-as: command not found`

**Solutions:**
```bash
# Install LLVM 17 (Ubuntu/Debian)
sudo apt-get install llvm-17

# Add to PATH
export PATH=/usr/lib/llvm-17/bin:$PATH

# Verify installation
llvm-as --version
opt --version

# Use Docker (recommended)
docker-compose up llvm-tester
```

#### 4. Permission Denied on Data Directories

**Symptom:** `Permission denied: '/data/seeds'`

**Solutions:**
```bash
# Fix permissions
chmod -R 755 backend/data/
chown -R $USER:$USER backend/data/

# For Docker
docker-compose down
docker-compose up --build
```

#### 5. Frontend Can't Connect to Backend

**Symptom:** `Network Error` or `CORS error`

**Solutions:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Update frontend API URL
export VITE_API_BASE_URL=http://localhost:8000

# Check CORS settings in backend
# app/main.py should have:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 6. High Memory Usage

**Symptom:** System slowdown or OOM errors

**Solutions:**
```bash
# Limit parallel workers
export MAX_WORKERS=2

# Reduce batch sizes in API calls
# Use smaller mutation counts per request

# Monitor Docker resources
docker stats

# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory
```

#### 7. Validation Timeout

**Symptom:** `Validation timeout after 30 seconds`

**Solutions:**
```bash
# Increase timeout
export VALIDATION_TIMEOUT=60

# Check for infinite loops in mutants
# Review mutant IR for obvious issues

# Disable refinement loop (faster)
export ENABLE_REFINEMENT=false
```

#### 8. Duplicate Mutants

**Symptom:** High duplicate rate in manifest

**Solutions:**
```bash
# Enable deduplication
export ENABLE_DEDUPLICATION=true

# Increase mutation diversity
# Use different seeds
# Increase mutation count
# Try different mutator types

# Check mutator strategies
# Ensure strategies are producing varied mutations
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Backend
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug

# View logs
tail -f backend/data/logs/*.log

# Docker logs
docker-compose logs -f backend
docker-compose logs -f llvm-tester
```

### Performance Optimization

```bash
# Use faster mutator for testing
mutator_type="grammar"  # Faster than LLM

# Disable expensive features
ENABLE_REFINEMENT=false
ENABLE_RULE_VALIDATION=false  # Not recommended

# Batch operations
# Generate mutants in batches of 10-20
# Validate in parallel batches

# Use SSD for data directories
# Mount backend/data/ on fast storage
```

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: `backend/data/logs/` contains detailed logs
2. **Review manifest**: `backend/data/logs/manifest.json` shows mutant status
3. **Test API**: Use `/docs` endpoint for interactive API testing
4. **Verify setup**: Run health check endpoint `/health`
5. **Check dependencies**: Ensure all prerequisites are installed

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Write tests**: Ensure new features have test coverage
4. **Follow code style**: Use Black for Python, ESLint for JavaScript
5. **Update documentation**: Update README and docstrings
6. **Submit a pull request**: Describe your changes clearly

### Development Setup

```bash
# Backend
cd backend/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install black pytest pytest-cov

# Frontend
cd frontend
npm install
npm run lint

# Pre-commit hooks
pip install pre-commit
pre-commit install
```

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{llvm_ir_fuzzing_pipeline,
  title = {LLVM IR Fuzzing Pipeline: AI-Driven Compiler Testing},
  author = {Your Name},
  year = {2026},
  url = {https://github.com/yourusername/llvm-ir-fuzzing}
}
```

## Acknowledgments

- **Ollama** for providing the LLM inference engine
- **LLVM Project** for the compiler infrastructure
- **FastAPI** for the backend framework
- **React** and **Vite** for the frontend framework
