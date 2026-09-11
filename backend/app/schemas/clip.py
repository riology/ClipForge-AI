"""Pydantic schemas for clip-related API responses."""

from pydantic import BaseModel


class ClipScores(BaseModel):
    """Individual scoring dimensions for a clip."""

    hook: int
    information: int
    emotion: int
    context: int
    completeness: int
    pacing: int


class ClipCandidate(BaseModel):
    """A single clip candidate with scores and metadata."""

    clip_index: int
    start: float
    end: float
    duration: float
    start_formatted: str
    end_formatted: str
    text: str
    clip_quality_score: int
    scores: ClipScores
    reasons: list[str]
    segment_count: int


class ClipGenerationResponse(BaseModel):
    """Response from clip generation."""

    message: str
    video_id: str
    clip_count: int
    clips: list[ClipCandidate]


class ClipGenerationRequest(BaseModel):
    """Optional parameters for clip generation."""

    max_clips: int | None = None
    regenerate: bool = False  # Force regeneration even if cached
