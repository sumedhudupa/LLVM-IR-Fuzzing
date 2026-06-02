# Source Code Directory

This directory provides a unified entry point to the project's source code.

## Source Code Locations

The project source is organized as a modular microservices architecture:

### Backend (Python — FastAPI)
**Location**: [`../backend/api/app/`](../backend/api/app/)

| File | Description |
|---|---|
| `main.py` | FastAPI application entry point |
| `config.py` | Centralized configuration (env vars, paths, feature flags) |
| `generate_mutants.py` | Core mutation engine (LLM, Grammar, Random mutators) |
| `filter_valid.py` | Validation pipeline (rule checks + llvm-as + opt verify) |
| `comparison.py` | Metrics computation and comparison engine |

#### Routes (`../backend/api/app/routes/`)
| File | Description |
|---|---|
| `seeds.py` | Seed file management endpoints |
| `mutants.py` | Mutation generation and validation endpoints |
| `differential.py` | Differential testing endpoints |
| `analysis.py` | Analysis and study endpoints |

#### Services (`../backend/api/app/services/`)
| File | Description |
|---|---|
| `mutant_service.py` | Mutation orchestration logic |
| `manifest_service.py` | Manifest tracking and metadata |
| `differential_service.py` | Differential testing logic |
| `analysis_service.py` | Study history and seed sensitivity |
| `seed_service.py` | Seed file management |

#### Utilities (`../backend/api/app/utils/`)
| File | Description |
|---|---|
| `rule_validation.py` | 7 structural pre-validation checks |
| `ir_helpers.py` | IR extraction, sanitization, hashing, deduplication |
| `semantic_helpers.py` | Semantic triviality detection |
| `fs_helpers.py` | File system operations |
| `clang_helpers.py` | Clang compilation helpers |
| `logger.py` | Logging configuration |

#### Models (`../backend/api/app/models/`)
| File | Description |
|---|---|
| `mutants.py` | Pydantic schemas for mutant requests/responses |
| `differential.py` | Pydantic schemas for differential testing |
| `seeds.py` | Pydantic schemas for seed files |
| `analysis.py` | Pydantic schemas for analysis/studies |

### LLVM Tester (Bash)
**Location**: [`../backend/llvm-tester/`](../backend/llvm-tester/)

| File | Description |
|---|---|
| `docker-run.sh` | Validation + differential testing entrypoint |
| `Dockerfile` | Ubuntu 22.04 + LLVM-17 container |

### Frontend (React + Vite)
**Location**: [`../frontend/src/`](../frontend/src/)

| File | Description |
|---|---|
| `App.jsx` | Root component with routing |
| `api.js` | API client wrapper |
| `pages/SeedList.jsx` | Seed management page |
| `pages/MutationJobForm.jsx` | Mutation job configuration |
| `pages/ValidationStatus.jsx` | Validation results viewer |
| `pages/DifferentialDashboard.jsx` | Differential testing dashboard |
| `pages/ComparisonView.jsx` | Mutator comparison analytics |

### Tests
**Location**: [`../backend/api/tests/`](../backend/api/tests/)

| File | Description |
|---|---|
| `test_phase3.py` | Manifest tracking tests (16 tests) |
| `test_phase4.py` | Integration tests (38 tests) |
| `test_seeds_upload.py` | Seed upload tests |
| `verify_mutators.py` | Mutator verification utilities |
