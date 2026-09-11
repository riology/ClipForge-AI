"""Pydantic schemas for transcription-related API requests and responses."""

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """A single segment of the transcription with timestamps."""

    start: float
    end: float
    text: str


class TranscriptionRequest(BaseModel):
    """Optional parameters for transcription."""

    language: str | None = None  # Auto-detect if None
    model: str | None = None  # Override default model


class TranscriptionResult(BaseModel):
    """Full transcription result with metadata."""

    video_id: str
    language: str
    language_probability: float
    duration_seconds: float
    segment_count: int
    segments: list[TranscriptSegment]
    full_text: str


class TranscriptionResponse(BaseModel):
    """API response wrapper for transcription."""

    message: str
    result: TranscriptionResult


class TranscriptionStatusResponse(BaseModel):
    """Check whether a transcription exists for a video."""

    video_id: str
    has_transcription: bool
    segment_count: int | None = None
    language: str | None = None
