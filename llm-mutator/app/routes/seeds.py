"""
app/routes/seeds.py
APIRouter for the Seeds group.
Source: CONTEXT.json → apis.endpoints[GET /api/v1/seeds]
        CONTEXT.json → architecture.components  (no dedicated component; seeds
        are filesystem inputs consumed by the LLM Mutator Service)

Route path:  GET /api/v1/seeds   (prefix set in main.py)
"""
from fastapi import APIRouter, HTTPException
from app.models.seeds import SeedListResponse
from app.services.seed_service import SeedService
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/seeds", tags=["Seeds"])
logger = get_logger(__name__)


@router.get(
    "",
    response_model=SeedListResponse,
    summary="List all seed IR files",
    responses={
        404: {"description": "seeds directory not found"},
        500: {"description": "filesystem read error"},
    },
)
async def list_seeds() -> SeedListResponse:
    """
    GET /api/v1/seeds
    Returns metadata for every .ll file in SEED_DIR.
    Source: CONTEXT.json → apis.endpoints[GET /api/v1/seeds]
    """
    logger.info("list_seeds called")
    try:
        return await SeedService.list_seeds()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="seeds directory not found") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="filesystem read error") from exc

from fastapi import UploadFile, File
from app.models.seeds import SeedFile

@router.post(
    "/upload",
    response_model=SeedFile,
    summary="Upload a new seed IR file",
)
async def upload_seed(file: UploadFile = File(...)) -> SeedFile:
    """
    POST /api/v1/seeds/upload
    Receives a multipart/form-data file and writes it to SEED_DIR.
    """
    logger.info("upload_seed called for file: %s", file.filename)
    if not file.filename.endswith(".ll"):
        raise HTTPException(status_code=400, detail="Only .ll files are allowed.")
    
    content = await file.read()
    try:
        return await SeedService.upload_seed(file.filename, content)
    except Exception as exc:
        logger.error("Failed to upload seed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to upload file") from exc
