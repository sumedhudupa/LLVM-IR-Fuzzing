# CLAUDE.md — Technical Implementation Guide

This file describes the remaining technical work to complete the LLVM IR Fuzzing Pipeline
prototype. The pipeline already has a working end-to-end flow (seed upload → LLM/grammar
mutation → validation → differential testing → comparison view). What follows are the
specific gaps that still need to be closed.

---

## Project Layout (Quick Reference)

```
llm-mutator/
  app/
    config.py                  # env vars: SEED_DIR, MUTANT_DIR, GRAMMAR_DIR, VALID_DIR, INVALID_DIR, LOGS_DIR
    generate_mutants.py        # LLMMutator + GrammarMutator classes
    filter_valid.py            # llvm-as + opt -passes=verify pipeline
    comparison.py              # compute_comparison_metrics()
    routes/
      seeds.py                 # GET /api/v1/seeds, POST /api/v1/seeds/upload
      mutants.py               # POST /api/v1/mutants/generate, POST /api/v1/mutants/validate
      differential.py          # POST /api/v1/differential/run, GET /api/v1/differential/results, GET /api/v1/differential/comparison
      analysis.py              # GET /api/v1/analysis/invalid-taxonomy, POST /api/v1/analysis/run-study
    services/
      mutant_service.py
      differential_service.py  # DifferentialService — core diff logic lives here
      analysis_service.py      # AnalysisService — taxonomy + controlled study
    models/
      mutants.py / differential.py / analysis.py / seeds.py
    utils/
      ir_helpers.py            # extract_ir, sanitize_ir, is_plausible_ir, strip_thinking_tags
      fs_helpers.py            # build_mutant_id, append_json_log
  logs/
    raw_mutants.json           # one entry per generated mutant (id, seed_name, mutator_type, strategy, status)
    validity_logs.json         # one entry per validated mutant (mutant_id, is_valid, error_type, verifier_output)
    results.csv                # one row per differential run (mutant_id, baseline_level, target_level, is_mismatch, ...)
    comparison_summary.csv     # aggregated LLM vs grammar metrics
    study_runs.jsonl           # one JSON object per controlled study run

frontend/src/
  api.js                       # all fetch calls — BASE_URL from VITE_API_BASE_URL
  pages/
    SeedList.jsx
    MutationJobForm.jsx
    ValidationStatus.jsx
    DifferentialDashboard.jsx
    ComparisonView.jsx         # controlled study runner + comparison table + taxonomy
```

---

## 1. Trivial / Semantically-Useless Mutation Detection

**Why it matters:** The problem statement explicitly asks for a study of "semantically
useless mutations." Right now `comparison.py` has a `trivial` counter that only catches
invalid mutants that don't fit other error categories. There is no detection of *valid*
mutants that are semantically equivalent to the seed.

### What to build

Add a post-validation semantic equivalence check in `filter_valid.py` (or a new
`app/utils/semantic_helpers.py`). The approach:

1. After a mutant passes `opt -passes=verify`, run both the seed and the mutant through
   `opt -S -passes=instcombine,simplifycfg` and compare the normalised output.
2. If the normalised IR is identical, mark the mutant as `trivial=True` in its validity
   log entry.
3. Add `trivial` as a first-class field in `MutantValidationResult` (models/mutants.py)
   and in the validity log schema.

### Backend changes

**`llm-mutator/app/utils/semantic_helpers.py`** — new file:
```python
# is_semantically_trivial(seed_path: Path, mutant_path: Path) -> bool
# Runs opt -S -passes=instcombine,simplifycfg on both files,
# strips comments and whitespace, returns True if outputs are identical.
```

**`llm-mutator/app/filter_valid.py`** — in `validate_mutant()`:
- After the `is_valid = True` branch, call `is_semantically_trivial(seed_path, target_dir/ll_path.name)`.
- Add `"trivial": bool` to `log_entry`.
- The seed path must be passed in or looked up from `SEED_DIR` using the mutant_id prefix.

**`llm-mutator/app/comparison.py`** — in `compute_comparison_metrics()`:
- Add a `trivial_valid` counter (valid but trivial) separate from the existing `trivial`
  counter (which currently counts invalid-other).
- Rename the existing `trivial` key to `other_invalid` to avoid confusion.

**`llm-mutator/app/models/mutants.py`** — `MutantValidationResult`:
```python
trivial: bool = False   # True if valid but semantically equivalent to seed
```

### Frontend changes

**`frontend/src/pages/ComparisonView.jsx`** — add `trivial_valid` to the `COLUMNS` array
and update the table header label to `"trivial (valid)"`.

---

## 2. Seed Diversity — Bundled Seed Set

