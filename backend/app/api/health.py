"""ClipForge AI — Health check endpoint."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check():
    """Return application health status.

    Used to verify the backend is running and responsive.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
