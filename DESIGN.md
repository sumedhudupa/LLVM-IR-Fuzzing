# DESIGN: LLVM IR Fuzzing Pipeline

## 1. Problem Statement

Compiler optimizations are critical for software performance but can silently introduce correctness bugs. Traditional compiler testing approaches — manual test suites and grammar-based fuzzers — suffer from limited semantic diversity and high false-positive rates. This project investigates whether **Large Language Models (LLMs)** can generate semantically richer, structurally valid LLVM IR mutations that improve differential testing coverage beyond traditional methods.

## 2. Design Approach

### 2.1 Core Architecture: Multi-Strategy Mutation + Differential Testing

The system uses a **three-pronged mutation strategy** to maximize bug-finding potential while providing rigorous baseline comparisons:

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLVM IR Fuzzing Pipeline                      │
│                                                                 │
│  ┌──────────┐    ┌───────────┐    ┌───────────┐                │
│  │   Seed   │───▶│  Mutation  │───▶│ Validation│                │
│  │   Pool   │    │  Engine    │    │  Pipeline │                │
│  └──────────┘    └───────────┘    └───────────┘                │
│                   │   │   │              │                       │
│           ┌───────┘   │   └───────┐     │                       │
│           ▼           ▼           ▼     ▼                       │
│      ┌────────┐ ┌─────────┐ ┌────────┐ ┌─────────────┐        │
│      │  LLM   │ │ Grammar │ │ Random │ │ Differential│        │
│      │Mutator │ │ Mutator │ │Mutator │ │   Tester    │        │
│      └────────┘ └─────────┘ └────────┘ └─────────────┘        │
│                                                │                │
│                                         ┌──────┴──────┐        │
│                                         │  Comparison │        │
│                                         │   Engine    │        │
│                                         └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

1. **Seed Ingestion** → LLVM IR seed files are loaded from disk  
2. **Mutation** → Three mutators generate candidate IR files in parallel  
3. **Pre-Validation** → Rule-based structural checks (7 rules) reject obvious invalids cheaply  
4. **LLVM Validation** → `llvm-as` + `opt -passes=verify` confirm semantic validity  
5. **Deduplication** → Normalized MD5 hashing detects duplicate mutations  
6. **Differential Testing** → Valid mutants compiled at `-O0` vs `-O2`, outputs compared  
7. **Analysis** → Aggregated metrics, per-strategy breakdowns, seed sensitivity

### 2.3 Mutation Strategies

#### LLM Mutator (Primary — 5 strategies)
Uses Ollama-hosted LLMs (qwen2.5:1.5b / qwen3:1.5b) with tightly-scoped prompts:

| Strategy | Description |
|---|---|
| `arithmetic_substitution` | Replace one arithmetic opcode (add→sub, mul→sdiv) |
| `constant_mutation` | Modify one integer constant value |
| `icmp_predicate_change` | Flip comparison predicates (eq→ne, slt→sgt) |
| `nop_insertion` | Insert a semantically neutral instruction |
| `branch_condition_flip` | Negate conditional branch predicates |

**Key design choices:**
- **Tightly-scoped prompts** — Each prompt constrains the LLM to exactly one mutation type, preventing hallucination of multiple changes
- **Optional refinement loop** — Failed generations can be retried with error context fed back to the LLM (up to 3 attempts)
- **Temperature ramping** — Progressive temperature increase (0.60 → 0.90) across batch for diversity

#### Grammar Mutator (Baseline — 3 strategies)
Deterministic, rule-based transforms following LLVM IR grammar:

| Strategy | Description |
|---|---|
| `arithmetic_substitution` | Systematic opcode swap via regex tables |
| `icmp_predicate_flip` | Predicate inversion from swap tables |
| `constant_perturbation` | Controlled ±1 to ±3 perturbation |

#### Random Mutator (Negative Baseline — 5 strategies)
Non-grammar-aware mutations for lower-bound comparison:

| Strategy | Description |
|---|---|
| `random_char_flip` | Single character flip |
| `random_line_delete` | Delete one line |
| `random_line_duplicate` | Duplicate one line |
| `random_line_swap` | Swap adjacent lines |
| `random_word_replace` | Replace LLVM keywords |

### 2.4 Validation Pipeline (Multi-Stage)