**Why it matters:** The `seeds/` directory is empty in the repo. The controlled study
needs at least 4–5 structurally diverse seeds to produce meaningful LLM vs grammar
comparison numbers.

### What to build

Create `seeds/` files directly in the repo (they are small text files, safe to commit).
Each seed should exercise a different IR pattern:

| Filename | IR pattern to cover |
|---|---|
| `seed_arith.ll` | integer arithmetic, no branches |
| `seed_branch.ll` | conditional branch + icmp |
| `seed_loop.ll` | loop with PHI node |
| `seed_call.ll` | function call + return value |
| `seed_memory.ll` | alloca + store + load |

Each file must:
- Be valid LLVM IR (passes `llvm-as` + `opt -passes=verify`).
- Define `@main` returning `i32` so differential execution works without a harness.
- Be short (20–50 lines) so the LLM context window is not saturated.

The `seeds_test/` directory (used by `tests/verify_mutators.py`) should also get a
matching `seed_arith.ll` so the test suite has a real file to work with.

---

## 3. Study History Endpoint + UI Panel

**Why it matters:** `analysis_service.py` already appends each controlled study run to
`logs/study_runs.jsonl`, but there is no way to retrieve or display past runs. The final
report needs a table of run results.

### Backend changes

**`llm-mutator/app/routes/analysis.py`** — add:
```
GET /api/v1/analysis/study-history
```
Returns the last N study runs from `study_runs.jsonl` (default N=20), newest first.
Each entry includes `run_id`, `started_at`, `completed_at`, `settings`, and `aggregate`.

**`llm-mutator/app/services/analysis_service.py`** — add `get_study_history(limit: int)`:
```python
@staticmethod
def get_study_history(limit: int = 20) -> list[dict]:
    # Read STUDY_RUNS_LOG (newline-delimited JSON), return last `limit` entries reversed.
```

**`llm-mutator/app/models/analysis.py`** — add:
```python
class StudyHistoryResponse(BaseModel):
    runs: list[dict]
    total: int
```

### Frontend changes

**`frontend/src/api.js`** — add:
```js
export const getStudyHistory = () => request("GET", "/api/v1/analysis/study-history");
```

**`frontend/src/pages/ComparisonView.jsx`** — add a collapsible "Study Run History"
section below the controlled study runner. Show a table with columns:
`run_id | started_at | seeds | count/seed | validity% | mismatch%`.
Load history on mount alongside `loadMetrics()`.

---

## 4. Seed-Size / Context-Sensitivity Measurement

**Why it matters:** The status report lists this as a next measurement step. It answers
whether larger seeds cause more LLM truncation failures — a key finding for the report.

### What to build

Add a `seed_size_bytes` field to every entry in `raw_mutants.json` at generation time.

**`llm-mutator/app/generate_mutants.py`** — in `LLMMutator.run()`, inside the log entry:
```python
"seed_size_bytes": len(seed_ir.encode("utf-8")),
```
Do the same in `GrammarMutator.run()`.

Then add a new analysis endpoint:

**`GET /api/v1/analysis/seed-sensitivity`**

Returns a list of `{ seed_name, seed_size_bytes, validity_rate, trivial_rate }` grouped
by seed, for both mutator types. This lets you plot validity rate vs seed size.

**`llm-mutator/app/services/analysis_service.py`** — add `get_seed_sensitivity()`:
```python
@staticmethod
async def get_seed_sensitivity() -> list[dict]:
    # Join raw_mutants.json (for seed_size_bytes) with validity_logs.json (for is_valid).
    # Group by (seed_name, mutator_type), compute validity_rate per group.
    # Return sorted by seed_size_bytes ascending.
```

**`llm-mutator/app/routes/analysis.py`** — register the new route.

**`frontend/src/api.js`** — add `getSeedSensitivity`.

**`frontend/src/pages/ComparisonView.jsx`** — add a "Seed Sensitivity" table showing
seed name, size (bytes), LLM validity rate, grammar validity rate side by side.

---

## 5. Per-Strategy Breakdown in Comparison Metrics

**Why it matters:** The LLM uses 5 named strategies (arithmetic_substitution,
constant_mutation, icmp_predicate_change, nop_insertion, branch_condition_flip). The
grammar mutator uses 3 (arithmetic_substitution, icmp_predicate_flip,
constant_perturbation). Right now all strategies are aggregated together. Breaking them
out shows which strategies produce the most valid / most interesting mutants.

### Backend changes

**`llm-mutator/app/comparison.py`** — in `compute_comparison_metrics()`, add a
`per_strategy` dict alongside the top-level `llm`/`grammar` dicts:
```python
# per_strategy[mutator_type][strategy_name] = { generated, valid, validity_rate }
```
Join `raw_mutants.json` (has `strategy` field) with `validity_logs.json` (has `is_valid`).

