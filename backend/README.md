# Backend Layout

## Active Structure

- `api/`
  - FastAPI service, mutation pipeline, validation pipeline, analysis services, tests
- `llvm-tester/`
  - LLVM helper container assets
- `data/`
  - Runtime seeds, generated mutants, valid/invalid outputs, logs, manifest
- `test_data/`
  - Backend-side test fixtures and test outputs

## Important Paths

- Seeds: `backend/data/seeds/`
- LLM mutants: `backend/data/mutants_llm/`
- Grammar mutants: `backend/data/mutants_grammar/`
- Random mutants: `backend/data/mutants_random/`
- Valid mutants: `backend/data/valid_mutants/`
- Invalid mutants: `backend/data/invalid_mutants/`
- Logs and manifest: `backend/data/logs/`

## Notes

- `docker-compose.yml` now points to `backend/api`, `backend/llvm-tester`, and `backend/data`.
- The workspace still contains legacy root-level copies that could not be physically removed in this session because Windows denied move operations on those paths.
- The active backend workflow should use the `backend/` tree.
