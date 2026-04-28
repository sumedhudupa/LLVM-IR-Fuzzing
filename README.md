# LLVM IR Fuzzing Pipeline

> AI-driven LLVM IR mutation, validity filtering, and differential testing.

This repository now contains **two complementary workflows**:

1. **Containerized Ollama pipeline** (frontend + FastAPI + LLVM tester)
2. **Research experiment runner** (LLM vs grammar vs random baselines, paper figures)

Both workflows share the same research goal: generating LLVM IR test cases, validating them,
and comparing their effectiveness for differential compiler testing.

---

## 1) Pipeline Workflow (Ollama + Docker)

### Folder Structure

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

### Quick Start

1) Start Ollama
```bash
ollama serve
# Or via Docker:
docker run -d -p 11434:11434 ollama/ollama
ollama pull qwen2.5:1.5b
```

2) Place seed IR files
```bash
cp my_test.ll seeds/
```

3) Build and run containers
```bash
docker-compose build
docker-compose up ollama llm-mutator llvm-tester
```

4) Use the FastAPI backend
```
GET  http://localhost:8000/api/v1/seeds
POST http://localhost:8000/api/v1/mutants/generate
POST http://localhost:8000/api/v1/mutants/validate
POST http://localhost:8000/api/v1/differential/run
GET  http://localhost:8000/api/v1/differential/results
```
Interactive docs: http://localhost:8000/docs

5) Run the frontend dashboard
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 2) Research Experiment Workflow (Paper Artifacts)

This workflow powers the controlled study reported in `report.md` and
generates the figures used in the paper.

### Project Structure

```
├── report.md                          # Full research report
├── constraints_catalog.md             # LLVM IR validity constraints catalog
├── src/
│   ├── ir_generator.py                # LLM-based LLVM IR generation/mutation
│   ├── ir_validator.py                # Multi-stage IR validation pipeline
│   ├── grammar_mutator.py             # Grammar-based mutation baseline
│   ├── differential_tester.py         # Differential testing across opt levels
│   ├── failure_analyzer.py            # Failure case analysis
│   ├── experiment_runner.py           # Main experiment orchestration
│   └── utils.py                       # Shared utilities
├── seed_ir/
│   └── seeds.py                       # LLVM IR seed cases
└── results/
    ├── experiment_results.json        # Raw experiment data
    ├── analysis_output.md             # Generated analysis report
    └── figures/                       # PNG/SVG figures + manifest
```

### How to Run

```bash
pip install llvmlite matplotlib huggingface_hub
python -m src.experiment_runner
```

Set `HF_TOKEN` to enable live Hugging Face inference; otherwise the generator
falls back to mock mode. The experiment runner will also regenerate all paper
figures into `results/figures/` automatically.

### Generate Paper Figures (Manual)

```bash
python scripts/generate_paper_figures.py
```

Optional custom paths:

```bash
python scripts/generate_paper_figures.py --input results/experiment_results.json --output results/figures
```

Generated outputs:
- `results/figures/fig_validity_interest.(png|svg)`
- `results/figures/fig_error_distribution.(png|svg)`
- `results/figures/fig_error_distribution_donut.(png|svg)`
- `results/figures/fig_mutation_effectiveness.(png|svg)`
- `results/figures/fig_mutation_validity_ranking.(png|svg)`
- `results/figures/fig_semantic_interest_breakdown.(png|svg)`
- `results/figures/fig_source_outcome_stack.(png|svg)`
- `results/figures/fig_semantic_feature_heatmap.(png|svg)`
- `results/figures/figure_manifest.md`

### Key Results (Latest Run)

| Approach | Total | Valid | Valid% | Interesting | Int% |
|---|---|---|---|---|---|
| **LLM-based** | 45 | 41 | **91.1%** | 45 | **100.0%** |
| Grammar-based | 50 | 45 | **90.0%** | 27 | 54.0% |
| Random mutation | 50 | 8 | **16.0%** | 7 | 14.0% |

---

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