```
Candidate IR
     │
     ▼
┌─────────────────────┐
│ Rule-Based Pre-Check │  ← 7 structural checks (fast, no subprocess)
│  1. Function exists  │
│  2. Balanced braces  │
│  3. Block terminators│
│  4. SSA property     │
│  5. PHI placement    │
│  6. Branch targets   │
│  7. Type consistency │
└──────────┬──────────┘
           │ pass
           ▼
┌──────────────────────┐
│   llvm-as (assembly) │  ← Catches syntax errors
└──────────┬───────────┘
           │ pass
           ▼
┌──────────────────────┐
│  opt -passes=verify  │  ← Catches semantic errors (SSA, types, CFG)
└──────────┬───────────┘
           │ pass
           ▼
┌──────────────────────┐
│  Semantic Triviality │  ← Detects mutations identical to seed
└──────────┬───────────┘
           │
           ▼
      Valid Mutant
```

### 2.5 Differential Testing

Valid mutants are compiled at two optimization levels and their outputs compared:
- **Baseline**: `clang -O0` (no optimization)
- **Target**: `clang -O2` (aggressive optimization)
- **Execution**: Direct (if `main` exists) or auto-generated C harness
- **Mismatch Categories**: `output_mismatch`, `runtime_crash`, `timeout`, `compile_error`, `link_error`, `missing_main`

## 3. Design Alternatives Considered

### 3.1 LLM Model Selection

| Alternative | Pros | Cons | Decision |
|---|---|---|---|
| GPT-4 / Claude (API) | Higher quality | Cost, latency, privacy | ❌ Rejected |
| CodeLlama 7B | Code-specialized | High RAM, slow on CPU | ❌ Rejected |
| Qwen 2.5:1.5B (Ollama) | Fast, local, free | Lower capability | ✅ Selected |
| No LLM (grammar-only) | Deterministic | Limited semantic diversity | ❌ Rejected (used as baseline) |

**Rationale**: Local Ollama deployment gives full control over latency, cost, and privacy. The 1.5B model balances generation quality with resource constraints.

### 3.2 Validation Architecture

| Alternative | Pros | Cons | Decision |
|---|---|---|---|
| `llvm-as` only | Simple | Misses semantic errors | ❌ Rejected |
| Full `opt -O2` pipeline | Catches more | Slow, noisy errors | ❌ Rejected |
| Rule pre-check + `llvm-as` + `opt verify` | Fast reject + thorough | More complex | ✅ Selected |
| Clang frontend parsing | Richer diagnostics | LLVM IR ≠ C source | ❌ Rejected |

**Rationale**: The layered approach avoids expensive subprocess calls for obviously invalid IR (rule checks reject ~20% before `llvm-as`).

### 3.3 Deduplication Strategy

| Alternative | Pros | Cons | Decision |
|---|---|---|---|
| Exact string comparison | Simple | Whitespace/comment sensitive | ❌ Rejected |
| AST-level comparison | Semantically accurate | Requires LLVM C++ bindings | ❌ Rejected |
| Normalized hash (MD5) | Fast, comment/register-agnostic | Imperfect normalization | ✅ Selected |

**Rationale**: The normalized hash strips comments, collapses whitespace, and anonymizes register names — catching the most common duplicate patterns without requiring LLVM library bindings.

### 3.4 Frontend Architecture

| Alternative | Pros | Cons | Decision |
|---|---|---|---|
| CLI-only | Simple | Poor UX for monitoring | ❌ Rejected |
| Streamlit | Quick prototyping | Limited interactivity | ❌ Rejected |
| React + Vite | Rich UI, component model | More setup | ✅ Selected |

### 3.5 Deployment Architecture

| Alternative | Pros | Cons | Decision |
|---|---|---|---|
| Bare metal | No overhead | Dependency hell | ❌ Rejected |
| Docker single container | Simple | Monolithic | ❌ Rejected |
| Docker Compose (multi-service) | Isolated, reproducible | More YAML | ✅ Selected |

## 4. Key Design Decisions

1. **Microservices via Docker Compose** — Four containers (Ollama, Backend, LLVM-Tester, Frontend) for isolation and reproducibility
2. **FastAPI backend** — Async support for LLM calls, automatic OpenAPI docs, Pydantic validation
3. **Process-isolated validation** — Each mutant validated in a spawned subprocess to prevent crashes from poisoning the API
4. **Manifest tracking** — Centralized JSON manifest for all mutant metadata, enabling offline analysis
5. **Three-way comparison** — LLM vs. Grammar vs. Random provides statistical rigor for evaluating LLM effectiveness

## 5. Scalability Considerations

- **Batch processing** with configurable `MAX_WORKERS` for parallel validation
- **Streaming LLM responses** (prepared, currently using `stream=false` for simplicity)
- **File-based logging** (JSON + CSV) avoids database setup while remaining parseable
- **Stateless API** design — each request is self-contained, enabling horizontal scaling
