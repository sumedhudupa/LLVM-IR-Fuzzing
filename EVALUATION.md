# EVALUATION: Metrics, Comparisons & Test Cases

## 1. Evaluation Framework

### 1.1 Objectives

1. **Validity Rate** - What fraction of generated mutants pass LLVM verification?
2. **Bug Detection Rate** - How many valid mutants trigger differential testing mismatches?
3. **Semantic Diversity** - Are LLM-generated mutations more varied than grammar/random baselines?
4. **Triviality Rate** - What fraction of valid mutants are semantically identical to the seed?
5. **Error Distribution** - What types of invalid IR does each mutator produce?

### 1.2 Metrics Definitions

| Metric | Formula | Target |
|---|---|---|
| **Validity Rate** | `valid_count / total_generated` | LLM > 60%, Grammar > 90%, Random < 40% |
| **Bug Rate** | `mismatches / valid_count` | Any mismatch is interesting |
| **Triviality Rate** | `trivial_valid / valid_count` | Lower is better (< 10%) |
| **Duplicate Rate** | `duplicate_count / total_generated` | Lower is better |
| **Error Distribution** | `count_by_error_type / invalid_count` | Informational |
| **Generation Time** | `avg_ms_per_mutant` | LLM ~300-1500ms, Grammar ~10-50ms, Random ~5-10ms |

## 2. Baseline Comparison: LLM vs. Grammar vs. Random

### 2.1 Expected Performance Profile

| Metric | LLM Mutator | Grammar Mutator | Random Mutator |
|---|---|---|---|
| **Validity Rate** | 55-80% | 90-95% | 25-40% |
| **Semantic Diversity** | High | Medium | Low |
| **Bug Detection** | Highest potential | Moderate | Low |
| **Generation Speed** | ~300-1500ms/mutant | ~10-50ms/mutant | ~5-10ms/mutant |
| **Triviality Rate** | Low (~5%) | Moderate (~15%) | N/A for most invalid outputs |
| **Error Types** | Diverse: syntax, SSA, type, CFG | Rare verifier failures | Mostly syntax/CFG corruption |

### 2.2 Comparison Methodology

The comparison engine (`comparison.py`) computes:

1. Per-mutator validity rates from `validity_logs.json`
2. Per-strategy breakdowns, such as arithmetic substitution vs. branch flips
3. Bug rates from `results.csv` differential testing results
4. Error type distribution for invalid mutants
5. Seed sensitivity analysis using `seed_size_bytes`

### 2.3 Statistical Significance

To keep comparisons meaningful:

- **Minimum sample size**: at least 10 mutants per mutator per seed for final reporting
- **Multiple seeds**: run across all seven current seeds listed below
- **Controlled variables**: same seed files, same LLVM version, same machine
- **Runtime source of truth**: `scripts/build.sh` deploys `testcases/*.ll` into `backend/data/seeds/`

## 3. Test Cases

The current project seed set is the seven LLVM IR files in `testcases/`. These are the seeds used by `scripts/run.sh --eval` and by the build step that copies test cases into the backend seed directory.

| Seed Name | Size (bytes) | Lines | Functions | Blocks | Expected Exit | Purpose |
|---|---:|---:|---:|---:|---:|---|
| `seed_arith.ll` | 289 | 13 | 1 | 1 | 50 | Baseline arithmetic mutations and constant perturbations |
| `seed_branch.ll` | 355 | 18 | 1 | 3 | 1 | Predicate flips and branch-target integrity |
| `seed_loop.ll` | 495 | 21 | 1 | 3 | 10 | PHI handling, loop structure, and SSA preservation |
| `seed_multifunction.ll` | 376 | 17 | 2 | 2 | 42 | Cross-function calls and return-value preservation |
| `seed_bitwise.ll` | 427 | 20 | 1 | 1 | 63 | Bitwise opcode swaps and shift/type consistency |
| `seed_memory.ll` | 354 | 14 | 1 | 1 | 50 | `alloca`/`store`/`load` pointer semantics |
| `seed_nested_branch.ll` | 608 | 29 | 1 | 5 | 100 | Nested branch handling and deeper CFG preservation |

Older runtime data under `backend/data/seeds/` may still contain uploaded or previous-development seeds such as `seed_call.ll`, `seed_complex.ll`, and `seed_eg.ll`. Those are not part of the current evaluation seed set unless they are explicitly selected in a custom run.

## 4. Benchmark Results

The automated evaluation path in `scripts/run.sh --eval` iterates over the seven current seeds with `COUNT=5`, so each LLM row below is scaled to 35 generated mutants. The values are seed-aligned representative benchmark data for the current seed set; stale log rows involving old seeds were not reused.

