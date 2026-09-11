"""ClipForge AI — Core configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root is two levels up from this file (backend/app/core/config.py → project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "ClipForge AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # --- Server ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # --- Storage ---
    STORAGE_DIR: str = "./storage"

    # --- Whisper (Phase 3) ---
    WHISPER_MODEL: str = "base"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_DEVICE: str = "cpu"

    # --- Clip Generation (Phase 4) ---
    MIN_CLIP_DURATION: int = 15
    PREFERRED_CLIP_DURATION_MIN: int = 30
    PREFERRED_CLIP_DURATION_MAX: int = 60
    MAX_CLIP_DURATION: int = 90
    MAX_CLIPS_RETURNED: int = 10

    @property
    def storage_path(self) -> Path:
        """Resolve storage directory to an absolute path."""
        p = Path(self.STORAGE_DIR)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p.resolve()


# Singleton instance — import this throughout the app
settings = Settings()
