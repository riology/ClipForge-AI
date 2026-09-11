"""ClipForge AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.health import router as health_router
from app.api.videos import router as videos_router
from app.api.transcription import router as transcription_router
from app.api.clips import router as clips_router
from app.api.export import router as export_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("clipforge")


# ---------------------------------------------------------------------------
# Lifespan — runs on startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # --- Startup ---
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Ensure storage directories exist
    for subdir in ("uploads", "audio", "transcripts", "clips", "exports"):
        (settings.storage_path / subdir).mkdir(parents=True, exist_ok=True)
    logger.info("Storage directory: %s", settings.storage_path)

    yield

    # --- Shutdown ---
    logger.info("Shutting down %s", settings.APP_NAME)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Turn long-form videos into short-form content using local AI.",
    lifespan=lifespan,
)

from fastapi.staticfiles import StaticFiles

# CORS — allow the web frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve storage files (uploads, exports) for in-browser video previews
app.mount("/storage", StaticFiles(directory=str(settings.storage_path)), name="storage")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health_router, prefix="/api")
app.include_router(videos_router, prefix="/api")
app.include_router(transcription_router, prefix="/api")
app.include_router(clips_router, prefix="/api")
app.include_router(export_router, prefix="/api")
