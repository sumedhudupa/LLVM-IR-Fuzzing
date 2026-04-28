The LLVM IR Fuzzing Pipeline is a research project exploring whether LLMs can generate valid LLVM IR test cases for compiler differential testing. The core      infrastructure exists (mutation, validation, differential testing, comparison), but several key features from CLAUDE.md and the Problem Statement are
     missing.

     This implementation addresses the remaining technical gaps identified in CLAUDE.md sections 1-7 and supports the Problem Statement deliverables #4 (study
     of semantically useless mutations) and #5 (comparison between LLM and grammar mutation).

     Implementation Overview

     Priority Order (as specified in CLAUDE.md)

     1. Seed Diversity (Section 2) - Create diverse seed files
     2. Trivial Detection (Section 1) - Detect semantically equivalent mutants
     3. Seed Size Logging + Sensitivity Endpoint (Section 4) - Measure context sensitivity
     4. Per-Strategy Breakdown (Section 5) - Strategy-level metrics
     5. Study History Endpoint + UI (Section 3) - View past study runs
     6. Deduplication (Section 6) - Handle duplicate differential results
     7. Validation Page Auto-Load (Section 7) - UX improvement

     ---
     Phase 1: Seed Diversity

     Goal

     Create 4 additional seed files alongside the existing seed_arith.ll to provide structural diversity for meaningful LLM vs grammar comparison.

     Files to Create

     1. seeds/seed_branch.ll - Conditional branch + icmp
     2. seeds/seed_loop.ll - Loop with PHI node (simpler than seed_arith's loop)
     3. seeds/seed_call.ll - Function call + return value
     4. seeds/seed_memory.ll - alloca + store + load

     Requirements for Each Seed

     - Valid LLVM IR (passes llvm-as + opt -passes=verify)
     - Define @main returning i32 for differential execution
     - 20-50 lines, focused on one IR pattern
     - Include proper target triple and datalayout

     ---
     Phase 2: Trivial/Semantically-Useless Mutation Detection

     Goal

     Detect valid mutants that are semantically equivalent to their seed (the "semantically useless mutations" from Problem Statement).

     Files to Modify/Create

     1. Create llm-mutator/app/utils/semantic_helpers.py
       - Function is_semantically_trivial(seed_path, mutant_path) -> bool
       - Runs opt -S -passes=instcombine,simplifycfg on both
       - Strips comments/whitespace, compares normalized output
     2. Modify llm-mutator/app/filter_valid.py
       - After validation passes, call is_semantically_trivial()
       - Add "trivial": bool to log_entry
       - Need to determine seed path from mutant_id
     3. Modify llm-mutator/app/models/mutants.py
       - Add trivial: bool = False to MutantValidationResult
     4. Modify llm-mutator/app/comparison.py
       - Rename existing trivial counter to other_invalid
       - Add new trivial_valid counter for valid-but-semantically-equivalent
       - Update _init_stats() and results formatting
     5. Modify frontend/src/pages/ComparisonView.jsx
       - Update COLUMNS array to include trivial_valid
       - Change label from "trivial" to "trivial (valid)"

     ---
     Phase 3: Seed-Size / Context-Sensitivity Measurement

     Goal

     Track seed size and analyze whether larger seeds cause more validity failures (truncation-related).

     Files to Modify

     1. Modify llm-mutator/app/generate_mutants.py
       - In LLMMutator.run(): add "seed_size_bytes": len(seed_ir.encode("utf-8")) to log entry
       - In GrammarMutator.run(): same addition
     2. Create llm-mutator/app/utils/semantic_helpers.py (already created in Phase 2, add to it)
     3. Modify llm-mutator/app/services/analysis_service.py
       - Add get_seed_sensitivity() method
       - Joins raw_mutants.json with validity_logs.json
       - Groups by (seed_name, mutator_type)
       - Returns validity_rate per group
     4. Modify llm-mutator/app/routes/analysis.py
       - Add GET /api/v1/analysis/seed-sensitivity endpoint
     5. Modify llm-mutator/app/models/analysis.py
       - Add SeedSensitivityResponse model
     6. Modify frontend/src/api.js
       - Add getSeedSensitivity() function
     7. Modify frontend/src/pages/ComparisonView.jsx
       - Add "Seed Sensitivity" table section
       - Columns: seed_name, size_bytes, LLM validity%, grammar validity%

     ---
     Phase 4: Per-Strategy Breakdown

     Goal

     Show which mutation strategies produce the most valid/interesting mutants.

     Files to Modify

     1. Modify llm-mutator/app/comparison.py
       - In compute_comparison_metrics(), add per_strategy dict
       - Structure: per_strategy[mutator_type][strategy_name] = {generated, valid, validity_rate}
       - Join raw_mutants.json (has strategy) with validity_logs.json (has is_valid)
     2. Modify frontend/src/pages/ComparisonView.jsx
       - Add "Per-Strategy Breakdown" table below main comparison
       - Columns: strategy, LLM valid%, grammar valid%
       - Only render if metrics.per_strategy exists

     ---
     Phase 5: Study History Endpoint + UI Panel

     Goal

     Allow viewing past controlled study runs for report export.

     Files to Modify

     1. Modify llm-mutator/app/services/analysis_service.py
       - Add get_study_history(limit: int = 20) -> list[dict]
       - Read study_runs.jsonl, return last N entries reversed (newest first)
     2. Modify llm-mutator/app/routes/analysis.py
       - Add GET /api/v1/analysis/study-history endpoint
       - Query param limit (default 20)
     3. Modify llm-mutator/app/models/analysis.py
       - Add StudyHistoryResponse model with runs: list[dict], total: int
     4. Modify frontend/src/api.js
       - Add getStudyHistory() function
     5. Modify frontend/src/pages/ComparisonView.jsx
       - Add collapsible "Study Run History" section
       - Table columns: run_id, started_at, seeds, count/seed, validity%, mismatch%
       - Load on mount alongside loadMetrics()

     ---
     Phase 6: Differential Results Deduplication

     Goal

     Prevent duplicate rows in results.csv when running differential multiple times.

     Files to Modify

     1. Modify llm-mutator/app/services/differential_service.py
       - Add run_id to CSV_FIELDNAMES
       - Modify write_results_row() to accept run_id parameter
       - Check for existing row with same mutant_id + baseline_level + target_level
       - If exists: overwrite instead of append (or use run_id filtering)
       - Simpler approach: add run_id column and pass it through
     2. Modify llm-mutator/app/models/differential.py
       - Add run_id: str | None = None to DifferentialRunRequest
     3. Update callers in analysis_service.py
       - Pass run_id when calling DifferentialService.run()

     ---
     Phase 7: Validation Status Page Auto-Load

     Goal

     Show validation results when navigating directly to Validate tab.

     Files to Modify

     1. Create endpoint GET /api/v1/mutants/list
       - Returns {valid: [mutant_ids], invalid: [mutant_ids]}
       - Scans VALID_DIR and INVALID_DIR
     2. Modify llm-mutator/app/routes/mutants.py
       - Add the list endpoint
     3. Modify llm-mutator/app/services/mutant_service.py
       - Add list_mutants() method
     4. Modify frontend/src/api.js
       - Add listMutants() function
     5. Modify frontend/src/pages/ValidationStatus.jsx
       - On mount: if mutantIds empty, call listMutants() and show summary
       - Add "Load All Validated Mutants" button
       - Show count of existing valid/invalid mutants

     ---
     Testing Strategy

     1. Seed validation: Run llvm-as + opt -passes=verify on each new seed
     2. Semantic trivial detection: Test with identical IR (True) and mutated constant (False)
     3. API endpoints: Test with curl/httpie
     4. Frontend: Manual testing in browser

     ---
     Files Summary

     New Files (8)

     - seeds/seed_branch.ll
     - seeds/seed_loop.ll
     - seeds/seed_call.ll
     - seeds/seed_memory.ll
     - llm-mutator/app/utils/semantic_helpers.py

     Modified Backend Files (9)

     - llm-mutator/app/filter_valid.py
     - llm-mutator/app/comparison.py
     - llm-mutator/app/generate_mutants.py
     - llm-mutator/app/models/mutants.py
     - llm-mutator/app/models/analysis.py
     - llm-mutator/app/services/analysis_service.py
     - llm-mutator/app/routes/analysis.py
     - llm-mutator/app/services/differential_service.py
     - llm-mutator/app/models/differential.py

     Modified Frontend Files (2)

     - frontend/src/api.js
     - frontend/src/pages/ComparisonView.jsx
     - frontend/src/pages/ValidationStatus.jsx

     New Backend Routes (3)

     - GET /api/v1/analysis/study-history
     - GET /api/v1/analysis/seed-sensitivity
     - GET /api/v1/mutants/list

     ---
     Verification Steps

     After implementation:

     1. Upload all 5 seed files via UI
     2. Run controlled study with all seeds
     3. Verify comparison table shows trivial_valid column
     4. Check study history panel shows the run
     5. Verify seed sensitivity table shows size vs validity correlation
     6. Check per-strategy breakdown shows strategy-level metrics
     7. Run differential twice on same mutants - verify no duplicates
     8. Navigate to Validation tab directly - verify it shows existing mutants