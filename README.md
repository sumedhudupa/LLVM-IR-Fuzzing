# LLVM IR Fuzzing Pipeline

> AI-driven LLVM IR mutation, validity filtering, and differential testing using Ollama LLMs.

## Project Overview

This tool uses large language models (via Ollama) to mutate LLVM IR seed files, validates the output with `llvm-as` and `opt -passes=verify`, then runs differential testing (`-O0` vs `-O2`) to discover compiler bugs.

## Folder Structure

```
.
├── .env                     # Root environment variables
├── docker-compose.yml       # Orchestrates ollama, llm-mutator, llvm-tester
├── seeds/                   # Place seed .ll files here
├── mutants_llm/             # LLM-generated mutants (output)
├── mutants_grammar/          # Grammar-based mutants (output)
├── mutants_random/           # Random baseline mutants (output)
├── valid_mutants/           # Mutants that passed llvm-as + opt verification
├── invalid_mutants/         # Mutants that failed verification
├── logs/                    # CSV/JSON logs + manifest.json
│
├── llm-mutator/             # Python FastAPI service + LLM mutation scripts
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI entry point
│       ├── config.py        # Env var config
│       ├── generate_mutants.py  # LLMMutator + GrammarMutator + RandomMutator
│       ├── filter_valid.py  # llvm-as + opt validation pipeline
│       ├── comparison.py    # compute_comparison_metrics()
│       └── services/
│           ├── manifest_service.py    # ManifestTracker
│           ├── analysis_service.py    # AnalysisService
│           └── differential_service.py
│       └── utils/
│           ├── rule_validation.py     # RuleValidator (7 structural checks)
│           └── ir_helpers.py          # IR extraction, hashing, deduplication
│
├── llvm-tester/             # LLVM 17 container for validation + diff testing
│   ├── Dockerfile
│   └── docker-run.sh
│
└── frontend/                # React (Vite) dashboard
    └── src/
        ├── api.js           # API client
        ├── App.jsx          # Root + navigation
        └── pages/
            ├── SeedList.jsx
            ├── MutationJobForm.jsx
            ├── ValidationStatus.jsx
            ├── DifferentialDashboard.jsx
            └── ComparisonView.jsx    # Per-strategy breakdown, seed sensitivity
```

## Quick Start

### 1. Start Ollama
```bash
ollama serve
# Or via Docker:
docker run -d -p 11434:11434 ollama/ollama
ollama pull qwen2.5:1.5b
```

### 2. Place seed IR files
```bash
cp my_test.ll seeds/
```

### 3. Build and run containers
```bash
docker-compose build
docker-compose up ollama llm-mutator llvm-tester
```

### 4. Use the FastAPI backend
```
GET  http://localhost:8000/api/v1/seeds
POST http://localhost:8000/api/v1/mutants/generate
POST http://localhost:8000/mutants/validate
POST http://localhost:8000/api/v1/differential/run
GET  http://localhost:8000/api/v1/differential/results
GET  http://localhost:8000/api/v1/manifest         # Manifest with all mutant metadata
GET  http://localhost:8000/api/v1/analysis/study-history  # Past study runs
GET  http://localhost:8000/api/v1/analysis/seed-sensitivity # Seed size analysis
```
Interactive docs: http://localhost:8000/docs

### 5. Run the frontend dashboard
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## Mutation Strategies

### LLM Mutator (5 strategies)
1. **arithmetic_substitution** - Replace one arithmetic instruction with another
2. **constant_mutation** - Change one integer constant
3. **icmp_predicate_change** - Flip icmp predicate (eq→ne, slt→sgt)
4. **nop_insertion** - Insert a no-op instruction
5. **branch_condition_flip** - Negate branch condition

### Grammar Mutator (3 strategies)
1. **arithmetic_substitution** - Swap arithmetic operators
2. **icmp_predicate_flip** - Flip comparison predicates
3. **constant_perturbation** - Perturb constant values

### Random Mutator (5 strategies - baseline)
1. **random_char_flip** - Flip a single character
2. **random_line_delete** - Delete one line
3. **random_line_duplicate** - Duplicate one line
4. **random_line_swap** - Swap two adjacent lines
5. **random_word_replace** - Replace LLVM keywords

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
