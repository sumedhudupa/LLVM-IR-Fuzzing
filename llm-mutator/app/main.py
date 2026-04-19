"""
app/main.py – FastAPI application entry point (modular version).
Source: CONTEXT.json → tasks.step_by_step[8]
        CONTEXT.json → apis.endpoints

Registers routers from app/routes/:
  seeds        →  GET  /api/v1/seeds
  mutants      →  POST /api/v1/mutants/generate
               →  POST /api/v1/mutants/validate
  differential →  POST /api/v1/differential/run
               →  GET  /api/v1/differential/results
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import seeds, mutants, differential
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="LLVM IR Fuzzing Pipeline API",
    description=(
        "AI-driven LLVM IR mutation, validity filtering, and differential testing. "
        "Source of truth: CONTEXT.json"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (allow React dev server) ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(seeds.router)
app.include_router(mutants.router)
app.include_router(differential.router)

logger.info("Registered routes: %s", [r.path for r in app.routes])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}
