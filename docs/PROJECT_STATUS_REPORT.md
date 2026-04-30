# LLVM IR Fuzzing Pipeline: Status & Future Work

This document summarizes the development progress, structural analysis, and concrete next steps to improve the AI-driven LLVM IR Fuzzing Pipeline.

## 1. Analysis & Progress Done Till Now

The core architecture to drive and test LLVM IR using Large Language Models has been fully realized. The following features have been successfully developed and analyzed:

*   **Infrastructure & Orchestration**: 
    Integrated FastAPI `llm-mutator`, an `llvm-tester` docker container, and a Vue/React `frontend` using a unified Docker-Compose configuration.
*   **Mutation Engines Implemented**: 
    *   **LLM Mutator**: Connected reliably to a local Ollama instance (running `qwen2.5:1.5b`) with a functioning retry mechanism, prompt template, and output extractor.
    *   **Grammar Mutator**: Added as a baseline comparison.
*   **Pipeline Visibility**: 
    Successfully integrated the `.gitignore` files to keep the generated bulk data (`/logs`, `/mutants_llm`, `/valid_mutants`, `/invalid_mutants`) out of Git while keeping them centrally available on Docker volumes.
*   **Validation Pipeline**: 
    Automated the use of `llvm-as` and `opt -passes=verify -disable-output` to correctly divide syntactically broken garbage from valid LLVM IR.
*   **Frontend Integration**:
    Implemented direct UI integration for seed files, meaning developers can now directly "Upload Seed" from the browser to dynamically update the fuzzing target state.
*   **Differential Tester & Bug Triage**: 
    *   Fixed a severe backend `500 Server Error` caused by malformed CSV logging (where Bash natively outputted strings like `"null"` into integer parser tracks).
    *   **Analyzed the `unknown` Bug**: Discovered that a large number of generated mutants were failing with an `'unknown'` label. After isolating a mutant (`seed_arith_llm_mut_0.ll`), we found that the LLM was intelligently modifying the code but incorrectly dropping the `define i32 @main()` wrappers. This caused `clang` linker errors `(undefined reference to 'main')` before execution even began.

---

## 2. Newly Implemented Study Features

The planned todo set has now been implemented to shift from pure pipeline setup to measurable study execution.

### 2.1 Differential Execution Reliability & Taxonomy
* Added explicit handling for mutants that drop `@main`: direct execution is used when `main` exists, and a harness mode is used when `main` is missing but a callable entry function can be detected.
* Differential results now classify failures into deterministic categories (`missing_main`, `compile_error`, `link_error`, `verification_error`, `runtime_crash`, `timeout`, `output_mismatch`, `unknown`) instead of overusing `unknown`.
* Result rows now include reproducibility metadata (`mutator_type`, `execution_mode`, `failure_stage`, `harness_entry`) while preserving backward compatibility when older CSV rows are parsed.

### 2.2 Invalid Mutant Failure Taxonomy Endpoint
* Added a backend analysis endpoint that mines `validity_logs` and aggregates invalid outputs into constraint-driven categories:
    * `broken_ssa`
    * `type_error`
    * `invalid_phi_dominance`
    * `syntax_parse`
    * `cfg_error`
    * `other_verifier_error`
* Added recurring error extraction (`top_errors`) for presentation-ready examples.

### 2.3 Controlled Comparative Study Automation
* Added an automated controlled-study API that runs matrix experiments over:
    * seed set
    * count per seed
    * mutator type (`llm`, `grammar`)
    * optimization pair (`baseline_opt`, `target_opt`)
* Each study run now records reproducible metadata (`run_id`, timestamps, settings, per-configuration metrics, aggregate rates) into persistent logs.

### 2.4 Frontend Analysis Enhancements
* Extended the comparison view to:
    * trigger controlled study runs,
    * show study-level aggregate metrics,
    * display invalid-mutant taxonomy counts and top recurring verifier errors,
    * include expanded comparison metrics (compile/link and runtime failure counters).

---

## 3. LLVM IR Validity Constraints Catalog (Living Draft)

This catalog is now aligned with observed failure domains and updated as new evidence arrives.

* **SSA / Dominance Constraints**
    * Every SSA value must be defined before use along valid dominance paths.
    * PHI incoming values/blocks must be structurally consistent with predecessor blocks.
* **Type Correctness Constraints**
    * Opcode operand widths and result types must match LLVM typing rules.
    * Pointer and integer operations must preserve legal type combinations.
* **Control-Flow Graph Constraints**
    * Terminators must be valid and successors must align with block structure.
    * Branch and PHI references must target valid existing labels.
* **Syntax / Parse Constraints**
    * Lexer/parser-level form must be valid (`llvm-as` acceptance).
    * IR text must avoid malformed tokens and incomplete instruction forms.
* **Executable Entry Constraints**
    * Differential execution needs either a valid `@main` or a harness-callable replacement entry.
    * Missing entry points are now explicitly tracked as `missing_main`.

---

## 4. Immediate Next Measurement Steps

1. Run controlled studies on a broader seed set and export per-mutator distributions.
2. Measure seed-size/context sensitivity to quantify truncation-related syntax failures.
3. Consolidate final report plots and map each plot to the main research question:
   * where LLM mutation improves exploration,
   * where it fails validity constraints,
   * where grammar mutation remains stronger.
