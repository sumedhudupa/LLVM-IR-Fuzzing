# EVALUATION: Metrics, Comparisons & Test Cases

## 1. Evaluation Framework

### 1.1 Objectives
1. **Validity Rate** — What fraction of generated mutants pass LLVM verification?
2. **Bug Detection Rate** — How many valid mutants trigger differential testing mismatches?
3. **Semantic Diversity** — Are LLM-generated mutations more varied than grammar/random baselines?
4. **Triviality Rate** — What fraction of valid mutants are semantically identical to the seed?
5. **Error Distribution** — What types of invalid IR does each mutator produce?

### 1.2 Metrics Definitions

| Metric | Formula | Target |
|---|---|---|
| **Validity Rate** | `valid_count / total_generated` | LLM > 60%, Grammar > 90%, Random < 40% |
| **Bug Rate** | `mismatches / valid_count` | Any mismatch is interesting |
| **Triviality Rate** | `trivial_valid / valid_count` | Lower is better (< 10%) |
| **Duplicate Rate** | `duplicate_count / total_generated` | Lower is better |
| **Error Distribution** | `count_by_error_type / invalid_count` | Informational |
| **Generation Time** | `avg_ms_per_mutant` | LLM ~1500ms, Grammar ~50ms, Random ~10ms |

## 2. Baseline Comparison: LLM vs. Grammar vs. Random

### 2.1 Expected Performance Profile

| Metric | LLM Mutator | Grammar Mutator | Random Mutator |
|---|---|---|---|
| **Validity Rate** | 65–80% | 90–95% | 25–40% |
| **Semantic Diversity** | High | Medium | Low |
| **Bug Detection** | Highest potential | Moderate | Low |
| **Generation Speed** | ~1–3s/mutant | ~10–50ms/mutant | ~5–10ms/mutant |
| **Triviality Rate** | Low (~5%) | Moderate (~15%) | N/A (mostly invalid) |
| **Error Types** | Diverse (SSA, type, syntax) | Rare (mostly valid) | Mostly syntax |

### 2.2 Comparison Methodology

The comparison engine (`comparison.py`) computes:
1. Per-mutator validity rates from `validity_logs.json`
2. Per-strategy breakdown (e.g., `arithmetic_substitution` validity for LLM vs. Grammar)
3. Bug rates from `results.csv` differential testing results
4. Error type distribution for invalid mutants
5. Seed sensitivity analysis (validity vs. seed size/complexity)

### 2.3 Statistical Significance

To ensure meaningful comparison:
- **Minimum sample size**: ≥10 mutants per mutator per seed
- **Multiple seeds**: Test across seeds of varying complexity
- **Controlled variables**: Same seed files, same LLVM version, same machine

## 3. Test Cases (≥ 5 Seed Files)

### Test Case 1: `seed_arith.ll` — Basic Arithmetic

```llvm
; ModuleID = 'seed_arith.ll'
define i32 @main() {
entry:
  %a = add i32 10, 20
  %b = sub i32 %a, 5
  %c = mul i32 %b, 2
  ret i32 %c
}
```

**Purpose**: Tests arithmetic substitution mutations. Expected exit code: 50.  
**Expected LLM mutations**: `add→sub`, `sub→add`, `mul→sdiv`, constant changes.  
**Expected Grammar mutations**: Systematic opcode swaps.  
**Expected Random mutations**: Character flips breaking syntax.

---

### Test Case 2: `seed_branch.ll` — Conditional Branching

```llvm
; ModuleID = 'seed_branch.ll'
define i32 @main() {
entry:
  %x = add i32 5, 10
  %cmp = icmp sgt i32 %x, 12
  br i1 %cmp, label %then, label %else

then:
  ret i32 1

else:
  ret i32 0
}
```

**Purpose**: Tests branch condition flipping and icmp predicate changes.  
**Expected behavior**: -O0 returns 1 (15 > 12 is true). Predicate flip (sgt→slt) would change result.

---

### Test Case 3: `seed_loop.ll` — Loop with PHI Node

```llvm
; ModuleID = 'seed_loop.ll'
define i32 @main() {
entry:
  br label %loop

loop:
  %i = phi i32 [ 0, %entry ], [ %next, %loop ]
  %sum = phi i32 [ 0, %entry ], [ %newsum, %loop ]
  %newsum = add i32 %sum, %i
  %next = add i32 %i, 1
  %cond = icmp slt i32 %next, 5
  br i1 %cond, label %loop, label %exit

exit:
  ret i32 %newsum
}
```

