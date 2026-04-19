# LLVM IR Fuzzing Pipeline

> AI-driven LLVM IR mutation, validity filtering, and differential testing using Ollama LLMs.

## Project Overview

This tool uses large language models (via Ollama) to mutate LLVM IR seed files, validates the output with `llvm-as` and `opt -passes=verify -disable-output`, then runs differential testing (`-O0` vs `-O2`) to discover compiler bugs.

## Folder Structure

```
.
├── .env                     # Root environment variables
├── docker-compose.yml       # Orchestrates ollama, llm-mutator, llvm-tester
├── seeds/                   # Place seed .ll files here
├── mutants_llm/             # LLM-generated mutants (output)
├── mutants_grammar/         # Grammar-based mutants (output)
├── valid_mutants/           # Mutants that passed llvm-as + opt -passes=verify -disable-output
├── invalid_mutants/         # Mutants that failed verification
├── logs/                    # results.csv + validity_logs.json
│
├── llm-mutator/             # Python FastAPI service + LLM mutation scripts
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI entry point (all 5 API endpoints)
│       ├── config.py        # Env var config
│       ├── generate_mutants.py
│       ├── filter_valid.py
│       └── comparison.py
│
├── llvm-tester/             # LLVM 17 container for validation + diff testing
│   ├── Dockerfile
│   └── docker-run.sh
│
└── frontend/                # React (Vite) dashboard
    └── src/
        ├── api.js           # API client (all 5 endpoints)
        ├── App.jsx          # Root + navigation
        └── pages/
            ├── SeedList.jsx
            ├── MutationJobForm.jsx
            ├── ValidationStatus.jsx
            ├── DifferentialDashboard.jsx
            └── ComparisonView.jsx
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
POST http://localhost:8000/api/v1/mutants/validate
POST http://localhost:8000/api/v1/differential/run
GET  http://localhost:8000/api/v1/differential/results
```
Interactive docs: http://localhost:8000/docs

### 5. Run the frontend dashboard
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API URL |
| `LLM_MODEL` | `qwen2.5:1.5b` | Model for IR mutation |
| `SEED_DIR` | `./seeds` | Seed IR directory |
| `MUTANT_DIR` | `./mutants_llm` | LLM mutant output dir |
| `GRAMMAR_DIR` | `./mutants_grammar` | Grammar mutant dir |
| `VALID_DIR` | `./valid_mutants` | Verified-valid mutants |
| `INVALID_DIR` | `./invalid_mutants` | Failed mutants |
| `LOGS_DIR` | `./logs` | CSV/JSON logs |
