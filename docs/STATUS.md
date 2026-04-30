# Status

Last updated: 2026-04-30

## Task 1
Status: Complete

Integrated into the live workflow:

- `random` mutator is now exposed in the main frontend mutation form.
- Validation batch lookup now includes `random` mutants in addition to `llm` and `grammar`.
- LLM generation now uses the existing refinement loop settings from config.
- Manifest generation is now triggered automatically after validation batches.
- Comparison and analysis flows now include `random` data instead of treating it as backend-only.

Key files touched:

- `backend/api/app/generate_mutants.py`
- `backend/api/app/filter_valid.py`
- `backend/api/app/comparison.py`
- `backend/api/app/services/analysis_service.py`
- `frontend/src/pages/MutationJobForm.jsx`
- `frontend/src/pages/DifferentialDashboard.jsx`
- `frontend/src/pages/ComparisonView.jsx`

## Task 2
Status: Complete

Corrected partial or differently implemented behavior:

- Deduplication now happens before mutant files are written to disk, with duplicate candidates skipped for the current job.
- Manifest entries now use the required naming shape:
  - `mutant_id`
  - `seed_name`
  - `mutator_type`
  - `mutation_strategy`
  - `is_valid`
  - `error_type`
  - `content_hash`
  - `timestamp`
- Validation now performs per-mutant process isolation via a spawned worker wrapper.
- Validation now writes richer metadata used by manifest generation.
- Seed sensitivity and comparison metrics now include `random`.

Verification:

- Edited Python files were parsed successfully with a no-write `compile(...)` check.

Known note:

- `frontend/src/pages/ComparisonView.jsx` contains pre-existing encoding noise in some fallback display strings, but the random-mutator flow itself has been wired in.

## Task 3
Status: Complete with filesystem limitation

Implemented:

- Active API code copied and switched to `backend/api/`
- LLVM helper service copied to `backend/llvm-tester/`
- Runtime data organized under `backend/data/`
- Backend-side test fixtures organized under `backend/test_data/`
- Docker Compose updated to use the new backend paths
- Backend config defaults updated to the new `backend/data/*` layout
- Added `backend/README.md` to document the professionalized backend tree

Limitation:

- Windows denied physical move operations on several original root-level directories, so legacy root copies remain in place.
- The active workflow should use the `backend/` tree; the root-level legacy directories are now stale copies rather than the intended layout.
