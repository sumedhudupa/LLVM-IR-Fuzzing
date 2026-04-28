"""
app/routes/analysis.py
APIRouter for analysis and controlled study endpoints.
"""
from fastapi import APIRouter, HTTPException

from app.models.analysis import (
    InvalidTaxonomyResponse,
    StudyRunRequest,
    StudyRunResponse,
    SeedSensitivityResponse,
    StudyHistoryResponse,
)
from app.services.analysis_service import AnalysisService
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/analysis", tags=["Analysis"])
logger = get_logger(__name__)


@router.get(
    "/invalid-taxonomy",
    response_model=InvalidTaxonomyResponse,
    summary="Get invalid mutant taxonomy from validity logs",
)
async def get_invalid_taxonomy() -> InvalidTaxonomyResponse:
    logger.info("get_invalid_taxonomy called")
    try:
        return await AnalysisService.get_invalid_taxonomy()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/run-study",
    response_model=StudyRunResponse,
    summary="Run controlled LLM vs grammar study matrix",
)
async def run_study(body: StudyRunRequest) -> StudyRunResponse:
    logger.info("run_study called with %d seed(s)", len(body.seed_names))
    try:
        return await AnalysisService.run_controlled_study(body)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/seed-sensitivity",
    response_model=SeedSensitivityResponse,
    summary="Get seed size vs validity rate analysis",
)
async def get_seed_sensitivity():
    logger.info("get_seed_sensitivity called")
    try:
        data = await AnalysisService.get_seed_sensitivity()
        return {"seeds": data, "total": len(data)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/study-history",
    response_model=StudyHistoryResponse,
    summary="Get history of controlled study runs",
)
async def get_study_history(limit: int = 20):
    logger.info("get_study_history called with limit=%d", limit)
    try:
        data = await AnalysisService.get_study_history(limit)
        return {"runs": data, "total": len(data)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
