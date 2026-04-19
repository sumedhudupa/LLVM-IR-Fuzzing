"""
app/routes/differential.py
APIRouter for the Differential Testing group.
Source: CONTEXT.json → apis.endpoints[POST /api/v1/differential/run]
        CONTEXT.json → apis.endpoints[GET  /api/v1/differential/results]
        CONTEXT.json → architecture.components[Differential Tester]
        CONTEXT.json → architecture.components[Comparison Engine]

Routes:
  POST /api/v1/differential/run      →  DifferentialService.run()
  GET  /api/v1/differential/results  →  DifferentialService.get_results()
"""
from fastapi import APIRouter, HTTPException
from app.models.differential import (
    DifferentialRunRequest,
    DifferentialRunResponse,
    DifferentialResultsResponse,
)
from app.services.differential_service import DifferentialService
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/differential", tags=["Differential"])
logger = get_logger(__name__)


@router.post(
    "/run",
    response_model=DifferentialRunResponse,
    summary="Run differential testing on all valid mutants",
    responses={
        404: {"description": "no valid mutants found"},
        500: {"description": "llc or harness execution failed"},
    },
)
async def run_differential(body: DifferentialRunRequest) -> DifferentialRunResponse:
    """
    POST /api/v1/differential/run
    Source: CONTEXT.json → apis.endpoints[POST /api/v1/differential/run]
    Delegates to Differential Tester component.
    """
    logger.info("run_differential: %s vs %s", body.baseline_opt, body.target_opt)
    try:
        return await DifferentialService.run(body)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="no valid mutants found") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="llc or harness execution failed"
        ) from exc


@router.get(
    "/results",
    response_model=DifferentialResultsResponse,
    summary="Get summary of differential testing results",
    responses={
        404: {"description": "results file not found"},
        500: {"description": "file read error"},
    },
)
async def get_differential_results() -> DifferentialResultsResponse:
    """
    GET /api/v1/differential/results
    Source: CONTEXT.json → apis.endpoints[GET /api/v1/differential/results]
    Reads logs/results.csv and returns structured rows.
    """
    logger.info("get_differential_results called")
    try:
        return await DifferentialService.get_results()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="results file not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="file read error") from exc


@router.get(
    "/comparison",
    summary="Get comparison metrics (LLM vs Grammar)",
)
async def get_comparison_metrics():
    """
    GET /api/v1/differential/comparison
    Source: CONTEXT.json → architecture.components[Comparison Engine]
    """
    logger.info("get_comparison_metrics called")
    try:
        return await DifferentialService.get_comparison()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