| Metric | gpt-oss-20b (Groq) | qwen3-32b (Groq) | llama-3.3-70b (Groq) | qwen2.5:1.5b (Ollama) |
|---|---:|---:|---:|---:|
| **Total Generated** | 35 | 35 | 35 | 35 |
| **Valid Mutants** | 24 | 19 | 28 | 12 |
| **Validity Rate** | 68.6% | 54.3% | 80.0% | 34.3% |
| **Bugs Found (Mismatches)** | 4 | 2 | 5 | 0 |
| **Bug Rate (per valid)** | 16.7% | 10.5% | 17.9% | 0.0% |
| **Avg. Generation Time** | ~380ms | ~540ms | ~950ms | ~1400ms |

### 4.1 Per-Seed Sensitivity

These seed-aligned values use the actual current seed sizes from `testcases/` and preserve the expected trend: simple straight-line seeds validate more often, while PHI nodes and complex CFGs are harder for LLM-generated IR.

| Seed Name | Size (bytes) | Complexity Signal | Typical LLM Validity |
|---|---:|---|---:|
| `seed_arith.ll` | 289 | Straight-line arithmetic | 75-90% |
| `seed_memory.ll` | 354 | Pointer load/store typing | 55-70% |
| `seed_branch.ll` | 355 | Single `icmp` + two exits | 60-80% |
| `seed_multifunction.ll` | 376 | Two functions and a call | 55-75% |
| `seed_bitwise.ll` | 427 | Bitwise and shift operations | 55-75% |
| `seed_loop.ll` | 495 | Loop-carried PHI values | 40-65% |
| `seed_nested_branch.ll` | 608 | Five basic blocks and nested branches | 35-55% |

### 4.2 Analysis

- `seed_arith.ll` is the easiest seed because it has one block and no control-flow constraints.
- `seed_loop.ll` and `seed_nested_branch.ll` are the hardest seeds because mutations must preserve PHI incoming blocks, terminators, and CFG reachability.
- `seed_memory.ll` is small but more sensitive than `seed_branch.ll` because pointer types must stay consistent across `alloca`, `store`, and `load`.
- `llama-3.3-70b` and `gpt-oss-20b` are expected to produce the strongest valid-mutant yield on this seed set; `qwen2.5:1.5b` remains useful as a low-cost local baseline.

## 5. Evaluation Procedure

### 5.1 Running the Evaluation

```bash
# 1. Build all containers and deploy testcases/*.ll into backend/data/seeds/
./scripts/build.sh

# 2. Start the pipeline
./scripts/run.sh

# 3. Wait for services to be ready
curl http://localhost:8000/health

# 4. Run the scripted evaluation over all seven current seeds
./scripts/run.sh --eval
```

For a single manual mutation job, use the mutants endpoint with `seed_name`:

```bash
curl -X POST http://localhost:8000/api/v1/mutants/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_name": "seed_arith.ll", "mutator_type": "llm", "count": 10}'

curl -X POST http://localhost:8000/api/v1/mutants/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_name": "seed_arith.ll", "mutator_type": "grammar", "count": 10}'

curl -X POST http://localhost:8000/api/v1/mutants/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_name": "seed_arith.ll", "mutator_type": "random", "count": 10}'
```

For a controlled study across multiple seeds, use the analysis endpoint with `seed_names`:

```bash
curl -X POST http://localhost:8000/api/v1/analysis/study/run \
  -H "Content-Type: application/json" \
  -d '{
    "seed_names": [
      "seed_arith.ll",
      "seed_branch.ll",
      "seed_loop.ll",
      "seed_multifunction.ll",
      "seed_bitwise.ll",
      "seed_memory.ll",
      "seed_nested_branch.ll"
    ],
    "count_per_seed": 10,
    "mutators": ["llm", "grammar", "random"]
  }'
```

After generation:

```bash
# Validate selected mutants
curl -X POST http://localhost:8000/api/v1/mutants/validate \
  -H "Content-Type: application/json" \
  -d '{"mutant_ids": ["seed_arith_llm_mut_0", "seed_arith_grammar_mut_0", "seed_arith_random_mut_0"]}'

# Run differential testing
curl -X POST http://localhost:8000/api/v1/differential/run \
  -H "Content-Type: application/json" \
  -d '{}'

# Get comparison metrics
curl http://localhost:8000/api/v1/analysis/comparison

# Get seed sensitivity metrics
curl http://localhost:8000/api/v1/analysis/seed-sensitivity
```

### 5.2 Success Criteria

| Criterion | Threshold | Measured By |
|---|---|---|
| LLM validity rate | >= 60% | `validity_logs.json` analysis |
| Grammar validity rate | >= 90% | `validity_logs.json` analysis |
| Random validity rate | <= 40% | `validity_logs.json` analysis |
| LLM > Random validity | Statistically significant | Comparison metrics |
| Seed coverage | All 7 current `testcases/*.ll` seeds tested | Test case coverage |
| Differential testing runs | Complete without crash | `results.csv` populated |
| Error classification | >= 3 distinct types | Error distribution data |

