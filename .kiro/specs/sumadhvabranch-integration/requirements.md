# Requirements Document: Sumadhvabranch Integration

## Introduction

This document specifies the requirements for integrating features from the `sumadhvabranch` research branch into the `main` branch of the LLVM IR mutation testing system. The integration aims to enhance the existing LLM-guided and grammar-based mutation pipeline with additional baseline comparisons, validation strategies, and metadata tracking capabilities developed during research.

The main branch currently implements a FastAPI-based service architecture with LLM-guided mutation (via Ollama), grammar-based mutation, LLVM-based validation (`llvm-as` + `opt -passes=verify`), and differential testing. The sumadhvabranch adds random mutation baselines, LLM refinement loops, rule-based pre-validation, IR deduplication, and enhanced manifest tracking.

## Glossary

- **Main_Branch**: The production branch with FastAPI service architecture, LLM mutation via Ollama, grammar mutation, and LLVM validation
- **Sumadhvabranch**: Research branch containing RandomMutator, refinement loops, rule-based validation, and IR deduplication features
- **PR_2_Branch**: Previous integration attempt by Copilot that partially integrated some features
- **LLM_Mutator**: Component that generates LLVM IR mutations using large language models via Ollama HTTP API
- **Grammar_Mutator**: Component that applies deterministic rule-based transformations to LLVM IR
- **Random_Mutator**: Component that applies non-grammar-aware random mutations (character flips, line operations)
- **Validation_Pipeline**: Multi-stage process for checking LLVM IR validity (rule-based checks, then LLVM verifier)
- **Refinement_Loop**: Iterative generation mechanism where LLM attempts are validated and retried on failure
- **Rule_Validator**: Pre-validation component that checks IR structure without invoking LLVM tools
- **IR_Deduplicator**: Component that computes normalized hashes to detect duplicate mutants
- **Manifest_Tracker**: System that records comprehensive metadata about mutants in JSON format
- **Subprocess_Isolation**: Mechanism to run LLVM tools in separate processes to prevent crashes from killing main process
- **Semantic_Equivalence_Checker**: Component that detects trivial mutations by comparing normalized IR

## Requirements

### Requirement 1: Random Mutation Baseline

**User Story:** As a researcher, I want to generate random (non-grammar-aware) mutations of LLVM IR, so that I can establish a baseline for comparing LLM-guided and grammar-based approaches.

#### Acceptance Criteria

1. THE Random_Mutator SHALL implement five mutation strategies: random_char_flip, random_line_delete, random_line_duplicate, random_line_swap, and random_word_replace
2. WHEN a seed IR is provided, THE Random_Mutator SHALL apply exactly one randomly selected mutation strategy
3. THE Random_Mutator SHALL record the mutation_type as "random_{strategy_name}" in the generation result
4. THE Random_Mutator SHALL validate each generated mutant using the Validation_Pipeline
5. THE Random_Mutator SHALL integrate with the existing MutantService.generate() API by accepting mutator_type="random"
6. THE Random_Mutator SHALL write mutants to a configurable output directory (RANDOM_DIR environment variable)
7. THE Random_Mutator SHALL log generation metadata to logs/raw_mutants.json following the existing schema
8. THE Random_Mutator SHALL support batch generation with configurable count parameter

### Requirement 2: LLM Refinement Loop

**User Story:** As a researcher, I want the LLM mutator to automatically retry failed generations, so that I can improve the validity rate of LLM-generated mutants without manual intervention.

#### Acceptance Criteria

1. THE LLM_Mutator SHALL support a max_attempts parameter (default: 3) for refinement iterations
2. WHEN an LLM-generated mutant fails rule-based validation, THE LLM_Mutator SHALL extract error messages from the Rule_Validator
3. WHEN retrying generation, THE LLM_Mutator SHALL include previous error messages in the prompt to guide correction
4. THE LLM_Mutator SHALL increment temperature by 0.1 on each retry attempt to increase output diversity
5. THE LLM_Mutator SHALL terminate refinement after max_attempts iterations regardless of validation result
6. THE LLM_Mutator SHALL record the number of attempts and final validation status in generation metadata
7. THE LLM_Mutator SHALL log each refinement attempt with attempt_number and validation_result to logs/raw_mutants.json
8. WHEN refinement succeeds before max_attempts, THE LLM_Mutator SHALL return the first valid mutant

