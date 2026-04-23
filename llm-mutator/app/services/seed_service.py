"""
app/services/seed_service.py
Service layer for seeds.
Source: CONTEXT.json → architecture.components  (seeds are filesystem inputs;
        no dedicated component, but data_flow step 1 describes them)
        CONTEXT.json → apis.endpoints[GET /api/v1/seeds]
        CONTEXT.json → setup.environment_variables[SEED_DIR]
"""
import datetime
from app.config import SEED_DIR
from app.models.seeds import SeedFile, SeedListResponse


class SeedService:
    """
    Handles access to seed IR files stored in SEED_DIR.

    TODO (Phase 2): add upload_seed() to accept multipart file uploads,
    matching the optional UploadButton in CONTEXT.json ui.screens[Seed IR List].
    """

    @staticmethod
    async def list_seeds() -> SeedListResponse:
        """
        Scan SEED_DIR for .ll files and return metadata for each.
        Raises FileNotFoundError if SEED_DIR does not exist.
        Raises OSError on filesystem read failure.
        """
        if not SEED_DIR.exists():
            raise FileNotFoundError(f"SEED_DIR not found: {SEED_DIR}")

        seeds: list[SeedFile] = []
        for f in sorted(SEED_DIR.glob("*.ll")):
            stat = f.stat()
            seeds.append(
                SeedFile(
                    name=f.name,
                    path=str(f.resolve()),
                    size_bytes=float(stat.st_size),
                    created_at=datetime.datetime.fromtimestamp(
                        stat.st_ctime, tz=datetime.timezone.utc
                    ).isoformat(),
                )
            )

        return SeedListResponse(seeds=seeds)

    @staticmethod
    async def upload_seed(filename: str, content: bytes) -> SeedFile:
        """
        Saves a newly uploaded seed .ll file into SEED_DIR.
        """
        if not SEED_DIR.exists():
            SEED_DIR.mkdir(parents=True, exist_ok=True)
            
        file_path = SEED_DIR / filename
        with open(file_path, "wb") as f:
            f.write(content)
            
        stat = file_path.stat()
        return SeedFile(
            name=filename,
            path=str(file_path.resolve()),
            size_bytes=float(stat.st_size),
            created_at=datetime.datetime.fromtimestamp(
                stat.st_ctime, tz=datetime.timezone.utc
            ).isoformat(),
        )
