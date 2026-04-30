# Phase 3 Features Documentation

## Manifest Tracking System

### Overview

The Manifest Tracking system provides comprehensive metadata aggregation for all generated mutants. It combines raw generation logs with validation results to create a structured, queryable manifest of the entire pipeline output.

### Architecture

```
raw_mutants.json (newline-delimited)
    ↓
ManifestTracker.load_raw_mutants()
    ↓
[RawMutantEntry, ...]
    ↓
ManifestTracker.generate_manifest()
    ← + validity_logs.json (JSON array)
    ← + seed_ir_hash computation
    ← + seed file lookup
    ↓
[ManifestEntry, ...] + ManifestSummary
    ↓
ManifestTracker.save_manifest()
    ↓
logs/manifest.json (formatted JSON)
    ↓
API: GET /api/v1/manifest
    ↓
Frontend: Display & query manifest
```

### API Endpoint

**GET /api/v1/manifest**

Returns comprehensive manifest with all mutants and statistics.

**Response Schema**:
```json
{
  "generated_at": "2026-04-30T06:25:49.200021Z",
  "mutants": [
    {
      "mutant_id": "seed_arith_llm_mut_0",
      "seed_name": "seed_arith.ll",
      "source": "llm | grammar | random",
      "mutation_type": "strategy_name",
      "seed_ir_hash": "md5_hash",
      "is_valid": true | false,
      "trivial": true | false,
      "is_duplicate": true | false,
      "content_hash": "md5_hash | null",
      "error_type": "syntax | ssa | type | cfg | undef | other | timeout | null",
      "generation_time_s": 1.234 | null,
      "status": "generated | validated | failed",
      "timestamp": "2026-04-30T06:25:00.000000Z"
    }
  ],
  "summary": {
    "total_generated": 111,
    "valid_count": 5,
    "invalid_count": 106,
    "duplicate_count": 0,
    "trivial_count": 0,
    "by_mutator_type": {
      "llm": {
        "generated": 111,
        "valid": 5,
        "invalid": 106,
        "duplicate": 0,
        "trivial": 0
      },
      "grammar": { ... },
      "random": { ... }
    },
    "by_error_type": {
      "syntax": 10,
      "ssa": 2,
      "type": 5,
      "other": 89
    }
  }
}
```

### ManifestEntry Schema

Per-mutant metadata container:

| Field | Type | Description |
|---|---|---|
| mutant_id | string | Unique identifier (e.g., "seed_arith_llm_mut_0") |
| seed_name | string | Source seed filename (e.g., "seed_arith.ll") |
| source | string | Generator type: "llm", "grammar", or "random" |
| mutation_type | string | Strategy name (e.g., "arithmetic_substitution") |
| seed_ir_hash | string \| null | MD5 hash of seed IR |
| is_valid | boolean | Passed LLVM validation |
| trivial | boolean | Valid but semantically equivalent to seed |
| is_duplicate | boolean | Duplicate IR (same normalized hash) |
| content_hash | string \| null | Normalized MD5 hash of mutant IR |
| error_type | string \| null | Error category if invalid |
| generation_time_s | number \| null | Time to generate mutant |
| status | string | "generated", "validated", or "failed" |
| timestamp | string | ISO 8601 creation timestamp |

### ManifestSummary Schema

Aggregated statistics:

| Field | Type | Description |
|---|---|---|
| total_generated | int | Total mutants in batch |
| valid_count | int | Mutants passing LLVM verification |
| invalid_count | int | Mutants failing verification |
| duplicate_count | int | Mutants with duplicate IR hashes |
| trivial_count | int | Valid mutants semantically equivalent to seed |
| by_mutator_type | dict | Per-generator statistics |
| by_error_type | dict | Error category breakdown |

### Service Integration

**ManifestTracker** (`app/services/manifest_service.py`)

Main service class with methods:

```python
def __init__(logs_dir: Path, results_dir: Path | None = None):
    """Initialize tracker with logs directory."""

def load_raw_mutants() -> dict[str, dict]:
    """Load newline-delimited raw_mutants.json."""

def load_validity_logs() -> dict[str, dict]:
    """Load JSON array validity_logs.json."""

def generate_manifest(seed_dir: Path) -> tuple[list[ManifestEntry], ManifestSummary]:
    """Aggregate logs into manifest entries and summary."""

def save_manifest(seed_dir: Path) -> Path:
    """Generate and save manifest.json."""

def filter_entries(source: str | None = None,
                   mutation_type: str | None = None,
                   is_valid: bool | None = None,
                   trivial: bool | None = None) -> list[ManifestEntry]:
    """Query manifest entries by criteria."""

def get_summary() -> ManifestSummary | None:
    """Retrieve summary statistics."""

def compute_seed_ir_hash(seed_path: Path) -> str | None:
    """Compute MD5 hash of seed IR."""
```

**AnalysisService Integration** (`app/services/analysis_service.py`)

```python
async def get_manifest() -> dict:
    """Generate and retrieve manifest."""
```

### Usage Examples

#### Retrieve Full Manifest
```bash
curl -X GET http://localhost:8000/api/v1/analysis/manifest
```

#### Filter Valid LLM Mutants
```python
from app.services.manifest_service import ManifestTracker
from pathlib import Path

tracker = ManifestTracker(Path("./logs"))
tracker.save_manifest(Path("./seeds"))

valid_llm = tracker.filter_entries(source="llm", is_valid=True)
for entry in valid_llm:
    print(f"{entry.mutant_id}: {entry.mutation_type}")
```

#### Analyze Error Distribution
```python
# Get summary
summary = tracker.get_summary()
print(f"Validity rate: {summary.valid_count / summary.total_generated:.2%}")
print("Error breakdown:", summary.by_error_type)
```

