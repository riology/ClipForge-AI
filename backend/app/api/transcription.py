"""Transcription API endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.transcription import (
    TranscriptionRequest,
    TranscriptionResponse,
    TranscriptionResult,
    TranscriptionStatusResponse,
    TranscriptSegment,
)
from app.services.transcription_service import (
    TranscriptionError,
    has_transcript,
    load_transcript,
    save_transcript,
    transcribe_audio,
)
from app.services.video_service import find_audio_path

logger = logging.getLogger("clipforge.api.transcription")

router = APIRouter(prefix="/transcription", tags=["transcription"])


# ---------------------------------------------------------------------------
# POST /api/transcription/{video_id}/transcribe
# ---------------------------------------------------------------------------
@router.post("/{video_id}/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(video_id: str, request: TranscriptionRequest | None = None):
    """Transcribe the audio of an uploaded video.

    The video must have had its audio extracted first
    (via POST /api/videos/{id}/extract-audio).

    Returns timestamped transcript segments.
    """
    # Check for existing transcript
    existing = load_transcript(video_id)
    if existing is not None:
        logger.info("Returning cached transcript for %s", video_id)
        return TranscriptionResponse(
            message="Transcription already exists (returning cached result).",
            result=TranscriptionResult(
                video_id=video_id,
                **existing,
            ),
        )

    # Find audio file
    audio_path = find_audio_path(video_id)
    if audio_path is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No audio found for video '{video_id}'. "
                "Please extract audio first using POST /api/videos/{video_id}/extract-audio"
            ),
        )

    # Transcribe
    language = None
    if request and request.language:
        language = request.language

    try:
        result = transcribe_audio(audio_path, language=language)
    except TranscriptionError as e:
        logger.error("Transcription failed for %s: %s", video_id, e)
        raise HTTPException(status_code=422, detail=str(e))

    # Save transcript
    try:
        save_transcript(video_id, result)
    except Exception as e:
        logger.error("Failed to save transcript for %s: %s", video_id, e)
        # Continue anyway — the transcription succeeded

    return TranscriptionResponse(
        message="Transcription completed successfully.",
        result=TranscriptionResult(
            video_id=video_id,
            **result,
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/transcription/{video_id}
# ---------------------------------------------------------------------------
@router.get("/{video_id}", response_model=TranscriptionResponse)
async def get_transcription(video_id: str):
    """Retrieve a previously generated transcription."""
    transcript = load_transcript(video_id)
    if transcript is None:
        raise HTTPException(
            status_code=404,
            detail=f"No transcription found for video '{video_id}'.",
        )

    return TranscriptionResponse(
        message="Transcription retrieved.",
        result=TranscriptionResult(
            video_id=video_id,
            **transcript,
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/transcription/{video_id}/status
# ---------------------------------------------------------------------------
@router.get("/{video_id}/status", response_model=TranscriptionStatusResponse)
async def get_transcription_status(video_id: str):
    """Check whether a transcription exists for a video."""
    transcript = load_transcript(video_id)

    return TranscriptionStatusResponse(
        video_id=video_id,
        has_transcription=transcript is not None,
        segment_count=transcript["segment_count"] if transcript else None,
        language=transcript["language"] if transcript else None,
    )