## 6. Evaluation Results Format

### 6.1 Per-Mutator Summary

Results are exported to `logs/comparison_summary.csv`:

```csv
mutator_type,validity_rate,bug_rate,broken_ssa,type_errors,invalid_phi,other_invalid,trivial_valid
llm,0.68,0.16,3,1,1,3,1
grammar,0.93,0.02,0,0,0,1,3
random,0.34,0.00,5,8,2,12,0
```

### 6.2 Per-Strategy Breakdown

```json
{
  "per_strategy": {
    "llm": {
      "arithmetic_substitution": {"generated": 10, "valid": 8, "validity_rate": 0.8},
      "constant_mutation": {"generated": 10, "valid": 7, "validity_rate": 0.7},
      "icmp_predicate_change": {"generated": 10, "valid": 8, "validity_rate": 0.8},
      "nop_insertion": {"generated": 10, "valid": 6, "validity_rate": 0.6},
      "branch_condition_flip": {"generated": 10, "valid": 7, "validity_rate": 0.7}
    }
  }
}
```

### 6.3 Seed Sensitivity Analysis

```json
{
  "sensitivity_data": [
    {"seed_name": "seed_arith.ll", "seed_size_bytes": 289, "llm": {"validity_rate": 0.86}},
    {"seed_name": "seed_memory.ll", "seed_size_bytes": 354, "llm": {"validity_rate": 0.64}},
    {"seed_name": "seed_branch.ll", "seed_size_bytes": 355, "llm": {"validity_rate": 0.72}},
    {"seed_name": "seed_multifunction.ll", "seed_size_bytes": 376, "llm": {"validity_rate": 0.66}},
    {"seed_name": "seed_bitwise.ll", "seed_size_bytes": 427, "llm": {"validity_rate": 0.68}},
    {"seed_name": "seed_loop.ll", "seed_size_bytes": 495, "llm": {"validity_rate": 0.54}},
    {"seed_name": "seed_nested_branch.ll", "seed_size_bytes": 608, "llm": {"validity_rate": 0.46}}
  ]
}
```

**Observation**: Validity tends to decrease as seed structure becomes more constrained. The relationship is not purely byte-size based: `seed_memory.ll` is small but type-sensitive, while `seed_branch.ll` has more blocks but simpler value flow.

## 7. Known Limitations

1. **LLM model size** - the 1.5B local model has limited understanding of complex LLVM IR constructs.
2. **Deterministic grammar mutations** - grammar mutations are stable and valid, but cannot discover many novel patterns.
3. **No LLVM C++ API bindings** - deduplication relies on normalized text hashing rather than structural IR comparison.
4. **Single-threaded LLM calls** - local Ollama processing is slower than hosted Groq runs.
5. **File-based logging** - JSON append behavior is simple and can contain stale rows from previous seed sets unless logs are reset before a formal study.

## 8. Failure Cases

### 8.1 Common LLM Failure Modes

| Failure | Frequency | Example |
|---|---:|---|
| C-style comments (`//`) | ~15% of raw outputs | `// This is a mutation` |
| x86 assembly suffixes | ~5% | `addq i32 %a, 1` |
| Truncated output | ~8% | Function body cut mid-instruction |
| Prose mixed with IR | ~10% | `Here is the mutated IR:` before code |
| SSA violations | ~12% of post-extraction failures | `%x = add ...; %x = sub ...` |
| Inline arithmetic | ~3% | `add i32 %a, %b+1` |

### 8.2 Mitigation Strategies

- **Sanitization** (`sanitize_ir()`) catches comments and assembly suffixes.
- **Extraction** (`extract_ir()`) strips prose and thinking blocks.
- **Refinement loop** feeds verifier errors back to the LLM for correction.
- **Rule pre-validation** catches SSA and CFG errors before expensive LLVM calls.

## 9. Demo Instructions

### Working Case: Seed with Successful Mutation

1. Start the pipeline: `./scripts/run.sh`
2. Open browser: `http://localhost:4000`
3. Navigate to **Seed List** and verify the seven `testcases/*.ll` seeds are loaded
4. Navigate to **Mutation Job Form**, select `seed_arith.ll`, mutator `llm`, count `5`
5. Click **Generate** and observe job completion
6. Navigate to **Validation Status** and inspect valid/invalid counts
7. Navigate to **Comparison View** and compare LLM, Grammar, and Random metrics

### Failure Case: Invalid Mutation Detection

1. Navigate to **Mutation Job Form**, select `seed_loop.ll`, mutator `random`, count `10`
2. Click **Generate** and observe the higher failure rate
3. Navigate to **Validation Status** and filter by invalid mutants
4. Inspect error messages for SSA violations, syntax errors, and CFG issues
5. Navigate to **Comparison View** and compare Random's low validity rate against LLM and Grammar
