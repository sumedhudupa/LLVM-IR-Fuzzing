"""
app/models/mutants.py
Pydantic schemas for the Mutants API group.
Source: CONTEXT.json → apis.endpoints[POST /api/v1/mutants/generate]
        CONTEXT.json → apis.endpoints[POST /api/v1/mutants/validate]
        CONTEXT.json → database.tables[raw_mutants]
        CONTEXT.json → database.tables[validity_logs]
"""
from typing import Literal
from pydantic import BaseModel, Field

# ── Source: CONTEXT.json apis.endpoints[POST /api/v1/mutants/generate] ────────

MutatorType = Literal["llm", "grammar"]

class GenerateMutantsRequest(BaseModel):
    """Request body for POST /api/v1/mutants/generate."""
    seed_name: str = Field(..., description="filename of seed IR")
    mutator_type: MutatorType = Field(..., description="'llm' or 'grammar'")
    count: int = Field(default=5, ge=1, description="Number of mutants to generate")


class GenerateMutantsResponse(BaseModel):
    """Response schema for POST /api/v1/mutants/generate."""
    seed_name: str
    mutator_type: MutatorType
    mutant_count: int
    mutant_ids: list[str]
    status: str


# ── Source: CONTEXT.json apis.endpoints[POST /api/v1/mutants/validate] ────────

ErrorType = Literal["syntax", "ssa", "type", "cfg", "undef", "other"] | None

class ValidateMutantsRequest(BaseModel):
    """Request body for POST /api/v1/mutants/validate."""
    mutant_ids: list[str] = Field(..., description="IDs of mutants to validate")


class MutantValidationResult(BaseModel):
    """Per-mutant result matching CONTEXT.json database.tables[validity_logs]."""
    mutant_id: str
    is_valid: bool
    error_type: ErrorType = None
    verifier_output: str = ""
    trivial: bool = False  # True if valid but semantically equivalent to seed
    created_at: str        # ISO 8601


class ValidateMutantsResponse(BaseModel):
    """Response schema for POST /api/v1/mutants/validate."""
    results: list[MutantValidationResult]
