from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from src.config import get_settings
from src.db.session import get_engine
from src.models.schemas import CamelModel

router = APIRouter(tags=["Health"])


class HealthResponse(CamelModel):
    status: str
    app_name: str
    app_env: str
    database: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    db_status = "ok"

    if not settings.use_in_memory_repos:
        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {e}"
    else:
        db_status = "in-memory (no-db)"

    return HealthResponse(
        status="ok" if "error" not in db_status else "degraded",
        app_name=settings.app_name,
        app_env=settings.app_env,
        database=db_status,
    )
