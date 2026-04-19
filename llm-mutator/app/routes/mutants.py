"""
app/routes/mutants.py
APIRouter for the Mutants group.
Source: CONTEXT.json → apis.endpoints[POST /api/v1/mutants/generate]
        CONTEXT.json → apis.endpoints[POST /api/v1/mutants/validate]
        CONTEXT.json → architecture.components[LLM Mutator Service]
        CONTEXT.json → architecture.components[Validity Filter]

Routes:
  POST /api/v1/mutants/generate  →  MutantService.generate()
  POST /api/v1/mutants/validate  →  MutantService.validate()
"""
from fastapi import APIRouter, HTTPException
from app.models.mutants import (
    GenerateMutantsRequest,
    GenerateMutantsResponse,
    ValidateMutantsRequest,
    ValidateMutantsResponse,
)
from app.services.mutant_service import MutantService
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/mutants", tags=["Mutants"])
logger = get_logger(__name__)


@router.post(
    "/generate",
    response_model=GenerateMutantsResponse,
    summary="Trigger LLM-guided or grammar-based IR mutation",
    responses={
        400: {"description": "invalid request body"},
        500: {"description": "Ollama or mutation script failed"},
    },
)
async def generate_mutants(body: GenerateMutantsRequest) -> GenerateMutantsResponse:
    """
    POST /api/v1/mutants/generate
    Source: CONTEXT.json → apis.endpoints[POST /api/v1/mutants/generate]
    Delegates to LLM Mutator Service or grammar pipeline based on mutator_type.
    """
    logger.info("generate_mutants: seed=%s type=%s count=%d",
                body.seed_name, body.mutator_type, body.count)
    try:
        return await MutantService.generate(body)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="Ollama or mutation script failed"
        ) from exc


@router.post(
    "/validate",
    response_model=ValidateMutantsResponse,
    summary="Run llvm-as + opt -passes=verify -disable-output on a batch of mutants",
    responses={
        404: {"description": "mutant not found"},
        500: {"description": "llvm-as / opt command failed"},
    },
)
async def validate_mutants(body: ValidateMutantsRequest) -> ValidateMutantsResponse:
    """
    POST /api/v1/mutants/validate
    Source: CONTEXT.json → apis.endpoints[POST /api/v1/mutants/validate]
    Delegates to Validity Filter component.
    """
    logger.info("validate_mutants: %d id(s)", len(body.mutant_ids))
    try:
        return await MutantService.validate(body)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="mutant not found") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="llvm-as / opt command failed"
        ) from exc