### Requirement 3: Subprocess Crash Isolation

**User Story:** As a developer, I want LLVM validation tools to run in isolated subprocesses, so that crashes in llvm-as or opt do not terminate the main mutation pipeline.

#### Acceptance Criteria

1. THE Validation_Pipeline SHALL execute llvm-as in a subprocess with timeout protection (default: 30 seconds)
2. THE Validation_Pipeline SHALL execute opt -passes=verify in a subprocess with timeout protection (default: 30 seconds)
3. WHEN a subprocess times out, THE Validation_Pipeline SHALL classify the mutant as invalid with error_type="timeout"
4. WHEN a subprocess crashes, THE Validation_Pipeline SHALL capture the exit code and stderr output
5. THE Validation_Pipeline SHALL continue processing remaining mutants after a subprocess failure
6. THE Validation_Pipeline SHALL log subprocess failures with exit_code, stderr, and timeout_occurred fields
7. THE Validation_Pipeline SHALL clean up temporary files (.bc files) after subprocess completion or failure
8. THE Validation_Pipeline SHALL support configurable timeout values via environment variables

### Requirement 4: Rule-Based Pre-Validation

**User Story:** As a researcher, I want to pre-validate LLVM IR using lightweight structural checks, so that I can filter out obviously invalid mutants before invoking expensive LLVM tools.

#### Acceptance Criteria

1. THE Rule_Validator SHALL check for function definitions using regex pattern "define\\s+\\S+\\s+@\\w+"
2. THE Rule_Validator SHALL verify balanced braces (equal counts of '{' and '}')
3. THE Rule_Validator SHALL parse basic blocks and verify each block ends with a terminator instruction
4. THE Rule_Validator SHALL check SSA property by detecting multiple definitions of the same register
5. THE Rule_Validator SHALL validate PHI node placement (must appear before non-PHI instructions in blocks)
6. THE Rule_Validator SHALL verify branch targets reference existing block labels
7. THE Rule_Validator SHALL perform basic type consistency checks (integer ops use integer types, float ops use float types)
8. THE Rule_Validator SHALL classify errors into categories: syntax, ssa, type, cfg, undef, other
9. THE Rule_Validator SHALL return a RuleValidationResult with is_valid, error_type, and issues list
10. THE Validation_Pipeline SHALL invoke Rule_Validator before llvm-as to enable early rejection

### Requirement 5: IR Deduplication

**User Story:** As a researcher, I want to detect duplicate mutants automatically, so that I can avoid wasting resources on redundant validation and differential testing.

#### Acceptance Criteria

1. THE IR_Deduplicator SHALL compute MD5 hashes of normalized IR text for each mutant
2. THE IR_Deduplicator SHALL normalize IR by removing comments, collapsing whitespace, and stripping register names
3. THE IR_Deduplicator SHALL maintain an in-memory hash set of previously seen mutants during a generation session
4. WHEN a duplicate hash is detected, THE IR_Deduplicator SHALL mark the mutant with is_duplicate=true in metadata
5. THE IR_Deduplicator SHALL log duplicate mutants to logs/raw_mutants.json with content_hash field
6. THE Validation_Pipeline SHALL skip LLVM validation for mutants marked as duplicates
7. THE IR_Deduplicator SHALL support optional persistent deduplication across sessions via a hash cache file
8. THE IR_Deduplicator SHALL provide a utility function compute_ir_hash(ir_text) for external use

### Requirement 6: Valid/Invalid Manifest Tracking

**User Story:** As a researcher, I want comprehensive metadata about all generated mutants in a structured format, so that I can analyze generation patterns, error distributions, and mutation effectiveness.

#### Acceptance Criteria

1. THE Manifest_Tracker SHALL generate a manifest.json file in the results/ir/ directory
2. THE Manifest_Tracker SHALL include per-mutant entries with fields: mutant_id, file, source, mutation_type, seed_ir_hash, is_valid, trivial, is_duplicate, content_hash, error_type, generation_time_s, status, timestamp
3. THE Manifest_Tracker SHALL compute seed_ir_hash for each mutant to track which seed it originated from
4. THE Manifest_Tracker SHALL record whether valid mutants are semantically trivial using the Semantic_Equivalence_Checker
5. THE Manifest_Tracker SHALL aggregate data from logs/raw_mutants.json and logs/validity_logs.json
6. THE Manifest_Tracker SHALL update manifest.json after each pipeline run
7. THE Manifest_Tracker SHALL support filtering manifest entries by source, mutation_type, is_valid, and trivial fields
8. THE Manifest_Tracker SHALL provide summary statistics: total_generated, valid_count, invalid_count, duplicate_count, trivial_count

