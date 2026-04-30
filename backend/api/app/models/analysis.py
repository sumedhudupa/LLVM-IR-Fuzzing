"""
app/models/analysis.py
Schemas for analysis and controlled study endpoints.
"""
from typing import Literal
from pydantic import BaseModel, Field


class InvalidTaxonomyResponse(BaseModel):
    total_invalid: int
    categories: dict[str, int]
    top_errors: list[dict[str, str | int]]


class StudyRunRequest(BaseModel):
    seed_names: list[str] = Field(..., min_length=1)
    count_per_seed: int = Field(default=5, ge=1)
    baseline_opt: str = Field(default="-O0")
    target_opt: str = Field(default="-O2")
    mutators: list[Literal["llm", "grammar", "random"]] = Field(default=["llm", "grammar", "random"])


class StudyRunResponse(BaseModel):
    run_id: str
    started_at: str
    completed_at: str
    settings: dict
    per_config: list[dict]
    aggregate: dict


class SeedSensitivityResponse(BaseModel):
    seeds: list[dict]
    total: int


class StudyHistoryResponse(BaseModel):
    runs: list[dict]
    total: int


class ManifestEntryModel(BaseModel):
    """Per-mutant entry in manifest."""
    mutant_id: str
    seed_name: str
    mutator_type: str
    mutation_strategy: str
    timestamp: str
    is_valid: bool = False
    error_type: str | None = None
    content_hash: str | None = None
    seed_ir_hash: str | None = None
    status: str = "generated"
    path: str = ""
    trivial: bool = False
    is_duplicate: bool = False
    generation_time_s: float | None = None
    source: str | None = None
    mutation_type: str | None = None


class ManifestSummaryModel(BaseModel):
    """Summary statistics."""
    total_generated: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    trivial_count: int = 0
    skipped_duplicate_count: int = 0
    by_mutator_type: dict = {}
    by_error_type: dict = {}


class ManifestResponse(BaseModel):
    """Manifest response with entries and summary."""
    generated_at: str
    mutants: list[ManifestEntryModel]
    summary: ManifestSummaryModel