#### Per-Mutator Comparison
```python
summary = tracker.get_summary()
for mutator_type, stats in summary.by_mutator_type.items():
    rate = stats['valid'] / stats['generated'] if stats['generated'] > 0 else 0
    print(f"{mutator_type}: {rate:.2%} valid")
```

### Data Flow Integration

**Raw Mutant Generation**:
```
[Seed] → LLMMutator/GrammarMutator/RandomMutator
    → logs/raw_mutants.json entry:
       {id, seed_name, mutator_type, strategy, status, timestamp, ...}
    → [Mutant file written to disk]
```

**Validation Pipeline**:
```
[Mutant] → RuleValidator → llvm-as → opt -passes=verify
    → logs/validity_logs.json entry:
       {mutant_id, is_valid, error_type, trivial, content_hash, ...}
    → [File moved to valid_mutants/ or invalid_mutants/]
```

**Manifest Aggregation**:
```
raw_mutants.json + validity_logs.json + seed_files
    → ManifestTracker.generate_manifest()
    → [Entries merged, statistics computed]
    → logs/manifest.json
```

### Configuration

The manifest tracker uses configuration from `app/config.py`:

```python
LOGS_DIR: Path = Path("./logs")      # Where manifest.json is saved
SEED_DIR: Path = Path("./seeds")     # For seed IR hash computation
```

### Performance Characteristics

- **Aggregation**: O(n) where n = total mutants
- **Filtering**: O(n) linear scan (index for production)
- **Hash computation**: O(m) where m = seed file size
- **File I/O**: Single pass for manifest generation

### Backward Compatibility

✅ Manifest tracking is purely additive:
- Existing raw_mutants.json format unchanged
- Existing validity_logs.json format unchanged
- New manifest.json is generated on-demand
- Does not modify pipeline behavior
- Optional API endpoint (can be ignored by existing clients)

### Error Handling

**Graceful Degradation**:
- Empty manifest if logs don't exist
- Skips malformed JSON lines
- Returns None for missing seed files
- Continues aggregation if some entries are incomplete

**Logging**:
- All errors logged via standard logger
- No exceptions bubble up from manifest service
- Summary always includes partial results if available

### Testing

**Unit Test Coverage**: 16 test cases
- ✅ Load raw mutants (newline-delimited JSON)
- ✅ Load validity logs (JSON array)
- ✅ Manifest aggregation logic
- ✅ Summary statistics computation
- ✅ Per-mutator-type breakdown
- ✅ Error categorization
- ✅ File persistence
- ✅ Filtering operations
- ✅ Edge cases (empty logs, malformed JSON)
- ✅ Dataclass initialization
- ✅ Hash computation

Run tests:
```bash
cd llm-mutator
python -m pytest tests/test_phase3.py -v
```

### Future Enhancements

**Potential Improvements**:
1. Persist manifest.json between sessions (with versioning)
2. Index manifest for fast queries
3. Export manifest to CSV/TSV for analysis
4. Webhook notifications on manifest updates
5. Differential manifest comparison (run_id tracking)
6. Timeline view of mutant generation (timestamp-based)
7. Heatmap of error rates by strategy/seed
8. Trend analysis (validity improvement over time)

---

## Integration with Phase 2 Features

The Manifest Tracking system aggregates all Phase 2 enhancements:

- **Subprocess Isolation**: `timeout_occurred` field tracks timeout events
- **Rule Validation**: `rule_check_passed` field tracks pre-validation results
- **IR Deduplication**: `is_duplicate` and `content_hash` fields track duplicates
- **Semantic Equivalence**: `trivial` field identifies semantically-useless valid mutants
- **Refinement Loop**: Could track `attempt_number` in future (currently in raw_mutants.json)

---

## Schema Documentation

### logs/manifest.json

**Location**: `logs/manifest.json`  
**Format**: JSON (pretty-printed)  
**Generated**: On first API call to `/api/v1/manifest`  
**Updated**: Regenerated each call (current data)

**Size Estimate**: ~2KB per 100 mutants (varies with error message length)

### logs/raw_mutants.json

**Location**: `logs/raw_mutants.json`  
**Format**: Newline-delimited JSON  
**Written**: During generation phase  
**One entry per**: Generated mutant (before validation)

**Current Fields**:
- id, seed_name, mutator_type, strategy
- path, status, created_at
- seed_size_bytes (added in Phase 2)
- attempt_number, refinement_succeeded (for LLM with refinement enabled)

### logs/validity_logs.json

**Location**: `logs/validity_logs.json`  
**Format**: JSON array  
**Written**: During validation phase  
**One entry per**: Validated mutant

**Current Fields**:
- mutant_id, is_valid, error_type
- verifier_output, trivial, is_duplicate
- content_hash, rule_check_passed
- timeout_occurred, created_at

---

## Troubleshooting

### Manifest is empty
- Check if raw_mutants.json exists: `ls -la logs/raw_mutants.json`
- Check if generation completed: Run a test generation first
- Verify logs are in correct location (relative to app cwd)

### Missing seed_ir_hash
- Check if seed files exist in SEED_DIR
- Verify seed_name matches filename in raw_mutants.json
- Hash computation is optional and continues if seed not found

### Statistics don't match count
- Some mutants may be missing from validity_logs if validation is incomplete
- Manifest aggregates only entries present in both logs
- Run full validation pipeline to ensure complete data

### High trivial_count
- This is expected and indicates few structural changes
- Use `trivial=True` filter to see which strategies produce trivials
- Consider updating mutation strategies to increase diversity

---

## Related Documentation

- See CLAUDE.md for additional requirements context
- See requirements.md for full specification
- See Phase 2 documentation for subprocess/deduplication details
