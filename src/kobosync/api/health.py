from fastapi import APIRouter
from sqlmodel import Session, text

from ..database import engine
from ..logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check() -> dict[str, str | bool]:
    db_ok = False

    try:
        with Session(engine) as session:
            session.connection().execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning("Database health check failed", error=str(e))

    return {
        "status": "ready" if db_ok else "degraded",
        "database": db_ok,
    }