### Requirement 7: Integration with Existing Architecture

**User Story:** As a developer, I want the new features to integrate cleanly with the existing FastAPI service architecture, so that the API contracts remain stable and backward compatible.

#### Acceptance Criteria

1. THE MutantService.generate() SHALL accept mutator_type="random" in addition to "llm" and "grammar"
2. THE MutantService.generate() SHALL support optional refinement_enabled and max_attempts parameters for LLM mutations
3. THE MutantService.validate() SHALL invoke Rule_Validator before llvm-as validation
4. THE MutantService.validate() SHALL return enhanced MutantValidationResult with rule_check_passed, llvm_verify_passed, and trivial fields
5. THE Configuration SHALL add environment variables: RANDOM_DIR, ENABLE_REFINEMENT, MAX_REFINEMENT_ATTEMPTS, ENABLE_DEDUPLICATION, VALIDATION_TIMEOUT
6. THE API SHALL maintain backward compatibility with existing POST /api/v1/mutants/generate and POST /api/v1/mutants/validate endpoints
7. THE Logging SHALL extend logs/raw_mutants.json schema with fields: content_hash, is_duplicate, seed_ir_hash, attempt_number, refinement_succeeded
8. THE Logging SHALL extend logs/validity_logs.json schema with fields: rule_check_passed, llvm_verify_passed, trivial, timeout_occurred

### Requirement 8: Configuration and Feature Flags

**User Story:** As a developer, I want to enable or disable new features via configuration, so that I can control which enhancements are active without code changes.

#### Acceptance Criteria

1. THE Configuration SHALL provide ENABLE_REFINEMENT flag (default: false) to control LLM refinement loop
2. THE Configuration SHALL provide ENABLE_DEDUPLICATION flag (default: true) to control IR deduplication
3. THE Configuration SHALL provide ENABLE_RULE_VALIDATION flag (default: true) to control pre-validation
4. THE Configuration SHALL provide VALIDATION_TIMEOUT integer (default: 30) for subprocess timeout in seconds
5. THE Configuration SHALL provide MAX_REFINEMENT_ATTEMPTS integer (default: 3) for LLM retry limit
6. THE Configuration SHALL provide RANDOM_DIR path (default: "./mutants_random") for random mutant output
7. THE Configuration SHALL load all settings from environment variables or .env file
8. THE Configuration SHALL validate configuration values at startup and log warnings for invalid settings

### Requirement 9: Error Handling and Resilience

**User Story:** As a developer, I want the pipeline to handle errors gracefully, so that partial failures do not prevent completion of the entire mutation batch.

#### Acceptance Criteria

1. WHEN Rule_Validator encounters malformed IR, THE Validation_Pipeline SHALL log the error and mark the mutant as invalid
2. WHEN llvm-as subprocess times out, THE Validation_Pipeline SHALL log the timeout and continue with the next mutant
3. WHEN IR_Deduplicator hash computation fails, THE Validation_Pipeline SHALL log the error and proceed without deduplication for that mutant
4. WHEN Manifest_Tracker cannot write manifest.json, THE Pipeline SHALL log the error but complete the run
5. WHEN Random_Mutator generates invalid Python syntax during mutation, THE Random_Mutator SHALL catch the exception and return the original IR
6. WHEN LLM_Mutator refinement loop exhausts max_attempts, THE LLM_Mutator SHALL return the last attempt result regardless of validity
7. THE Pipeline SHALL log all errors with ERROR level including stack traces for debugging
8. THE Pipeline SHALL provide summary statistics including error counts by category at the end of each run

### Requirement 10: Testing and Validation

**User Story:** As a developer, I want comprehensive tests for the new features, so that I can verify correctness and prevent regressions.

#### Acceptance Criteria