**Purpose**: Tests PHI node handling, loop structure preservation, and SSA compliance.  
**Expected behavior**: Computes sum 0+1+2+3+4 = 10.  
**Stress test for**: PHI placement rules, SSA violations, branch target validity.

---

### Test Case 4: `seed_multifunction.ll` — Multiple Functions

```llvm
; ModuleID = 'seed_multifunction.ll'
define i32 @add_numbers(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}

define i32 @main() {
entry:
  %r = call i32 @add_numbers(i32 10, i32 32)
  ret i32 %r
}
```

**Purpose**: Tests mutation across function boundaries and call preservation.  
**Expected behavior**: Returns 42.  
**Stress test for**: Function signature preservation, cross-function SSA.

---

### Test Case 5: `seed_bitwise.ll` — Bitwise Operations

```llvm
; ModuleID = 'seed_bitwise.ll'
define i32 @main() {
entry:
  %a = and i32 255, 15
  %b = or i32 %a, 240
  %c = xor i32 %b, 128
  %d = shl i32 %c, 1
  %e = lshr i32 %d, 2
  ret i32 %e
}
```

**Purpose**: Tests bitwise operation mutations and type consistency.  
**Expected behavior**: `255 & 15 = 15`, `15 | 240 = 255`, `255 ^ 128 = 127`, `127 << 1 = 254`, `254 >> 2 = 63`.  
**Stress test for**: Grammar mutator opcode swaps (and↔or, xor→or).

---

### Test Case 6: `seed_memory.ll` — Memory Operations (Alloca + Load/Store)

```llvm
; ModuleID = 'seed_memory.ll'
define i32 @main() {
entry:
  %ptr = alloca i32
  store i32 42, i32* %ptr
  %val = load i32, i32* %ptr
  %result = add i32 %val, 8
  ret i32 %result
}
```

**Purpose**: Tests that mutations preserve memory operation types and pointer semantics.  
**Expected behavior**: Returns 50.  
**Stress test for**: Type errors (integer ops on pointer types), load/store consistency.

---

### Test Case 7: `seed_nested_branch.ll` — Nested Conditionals

```llvm
; ModuleID = 'seed_nested_branch.ll'
define i32 @main() {
entry:
  %x = add i32 10, 5
  %cmp1 = icmp sgt i32 %x, 12
  br i1 %cmp1, label %outer_then, label %outer_else

outer_then:
  %y = sub i32 %x, 3
  %cmp2 = icmp eq i32 %y, 12
  br i1 %cmp2, label %inner_then, label %inner_else

inner_then:
  ret i32 100

inner_else:
  ret i32 50

outer_else:
  ret i32 0
}
```

**Purpose**: Tests nested branch handling, multiple labels, and complex CFG.  
**Expected behavior**: 15 > 12 → outer_then; 15-3=12, 12==12 → inner_then, returns 100.  
**Stress test for**: Branch target validation, predicate flipping cascades.

## 4. Evaluation Procedure

### 4.1 Running the Evaluation

```bash
# 1. Build all containers
./build.sh

# 2. Start the pipeline
./run.sh

# 3. Wait for services to be ready
curl http://localhost:8000/health

# 4. Generate mutants (via API)
curl -X POST http://localhost:8000/api/v1/mutants/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_names": ["seed_arith.ll"], "mutator_type": "llm", "count": 10}'

curl -X POST http://localhost:8000/api/v1/mutants/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_names": ["seed_arith.ll"], "mutator_type": "grammar", "count": 10}'

curl -X POST http://localhost:8000/api/v1/mutants/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_names": ["seed_arith.ll"], "mutator_type": "random", "count": 10}'

# 5. Validate mutants
curl -X POST http://localhost:8000/api/v1/mutants/validate \
  -H "Content-Type: application/json" \
  -d '{"mutant_ids": ["seed_arith_llm_mut_0", "seed_arith_grammar_mut_0", "seed_arith_random_mut_0"]}'

# 6. Run differential testing
curl -X POST http://localhost:8000/api/v1/differential/run \
  -H "Content-Type: application/json" \
  -d '{}'

# 7. Get comparison metrics
curl http://localhost:8000/api/v1/analysis/comparison
```

### 4.2 Success Criteria

