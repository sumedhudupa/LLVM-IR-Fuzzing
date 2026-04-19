"""
app/models/seeds.py
Pydantic schemas for the Seeds API group.
Source: CONTEXT.json → apis.endpoints[GET /api/v1/seeds]
        CONTEXT.json → database.tables[raw_mutants] (seed_name, path, created_at)
"""
from pydantic import BaseModel


class SeedFile(BaseModel):
    """A single seed IR file entry returned by GET /api/v1/seeds."""
    name: str
    path: str
    size_bytes: float
    created_at: str   # ISO 8601


class SeedListResponse(BaseModel):
    """Response schema for GET /api/v1/seeds."""
    seeds: list[SeedFile]
