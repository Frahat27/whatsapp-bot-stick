"""
Endpoint de health check.
Verifica conectividad con PostgreSQL.
"""

from fastapi import APIRouter

from src.config import get_settings
from src.schemas.message import HealthResponse
from src.utils.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check — verifica que la app y la DB estén operativas.
    """
    settings = get_settings()
    db_status = "not_configured"

    if settings.database_url:
        try:
            from sqlalchemy import text
            from src.db.session import get_engine

            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            logger.error("health_check_db_error", error=str(e))
            db_status = f"error: {str(e)[:100]}"

    return HealthResponse(
        status="ok",
        environment=settings.environment,
        database=db_status,
    )
