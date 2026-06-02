# IMPLEMENTATION: LLVM IR Details

## 1. LLVM IR Background

LLVM IR (Intermediate Representation) is a typed, SSA-form (Static Single Assignment) language that serves as the common representation within the LLVM compiler infrastructure. It sits between source-level languages (C, C++, Rust) and machine code, making it the ideal target for compiler fuzzing because:

- **Optimization passes** operate directly on LLVM IR
- **SSA form** enforces that each variable is assigned exactly once
- **Strong typing** catches many errors at the IR level
- **Toolchain support** — `llvm-as`, `opt`, `llc`, `clang` form a complete pipeline

### 1.1 LLVM IR Structure

```llvm
; ModuleID = 'example.ll'
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @main() {
entry:
  %a = add i32 10, 20          ; arithmetic instruction
  %cmp = icmp sgt i32 %a, 25   ; comparison instruction
  br i1 %cmp, label %then, label %else  ; conditional branch

then:
  ret i32 1

else:
  ret i32 0
}
```

**Key components used in our mutations:**
- **Instructions**: `add`, `sub`, `mul`, `sdiv`, `icmp`, `br`, `ret`, `phi`
- **Types**: `i1`, `i8`, `i16`, `i32`, `i64`, `float`, `double`, `void`
- **SSA registers**: `%name` — each defined exactly once
- **Basic blocks**: Labeled sequences ending with a terminator (`ret`, `br`, `switch`)
- **Module metadata**: `; ModuleID`, `target datalayout`, `target triple`

## 2. LLVM Toolchain Integration

### 2.1 Validation Pipeline Tools

| Tool | Version | Purpose | Command |
|---|---|---|---|
| `llvm-as` | 17 | Assembles `.ll` → `.bc` (bitcode) | `llvm-as input.ll -o output.bc` |
| `opt` | 17 | Runs verification pass | `opt -S -passes=verify input.bc -o /dev/null` |
| `clang` | 17 | Compiles IR to executable | `clang -O0 input.ll -o binary` |

### 2.2 Validation Flow (Implementation Detail)

```python
# Stage 1: Assembly (catches syntax errors)
as_proc = subprocess.run(
    ["llvm-as", str(ll_path), "-o", str(bc_path)],
    capture_output=True, text=True,
    timeout=VALIDATION_TIMEOUT  # 30s default
)

# Stage 2: Verification (catches semantic errors)
opt_proc = subprocess.run(
    ["opt", "-S", "-passes=verify", str(bc_path), "-o", os.devnull],
    capture_output=True, text=True,
    timeout=VALIDATION_TIMEOUT
)
```

### 2.3 Error Classification

LLVM verifier errors are classified into structured categories:

| Error Type | Detection Pattern | Example |
|---|---|---|
| `syntax` | `llvm-as` failure, "expected" keyword | `expected instruction opcode` |
| `ssa` | "dominate", "phi" in stderr | `Instruction does not dominate all uses` |
| `type` | "type", "pointer", "mismatch" | `Stored value type does not match pointer operand type` |
| `cfg` | "terminate", "successor", "cfg" | `Block does not end with a terminator` |
| `undef` | "undef" in stderr | `Use of undefined value` |
| `timeout` | Subprocess exceeds 30s | Process killed after timeout |

## 3. Mutation Implementation Details

### 3.1 LLM-Guided Mutation

The LLM mutator uses the Ollama `/api/generate` endpoint with carefully engineered prompts:

```python
class OllamaClient:
    GENERATE_PATH = "/api/generate"

    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,        # qwen2.5:1.5b or qwen3:1.5b
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1500,    # prevent truncation
                "top_p": 0.90,
                "repeat_penalty": 1.1,
            },
        }
```

**Prompt Engineering for LLVM IR:**

Key constraints enforced in prompts:
1. **No C-style comments** — LLMs hallucinate `//`, must use `;`
2. **No x86 assembly suffixes** — Models output `addq` instead of `add`
3. **No inline arithmetic** — `%b+1` is invalid in LLVM IR
4. **PHI block references** — Must use `%entry` not `entry` (with `%` prefix)
5. **SSA compliance** — Every `%value` must be defined before use
6. **Full module output** — Prevents truncation of complex functions

### 3.2 IR Extraction from LLM Responses

LLM responses are noisy — they contain markdown, explanations, and thinking blocks. The extraction pipeline:

```python
def extract_ir(response_text: str) -> str | None:
    # Step 1: Strip <think>...</think> blocks (qwen3 chain-of-thought)
    text = strip_thinking_tags(response_text)

    # Step 2: Try code fence extraction (```llvm, ```ir, ```)
    for pattern in _FENCE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()

    # Step 3: Heuristic line-search fallback
    # Find first line starting with "; ModuleID", "define ", etc.
    for i, line in enumerate(text.splitlines()):
        if any(line.strip().startswith(tok) for tok in _IR_START_TOKENS):
            return "\n".join(lines[i:]).strip()

    return None  # Extraction failed
```

### 3.3 IR Sanitization

Post-extraction fixes for common LLM hallucination errors:

```python
def sanitize_ir(ir: str) -> str:
    # Fix 1: C-style comments → LLVM comments
    cleaned = re.sub(r"(?m)^\s*//", ";", ir)
    cleaned = re.sub(r"//", ";", cleaned)

    # Fix 2: x86 assembly suffixes (addq → add, subq → sub)
    for op in ["add", "sub", "mul", "div", "rem", "or", "and", "xor", "mov"]:
        cleaned = re.sub(rf"\b{op}[qlbw]\b", op, cleaned)

    # Fix 3: Strip trailing prose/markdown after last '}'
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        trailing = cleaned[last_brace + 1:].strip()
        if trailing and not any(c in trailing for c in ("!", "@", ";", "=")):
            cleaned = cleaned[:last_brace + 1]

    return cleaned.strip()
