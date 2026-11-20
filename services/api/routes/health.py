"""Health and readiness check endpoints."""

from fastapi import APIRouter, Depends
from services.api.dependencies import get_gateway, get_repository
from services.model_gateway.registry import ModelRegistry
from services.memory.repository import MemoryRepository
from services.api.config import settings
from datetime import datetime

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check(
    gateway: ModelRegistry = Depends(get_gateway),
    repo: MemoryRepository = Depends(get_repository),
):
    """System health, provider readiness, and offline status report."""
    db_healthy = True
    try:
        # Simple ping to test DB connection
        await repo.get_setting("health_check_ping", default="ok")
    except Exception:
        db_healthy = False

    model_health = await gateway.check_health()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": "connected" if db_healthy else "disconnected",
            "path": settings.db_path,
        },
        "model_runtime": model_health,
        "offline_ready": True,
    }
