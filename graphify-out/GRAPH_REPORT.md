# Graph Report - Lab EL  (2026-04-29)

## Corpus Check
- 38 files · ~23,364 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 335 nodes · 539 edges · 64 communities detected
- Extraction: 59% EXTRACTED · 41% INFERRED · 0% AMBIGUOUS · INFERRED: 221 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]

## God Nodes (most connected - your core abstractions)
1. `DifferentialRunRequest` - 21 edges
2. `GenerateMutantsRequest` - 21 edges
3. `ValidateMutantsRequest` - 21 edges
4. `RandomMutator` - 20 edges
5. `MutantService` - 19 edges
6. `LLMMutator` - 17 edges
7. `GrammarMutator` - 17 edges
8. `DifferentialRunResponse` - 16 edges
9. `DifferentialResultsResponse` - 16 edges
10. `GenerateMutantsResponse` - 16 edges

## Surprising Connections (you probably didn't know these)
- `validate_mutant()` --calls--> `compute_ir_hash()`  [INFERRED]
  llm-mutator\app\filter_valid.py → llm-mutator\app\utils\ir_helpers.py
- `validate_batch()` --calls--> `validate()`  [INFERRED]
  llm-mutator\app\filter_valid.py → llm-mutator\app\services\mutant_service.py
- `StudyRunRequest` --uses--> `app/services/analysis_service.py Analysis services for invalid taxonomy and con`  [INFERRED]
  llm-mutator\app\models\analysis.py → llm-mutator\app\services\analysis_service.py
- `StudyRunRequest` --uses--> `Load a JSON log file (array format or newline-delimited).`  [INFERRED]
  llm-mutator\app\models\analysis.py → llm-mutator\app\services\analysis_service.py
- `StudyRunRequest` --uses--> `Analyze validity rate vs seed size for both mutator types.         Returns list`  [INFERRED]
  llm-mutator\app\models\analysis.py → llm-mutator\app\services\analysis_service.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.14
