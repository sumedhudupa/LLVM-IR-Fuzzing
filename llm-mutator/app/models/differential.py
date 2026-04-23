"""
app/models/differential.py
Pydantic schemas for the Differential Testing API group.
Source: CONTEXT.json → apis.endpoints[POST /api/v1/differential/run]
        CONTEXT.json → apis.endpoints[GET  /api/v1/differential/results]
        CONTEXT.json → database.tables[differential_results]
"""
from typing import Literal
from pydantic import BaseModel, Field

MismatchType = Literal[
    "output_mismatch",
    "runtime_crash",
    "timeout",
    "verification_error",
    "compile_error",
    "link_error",
    "missing_main",
    "unknown",
] | None

# ── Source: CONTEXT.json apis.endpoints[POST /api/v1/differential/run] ────────

class DifferentialRunRequest(BaseModel):
    """Request body for POST /api/v1/differential/run."""
    baseline_opt: str = Field(default="-O0", description="e.g. -O0")
    target_opt:   str = Field(default="-O2", description="e.g. -O2")
    max_mutants:  int | None = Field(default=None, description="cap on mutants tested")
    mutant_ids:   list[str] | None = Field(default=None, description="specific valid mutant IDs to test")
    run_id:       str | None = Field(default=None, description="optional run identifier for deduplication")


class DifferentialRunResponse(BaseModel):
    """Response schema for POST /api/v1/differential/run."""
    total_valid:      int
    total_mismatches: int
    mismatch_rate:    float
    status:           str
    log_file:         str


# ── Source: CONTEXT.json apis.endpoints[GET /api/v1/differential/results] ─────

class DifferentialResult(BaseModel):
    """Single row matching CONTEXT.json database.tables[differential_results]."""
    mutant_id:          str
    baseline_level:     str            # e.g. -O0
    target_level:       str            # e.g. -O2
    is_mismatch:        bool
    mismatch_type:      MismatchType = None
    mutator_type:       Literal["llm", "grammar", "unknown"] = "unknown"
    execution_mode:     Literal["direct", "harness", "unknown"] = "unknown"
    failure_stage:      str | None = None
    harness_entry:      str | None = None
    runtime_ms_baseline: float | None = None
    runtime_ms_target:   float | None = None
    created_at:         str            # ISO 8601


class DifferentialResultsResponse(BaseModel):
    """Response schema for GET /api/v1/differential/results."""
    results: list[DifferentialResult]
