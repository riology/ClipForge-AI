"""Pydantic schemas for video-related API requests and responses."""

from pydantic import BaseModel


class VideoMetadata(BaseModel):
    """Metadata extracted from a video file via ffprobe."""

    filename: str
    original_filename: str
    file_size_bytes: int
    file_size_mb: float
    duration_seconds: float
    duration_formatted: str
    width: int
    height: int
    codec: str
    fps: float | None = None


class VideoUploadResponse(BaseModel):
    """Response after a successful video upload."""

    message: str
    video_id: str
    metadata: VideoMetadata


class AudioExtractionResponse(BaseModel):
    """Response after audio has been extracted from a video."""

    message: str
    video_id: str
    audio_filename: str
    audio_size_bytes: int
    audio_size_mb: float
    duration_seconds: float


class VideoStatusResponse(BaseModel):
    """Current status of a video and its processing stages."""

    video_id: str
    original_filename: str
    has_video: bool
    has_audio: bool
    metadata: VideoMetadata | None = None