Nodes (38): GrammarMutator, LLMMutator, RandomMutator, Orchestrates LLM-guided LLVM IR mutation using Ollama.     Source: CONTEXT.json, Deterministic rule-based LLVM IR mutator.     Source: CONTEXT.json → architectu, Random (non-grammar-aware) LLVM IR mutator for baseline comparison.     Source:, GenerateMutantsRequest, GenerateMutantsResponse (+30 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (31): _classify_error(), _extract_seed_name(), filter_valid.py – Validity filtering via llvm-as + opt -passes=verify -disable-o, Validate a list of mutant IDs and return per-mutant results., Extract seed name from mutant_id like 'seed_arith_llm_mut_0' -> 'seed_arith.ll'., Classify LLVM verifier output into structured error types., Run rule-based pre-validation, then llvm-as + opt -S -verify on the mutant IR fi, validate_batch() (+23 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (25): generate_grammar_mutants(), generate_llm_mutants(), generate_random_mutants(), generate_mutants.py – LLM-guided and grammar-based LLVM IR mutation. Source: CO, Apply grammar mutations to one seed and write results to GRAMMAR_DIR., Apply random mutations to one seed and write results to RANDOM_DIR.          S, Async wrapper around LLMMutator.run()., Sync wrapper around GrammarMutator.run(). (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (22): OllamaClient, POST to /api/generate with stream=false.         Returns the raw 'response' str, Return True if Ollama is reachable and responding., Return True if LLM_MODEL is pulled and listed by Ollama., Build a tightly scoped mutation prompt for a small LLM         (qwen3:1.5b or g, Build a refinement prompt that includes previous error messages to guide correct, Attempt to generate one mutant via Ollama with optional refinement loop., Full LLM mutation pipeline for one seed file.          Steps (per CONTEXT.json (+14 more)

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (24): DifferentialResult, DifferentialResultsResponse, DifferentialRunRequest, DifferentialRunResponse, app/models/differential.py Pydantic schemas for the Differential Testing API gr, Request body for POST /api/v1/differential/run., Response schema for POST /api/v1/differential/run., Single row matching CONTEXT.json database.tables[differential_results]. (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.19
Nodes (17): app/models/seeds.py Pydantic schemas for the Seeds API group. Source: CONTEXT., A single seed IR file entry returned by GET /api/v1/seeds., Response schema for GET /api/v1/seeds., SeedFile, SeedListResponse, list_seeds(), app/routes/seeds.py APIRouter for the Seeds group. Source: CONTEXT.json → apis, GET /api/v1/seeds     Returns metadata for every .ll file in SEED_DIR.     Sou (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (9): BaseModel, InvalidTaxonomyResponse, app/models/analysis.py Schemas for analysis and controlled study endpoints., SeedSensitivityResponse, StudyHistoryResponse, StudyRunRequest, StudyRunResponse, app/routes/analysis.py APIRouter for analysis and controlled study endpoints. (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.26
Nodes (12): generateMutants(), getComparisonMetrics(), getDifferentialResults(), getInvalidTaxonomy(), getSeeds(), getSeedSensitivity(), getStudyHistory(), listMutants() (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (6): Flip one character to a different character., Delete one line from the IR., Duplicate one line in the IR., Sync wrapper around RandomMutator.run()., Replace one word with a similar-looking word., Apply one random mutation strategy.         Returns (mutated_ir, strategy_name)

### Community 9 - "Community 9"
Cohesion: 0.2
Nodes (9): compute_comparison_metrics(), _load_json_log(), comparison.py – Metrics comparison: LLM-based vs grammar-based mutation. Source, Helper to write to results.csv (redefined here for convenience)., Robustly load either a JSON list or newline-delimited JSON objects., Read logs and compute metrics for 'llm' and 'grammar' mutators.     Source: CON, write_results_row(), config.py – Centralised settings for the LLM Mutator service. Source: CONTEXT.j (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.35
Nodes (10): _compile_binary(), _find_harness_entry(), get_results(), _has_main(), _infer_mutator_type(), _normalize_mismatch_type(), run(), _safe_str() (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.25
Nodes (4): Sync wrapper around GrammarMutator.run()., Flip the predicate of the first icmp instruction found., Increment one integer constant by a small offset (1–3).         Skips constants, Apply one grammar rule keyed by index.         Returns (mutated_ir, strategy_na

### Community 12 - "Community 12"
Cohesion: 0.67
Nodes (1): app/main.py – FastAPI application entry point (modular version). Source: CONTEX

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Attempt to generate one mutant via Ollama.          Returns:             (ir_

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Full LLM mutation pipeline for one seed file.          Steps (per CONTEXT.json

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Deterministic rule-based LLVM IR mutator.     Source: CONTEXT.json → architectu

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Replace the first occurrence of one arithmetic opcode with another.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Flip the predicate of the first icmp instruction found.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Increment one integer constant by a small offset (1–3).         Skips constants

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Apply one grammar rule keyed by index.         Returns (mutated_ir, strategy_na

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Apply grammar mutations to one seed and write results to GRAMMAR_DIR.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Random (non-grammar-aware) LLVM IR mutator for baseline comparison.     Source:

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Flip one character to a different character.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Delete one line from the IR.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Duplicate one line in the IR.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Swap two adjacent lines in the IR.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Replace one word with a similar-looking word.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Apply one random mutation strategy.         Returns (mutated_ir, strategy_name)

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Apply random mutations to one seed and write results to RANDOM_DIR.          S

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Async wrapper around LLMMutator.run().

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Sync wrapper around GrammarMutator.run().

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Sync wrapper around RandomMutator.run().

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Async HTTP wrapper for the Ollama /api/generate endpoint.     Source: CONTEXT.j

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): POST to /api/generate with stream=false.         Returns the raw 'response' str

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Return True if Ollama is reachable and responding.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Return True if LLM_MODEL is pulled and listed by Ollama.

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Orchestrates LLM-guided LLVM IR mutation using Ollama.     Source: CONTEXT.json

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Build a tightly scoped mutation prompt for a small LLM         (qwen3:1.5b or g

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Attempt to generate one mutant via Ollama.          Returns:             (ir_

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Full LLM mutation pipeline for one seed file.          Steps (per CONTEXT.json

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Deterministic rule-based LLVM IR mutator.     Source: CONTEXT.json → architectu

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Replace the first occurrence of one arithmetic opcode with another.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Flip the predicate of the first icmp instruction found.

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Increment one integer constant by a small offset (1–3).         Skips constants

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Apply one grammar rule keyed by index.         Returns (mutated_ir, strategy_na

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Apply grammar mutations to one seed and write results to GRAMMAR_DIR.

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Random (non-grammar-aware) LLVM IR mutator for baseline comparison.     Source:

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Flip one character to a different character.

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Delete one line from the IR.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Duplicate one line in the IR.

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Swap two adjacent lines in the IR.

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Replace one word with a similar-looking word.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Apply one random mutation strategy.         Returns (mutated_ir, strategy_name)

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Apply random mutations to one seed and write results to RANDOM_DIR.          S

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Async wrapper around LLMMutator.run().

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Sync wrapper around GrammarMutator.run().

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Response schema for POST /api/v1/mutants/validate.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Run llvm-as + opt -S -verify on the mutant IR file.     Moves file to VALID_DIR

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Validate a list of mutant IDs and return per-mutant results.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Extract seed name from mutant_id like 'seed_arith_llm_mut_0' -> 'seed_arith.ll'.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Classify LLVM verifier output into structured error types.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Run llvm-as + opt -S -verify on the mutant IR file.     Moves file to VALID_DIR

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Validate a list of mutant IDs and return per-mutant results.

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Async wrapper around LLMMutator.run().

## Knowledge Gaps
- **129 isolated node(s):** `comparison.py – Metrics comparison: LLM-based vs grammar-based mutation. Source`, `Robustly load either a JSON list or newline-delimited JSON objects.`, `Read logs and compute metrics for 'llm' and 'grammar' mutators.     Source: CON`, `Helper to write to results.csv (redefined here for convenience).`, `config.py – Centralised settings for the LLM Mutator service. Source: CONTEXT.j` (+124 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 12`** (3 nodes): `health()`, `app/main.py – FastAPI application entry point (modular version). Source: CONTEX`, `main.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Attempt to generate one mutant via Ollama.          Returns:             (ir_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Full LLM mutation pipeline for one seed file.          Steps (per CONTEXT.json`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Deterministic rule-based LLVM IR mutator.     Source: CONTEXT.json → architectu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Replace the first occurrence of one arithmetic opcode with another.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Flip the predicate of the first icmp instruction found.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Increment one integer constant by a small offset (1–3).         Skips constants`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Apply one grammar rule keyed by index.         Returns (mutated_ir, strategy_na`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Apply grammar mutations to one seed and write results to GRAMMAR_DIR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Random (non-grammar-aware) LLVM IR mutator for baseline comparison.     Source:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Flip one character to a different character.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Delete one line from the IR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Duplicate one line in the IR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Swap two adjacent lines in the IR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Replace one word with a similar-looking word.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Apply one random mutation strategy.         Returns (mutated_ir, strategy_name)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Apply random mutations to one seed and write results to RANDOM_DIR.          S`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Async wrapper around LLMMutator.run().`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Sync wrapper around GrammarMutator.run().`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Sync wrapper around RandomMutator.run().`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Async HTTP wrapper for the Ollama /api/generate endpoint.     Source: CONTEXT.j`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `POST to /api/generate with stream=false.         Returns the raw 'response' str`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Return True if Ollama is reachable and responding.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Return True if LLM_MODEL is pulled and listed by Ollama.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Orchestrates LLM-guided LLVM IR mutation using Ollama.     Source: CONTEXT.json`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Build a tightly scoped mutation prompt for a small LLM         (qwen3:1.5b or g`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Attempt to generate one mutant via Ollama.          Returns:             (ir_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Full LLM mutation pipeline for one seed file.          Steps (per CONTEXT.json`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Deterministic rule-based LLVM IR mutator.     Source: CONTEXT.json → architectu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Replace the first occurrence of one arithmetic opcode with another.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Flip the predicate of the first icmp instruction found.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Increment one integer constant by a small offset (1–3).         Skips constants`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Apply one grammar rule keyed by index.         Returns (mutated_ir, strategy_na`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Apply grammar mutations to one seed and write results to GRAMMAR_DIR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Random (non-grammar-aware) LLVM IR mutator for baseline comparison.     Source:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Flip one character to a different character.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Delete one line from the IR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Duplicate one line in the IR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Swap two adjacent lines in the IR.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Replace one word with a similar-looking word.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Apply one random mutation strategy.         Returns (mutated_ir, strategy_name)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Apply random mutations to one seed and write results to RANDOM_DIR.          S`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Async wrapper around LLMMutator.run().`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Sync wrapper around GrammarMutator.run().`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Response schema for POST /api/v1/mutants/validate.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Run llvm-as + opt -S -verify on the mutant IR file.     Moves file to VALID_DIR`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Validate a list of mutant IDs and return per-mutant results.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Extract seed name from mutant_id like 'seed_arith_llm_mut_0' -> 'seed_arith.ll'.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Classify LLVM verifier output into structured error types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Run llvm-as + opt -S -verify on the mutant IR file.     Moves file to VALID_DIR`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Validate a list of mutant IDs and return per-mutant results.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `Async wrapper around LLMMutator.run().`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MutantService` connect `Community 0` to `Community 6`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `LLMMutator` connect `Community 0` to `Community 2`, `Community 3`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `RandomMutator` connect `Community 0` to `Community 8`, `Community 2`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `DifferentialRunRequest` (e.g. with `app/routes/differential.py APIRouter for the Differential Testing group. Sourc` and `POST /api/v1/differential/run     Source: CONTEXT.json → apis.endpoints[POST /a`) actually correct?**
  _`DifferentialRunRequest` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `GenerateMutantsRequest` (e.g. with `app/routes/mutants.py APIRouter for the Mutants group. Source: CONTEXT.json →` and `POST /api/v1/mutants/generate     Source: CONTEXT.json → apis.endpoints[POST /a`) actually correct?**
  _`GenerateMutantsRequest` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `ValidateMutantsRequest` (e.g. with `app/routes/mutants.py APIRouter for the Mutants group. Source: CONTEXT.json →` and `POST /api/v1/mutants/generate     Source: CONTEXT.json → apis.endpoints[POST /a`) actually correct?**
  _`ValidateMutantsRequest` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `RandomMutator` (e.g. with `MutantService` and `app/services/mutant_service.py Service layer for mutation generation and validi`) actually correct?**
  _`RandomMutator` has 9 INFERRED edges - model-reasoned connections that need verification._