**`GET /api/v1/differential/comparison`** — the existing endpoint already calls
`compute_comparison_metrics()`, so the new `per_strategy` key will appear automatically
once the function is updated.

### Frontend changes

**`frontend/src/pages/ComparisonView.jsx`** — add a "Per-Strategy Breakdown" table
below the main comparison table. Columns: `strategy | LLM valid% | Grammar valid%`.
Only render if `metrics.per_strategy` is present (backward-compatible).

---

## 6. Differential Results Deduplication

**Why it matters:** Every call to `POST /api/v1/differential/run` appends new rows to
`results.csv` without checking for duplicates. Running the study multiple times inflates
all metrics.

### Backend changes

**`llm-mutator/app/services/differential_service.py`** — in `write_results_row()`:
- Before appending, check if a row with the same `mutant_id + baseline_level + target_level`
  already exists in `results.csv`.
- If it exists, overwrite that row (rewrite the file) rather than appending.

Alternatively, add a `run_id` column to `results.csv` and filter by the latest run_id
when computing comparison metrics. This is simpler and preserves history.

The simpler approach: add `run_id` to `CSV_FIELDNAMES` in `differential_service.py` and
pass it through from `DifferentialRunRequest`. Update `compute_comparison_metrics()` in
`comparison.py` to only use rows from the most recent run_id per mutant when computing
rates (or expose a `run_id` filter parameter).

---

## 7. Validation Status Page — Auto-Load on Navigate

**Why it matters:** `ValidationStatus.jsx` only shows results after the user clicks
"Revalidate." If the user navigates directly to the Validate tab (not via the mutation
flow), `mutantIds` is empty and the page is blank with no guidance.

### Frontend changes

**`frontend/src/pages/ValidationStatus.jsx`**:
- On mount, if `mutantIds` is empty, call `GET /api/v1/differential/results` to check
  whether any validated mutants already exist and show a summary count.
- Add a "Load All Validated Mutants" button that calls a new endpoint (see below) to
  list all mutants currently in `valid_mutants/` and `invalid_mutants/`.

**`GET /api/v1/mutants/list`** — new endpoint:
```
Returns { valid: [mutant_id, ...], invalid: [mutant_id, ...] }
by scanning VALID_DIR and INVALID_DIR.
```

**`llm-mutator/app/routes/mutants.py`** — add the route.
**`llm-mutator/app/services/mutant_service.py`** — add `list_mutants()`.

---

## 8. Test Coverage for New Code

The existing test file is `llm-mutator/tests/verify_mutators.py`. It tests
`ir_helpers` and `GrammarMutator._mutate_one()` only.

Add test cases for:

- `semantic_helpers.is_semantically_trivial()` — test with identical IR (should return
  True) and with a mutated constant (should return False).
- `AnalysisService.get_seed_sensitivity()` — mock `raw_mutants.json` and
  `validity_logs.json` with known data, assert correct grouping and rates.
- `AnalysisService.get_study_history()` — write a temp `study_runs.jsonl`, assert
  correct ordering and limit behaviour.
- `DifferentialService._infer_mutator_type()` — already deterministic, easy to unit test.

Run tests from inside the `llm-mutator/` directory:
```bash
python tests/verify_mutators.py
```

---

## Environment Variables (for reference)

All set in `.env` at the repo root and passed through `docker-compose.yml`:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API base URL |
| `LLM_MODEL` | `qwen3:1.5b` | Model name for mutation |
| `SEED_DIR` | `./seeds` | Input seed `.ll` files |
| `MUTANT_DIR` | `./mutants_llm` | LLM-generated mutants |
| `GRAMMAR_DIR` | `./mutants_grammar` | Grammar-generated mutants |
| `VALID_DIR` | `./valid_mutants` | Mutants that passed verification |
| `INVALID_DIR` | `./invalid_mutants` | Mutants that failed verification |
| `LOGS_DIR` | `./logs` | All JSON/CSV logs |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend → backend base URL |

---

## Implementation Order

Work through these in order — each builds on the previous:

1. **Seed files** (Section 2) — needed before any study can produce real data.
2. **Trivial detection** (Section 1) — adds the missing "semantically useless" metric.
3. **seed_size_bytes logging + seed sensitivity endpoint** (Section 4) — small change to
   generation, big payoff for the report.
4. **Per-strategy breakdown** (Section 5) — pure data aggregation, no new I/O.
5. **Study history endpoint + UI** (Section 3) — needed to export results for the report.
6. **Deduplication** (Section 6) — clean up before running the final study.
7. **Validation page auto-load** (Section 7) — UX polish, low priority.
8. **Tests** (Section 8) — add alongside each section above, not at the end.
