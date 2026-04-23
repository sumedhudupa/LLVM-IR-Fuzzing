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
    mutators: list[Literal["llm", "grammar"]] = Field(default=["llm", "grammar"])


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