```

### 3.4 Grammar-Based Mutation

Deterministic transforms using regex-based pattern matching:

```python
# Arithmetic opcode swap table
_ARITH_SWAPS = [
    (r"\badd\b",  "sub"),   (r"\bsub\b",  "add"),
    (r"\bmul\b",  "sdiv"),  (r"\bsdiv\b", "mul"),
    (r"\budiv\b", "urem"),  (r"\burem\b", "udiv"),
    (r"\bsrem\b", "sdiv"),
    (r"\band\b",  "or"),    (r"\bor\b",   "and"),
    (r"\bxor\b",  "or"),
]

# icmp predicate flip pairs
_ICMP_FLIPS = [
    ("eq", "ne"),   ("ne", "eq"),
    ("slt", "sgt"), ("sgt", "slt"),
    ("sle", "sge"), ("sge", "sle"),
    ("ult", "ugt"), ("ugt", "ult"),
    ("ule", "uge"), ("uge", "ule"),
]
```

### 3.5 Deduplication via Normalized Hashing

```python
def compute_ir_hash(ir_text: str) -> str:
    # Step 1: Remove all comments (lines starting with ;)
    # Step 2: Collapse multiple whitespace to single space
    # Step 3: Anonymize registers (%identifier → %)
    # Step 4: Compute MD5 hash
    ir_normalized = re.sub(r'%[a-zA-Z_][a-zA-Z0-9_]*', '%', ir_collapsed)
    return hashlib.md5(ir_normalized.encode('utf-8')).hexdigest()
```

This normalization catches duplicates that differ only in:
- Comment text
- Whitespace formatting
- Register naming conventions

## 4. Rule-Based Pre-Validation (7 Structural Checks)

Before invoking expensive `llvm-as`/`opt` subprocesses, a fast Python-based validator rejects obviously invalid IR:

| # | Check | Error Category | What It Catches |
|---|---|---|---|
| 1 | Function definitions exist | `syntax` | Missing `define` statements |
| 2 | Balanced braces | `syntax` | Unclosed function bodies |
| 3 | Block terminators | `cfg` | Basic blocks without `ret`/`br`/`switch` |
| 4 | SSA property | `ssa` | Multiple definitions of same `%register` |
| 5 | PHI node placement | `ssa` | `phi` after non-phi instructions in a block |
| 6 | Branch target validity | `cfg` | Branches to non-existent labels |
| 7 | Type consistency | `type` | Integer ops on float types, float ops on int types |

**Implementation highlights:**
- Check 4 (SSA) uses a dictionary to track `%register = ...` definitions and flags duplicates
- Check 5 (PHI) scans each basic block for `phi` instructions after non-phi instructions
- Check 6 collects all block labels via regex, then verifies all `br label %target` references
- Check 7 cross-references opcode families (int ops: `add`, `sub`, etc.) with operand types

## 5. Differential Testing Implementation

### 5.1 Execution Modes

| Mode | Condition | Implementation |
|---|---|---|
| **Direct** | IR contains `define ... @main(...)` | Compile and run directly |
| **Harness** | No `main` function | Auto-generate C harness calling first zero-arg function |

### 5.2 Auto-Generated Harness

```c
// Generated for mutant without main()
extern int discovered_function(void);
int main(void) {
    return discovered_function();
}
```

The harness discovery function scans for `define (void|i32) @name()` patterns, excluding `@main`.

### 5.3 Mismatch Detection

```
Compile: clang -O0 input.ll -o bin_O0
Compile: clang -O2 input.ll -o bin_O2
Execute: ./bin_O0 > out_O0.txt
Execute: ./bin_O2 > out_O2.txt
Compare: diff out_O0.txt out_O2.txt
```

Mismatches are classified by failure stage:
- **compile** → `compile_error`, `link_error`, `missing_main`
- **execute** → `runtime_crash`, `timeout`
- **compare** → `output_mismatch`

## 6. Process Isolation

Each validation runs in a separate Python process (`multiprocessing.spawn`) to prevent:
- Segfaults in LLVM tools from crashing the API
- Resource leaks from accumulating
- Timeout handling at the process level

```python
def _run_validation_isolated(mutant_id: str, mutator_type: str) -> dict:
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=_validate_mutant_worker, args=(...))
    proc.start()
    proc.join(VALIDATION_TIMEOUT * 2 + 5)

    if proc.is_alive():
        proc.terminate()
        return {"error_type": "timeout", ...}
```

## 7. Manifest System

A centralized manifest (`logs/manifest.json`) tracks all mutant metadata:

```json
{
  "mutant_id": "seed_arith_llm_mut_0",
  "source_seed": "seed_arith.ll",
  "mutator_type": "llm",
  "mutation_strategy": "arithmetic_substitution",
  "is_valid": true,
  "is_trivial": false,
  "is_duplicate": false,
  "error_type": null,
  "content_hash": "a1b2c3d4e5f6...",
  "generated_at": "2026-05-01T12:00:00Z"
}
```

## 8. LLVM Version and Build Details

- **LLVM Version**: 17 (installed via `apt.llvm.org` in Docker)
- **Containers**: 
  - Backend: `python:3.11-slim-bookworm` + LLVM-17
  - LLVM-Tester: `ubuntu:22.04` + LLVM-17
- **Symlinked tools**: `clang-17 → clang`, `opt-17 → opt`, `llvm-as-17 → llvm-as`