1. THE Test_Suite SHALL include unit tests for Random_Mutator covering all five mutation strategies
2. THE Test_Suite SHALL include unit tests for Rule_Validator covering all error categories (syntax, ssa, type, cfg, undef)
3. THE Test_Suite SHALL include unit tests for IR_Deduplicator verifying hash computation and duplicate detection
4. THE Test_Suite SHALL include integration tests for LLM refinement loop with mock Ollama responses
5. THE Test_Suite SHALL include integration tests for subprocess isolation verifying timeout and crash handling
6. THE Test_Suite SHALL include end-to-end tests for the complete pipeline with all mutator types
7. THE Test_Suite SHALL verify backward compatibility by running existing API tests against the enhanced implementation
8. THE Test_Suite SHALL achieve minimum 80% code coverage for new components

## Integration Strategy

### Phase 1: Core Components (Random Mutator, Rule Validator, IR Deduplicator)
- Implement RandomMutator class in llm-mutator/app/generate_mutants.py
- Implement RuleValidationResult and prevalidate_ir() in llm-mutator/app/utils/rule_validation.py
- Implement compute_ir_hash() and deduplication logic in llm-mutator/app/utils/ir_helpers.py
- Add RANDOM_DIR, ENABLE_DEDUPLICATION, ENABLE_RULE_VALIDATION to config.py
- Update MutantService.generate() to support mutator_type="random"
- Update filter_valid.py to invoke Rule_Validator before llvm-as

### Phase 2: Refinement Loop and Subprocess Isolation
- Add refinement loop logic to LLMMutator._generate_one() with max_attempts parameter
- Refactor filter_valid.py to use subprocess.run() with timeout for llvm-as and opt
- Add timeout handling and error classification for subprocess failures
- Add ENABLE_REFINEMENT, MAX_REFINEMENT_ATTEMPTS, VALIDATION_TIMEOUT to config.py
- Update logs/raw_mutants.json schema to include attempt_number and refinement_succeeded

### Phase 3: Manifest Tracking and Enhanced Logging
- Implement Manifest_Tracker in llm-mutator/app/services/manifest_service.py
- Add seed_ir_hash, content_hash, is_duplicate fields to raw_mutants.json
- Add rule_check_passed, llvm_verify_passed, trivial fields to validity_logs.json
- Implement manifest.json generation in results/ir/ directory
- Add API endpoint GET /api/v1/manifest for retrieving manifest data

### Phase 4: Testing and Documentation
- Write unit tests for RandomMutator, Rule_Validator, IR_Deduplicator
- Write integration tests for refinement loop and subprocess isolation
- Write end-to-end tests for complete pipeline with all mutator types
- Update README.md with new features and configuration options
- Update API documentation with new parameters and response fields

## Conflicts and Challenges

### Architecture Differences
- **Challenge**: Sumadhvabranch uses a monolithic experiment_runner.py while main uses FastAPI service architecture
- **Resolution**: Extract individual components (RandomMutator, Rule_Validator) and integrate into existing service classes

### Validation Pipeline Differences
- **Challenge**: Sumadhvabranch uses llvmlite for validation while main uses llvm-as + opt subprocess calls
- **Resolution**: Keep main's subprocess approach for consistency, add rule-based pre-validation as an additional stage

### Logging Schema Differences
- **Challenge**: Sumadhvabranch uses different field names and structures in logs
- **Resolution**: Extend main's existing schema with new fields, maintain backward compatibility

### Deduplication Scope
- **Challenge**: Sumadhvabranch implements session-based deduplication, unclear if persistence is needed
- **Resolution**: Implement in-memory deduplication by default, add optional persistent cache via configuration flag

### Refinement Loop Integration
- **Challenge**: Refinement loop requires multiple Ollama calls which may increase latency
- **Resolution**: Make refinement optional via ENABLE_REFINEMENT flag, default to disabled for backward compatibility

## Success Criteria

1. All three mutator types (llm, grammar, random) generate mutants successfully via POST /api/v1/mutants/generate
2. Rule-based pre-validation reduces LLVM tool invocations by at least 30% for invalid mutants
3. IR deduplication detects and skips at least 10% of duplicate mutants in typical workloads
4. LLM refinement loop improves validity rate by at least 15% when enabled
5. Subprocess isolation prevents pipeline crashes when llvm-as or opt encounter malformed IR
6. Manifest.json provides comprehensive metadata for all generated mutants
7. All existing API tests pass without modification
8. New test suite achieves 80%+ code coverage for new components
9. Pipeline performance degrades by no more than 20% with all features enabled
10. Documentation clearly explains all new features and configuration options