| Criterion | Threshold | Measured By |
|---|---|---|
| LLM validity rate | ≥ 60% | `validity_logs.json` analysis |
| Grammar validity rate | ≥ 90% | `validity_logs.json` analysis |
| Random validity rate | ≤ 40% | `validity_logs.json` analysis |
| LLM > Random validity | Statistically significant | Comparison metrics |
| ≥ 5 test cases | All 7 seeds tested | Test case coverage |
| Differential testing runs | Complete without crash | `results.csv` populated |
| Error classification | ≥ 3 distinct types | Error distribution data |

## 5. Evaluation Results Format

### 5.1 Per-Mutator Summary

Results are exported to `logs/comparison_summary.csv`:

```csv
mutator_type,validity_rate,bug_rate,broken_ssa,type_errors,invalid_phi,other_invalid,trivial_valid
llm,0.72,0.05,3,1,0,2,1
grammar,0.93,0.02,0,0,0,1,3
random,0.31,0.00,5,8,2,12,0
```

### 5.2 Per-Strategy Breakdown

```json
{
  "per_strategy": {
    "llm": {
      "arithmetic_substitution": {"generated": 10, "valid": 8, "validity_rate": 0.8},
      "constant_mutation": {"generated": 10, "valid": 7, "validity_rate": 0.7},
      "icmp_predicate_change": {"generated": 10, "valid": 9, "validity_rate": 0.9},
      "nop_insertion": {"generated": 10, "valid": 6, "validity_rate": 0.6},
      "branch_condition_flip": {"generated": 10, "valid": 7, "validity_rate": 0.7}
    }
  }
}
```

### 5.3 Seed Sensitivity Analysis

```json
{
  "sensitivity_data": [
    {"seed_name": "seed_arith.ll", "seed_size_bytes": 180, "llm": {"validity_rate": 0.8}},
    {"seed_name": "seed_loop.ll", "seed_size_bytes": 350, "llm": {"validity_rate": 0.65}},
    {"seed_name": "seed_nested_branch.ll", "seed_size_bytes": 520, "llm": {"validity_rate": 0.55}}
  ]
}
```

**Observation**: Validity rate tends to decrease with seed complexity, as larger IR modules have more opportunities for SSA violations and structural errors.

## 6. Known Limitations

1. **LLM model size** — 1.5B parameter model has limited understanding of complex LLVM IR constructs
2. **Deterministic grammar mutations** — Cannot discover novel mutation patterns
3. **No LLVM C++ API bindings** — Deduplication relies on text hashing, not AST comparison
4. **Single-threaded LLM calls** — Ollama processes requests sequentially
5. **File-based logging** — JSON append is not atomic under concurrent writes

## 7. Failure Cases

### 7.1 Common LLM Failure Modes

| Failure | Frequency | Example |
|---|---|---|
| C-style comments (`//`) | ~15% of raw outputs | `// This is a mutation` |
| x86 assembly suffixes | ~5% | `addq i32 %a, 1` |
| Truncated output | ~8% | Function body cut mid-instruction |
| Prose mixed with IR | ~10% | `Here is the mutated IR:` before code |
| SSA violations | ~12% of post-extraction | `%x = add ...; %x = sub ...` |
| Inline arithmetic | ~3% | `add i32 %a, %b+1` |

### 7.2 Mitigation Strategies

- **Sanitization** (`sanitize_ir()`) catches comments and assembly suffixes
- **Extraction** (`extract_ir()`) strips prose and thinking blocks
- **Refinement loop** feeds back error messages to the LLM for correction
- **Rule pre-validation** catches SSA/CFG errors before expensive LLVM calls

## 8. Demo Instructions

### Working Case (Seed with successful mutation)

1. Start the pipeline: `./run.sh`
2. Open browser: `http://localhost:4000`
3. Navigate to **Seed List** → verify seeds are loaded
4. Navigate to **Mutation Job Form** → select `seed_arith.ll`, mutator `llm`, count `5`
5. Click **Generate** → observe job completion
6. Navigate to **Validation Status** → see valid/invalid counts
7. Navigate to **Comparison View** → see LLM vs Grammar vs Random metrics

### Failure Case (Invalid mutation detection)

1. Navigate to **Mutation Job Form** → select `seed_loop.ll`, mutator `random`, count `10`
2. Click **Generate** → observe high failure rate
3. Navigate to **Validation Status** → filter by "Invalid"
4. Inspect error messages showing SSA violations, syntax errors
5. Navigate to **Comparison View** → observe Random's low validity rate vs LLM/Grammar
