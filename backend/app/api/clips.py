"""Clip intelligence API endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.clip import (
    ClipCandidate,
    ClipGenerationRequest,
    ClipGenerationResponse,
)
from app.services.clip_engine.engine import (
    analyze_transcript,
    load_clips,
    save_clips,
)
from app.services.transcription_service import load_transcript

logger = logging.getLogger("clipforge.api.clips")

router = APIRouter(prefix="/clips", tags=["clips"])


# ---------------------------------------------------------------------------
# POST /api/clips/{video_id}/generate
# ---------------------------------------------------------------------------
@router.post("/{video_id}/generate", response_model=ClipGenerationResponse)
async def generate_clips(
    video_id: str,
    request: ClipGenerationRequest | None = None,
):
    """Generate top clip candidates from a video's transcription.

    The video must have been transcribed first
    (via POST /api/transcription/{video_id}/transcribe).

    Pipeline:
      1. Load transcript segments
      2. Generate 15-90s candidate clips with natural boundaries
      3. Score each clip across 6 dimensions (Hook, Info, Emotion, Context, Completeness, Pacing)
      4. Filter out duplicate / highly overlapping clips
      5. Rank and return the top clips with explainable reasons
    """
    regenerate = request.regenerate if request else False
    max_clips = request.max_clips if request else None

    # Check for cached clips if regeneration not requested
    if not regenerate:
        existing = load_clips(video_id)
        if existing is not None:
            logger.info("Returning %d cached clips for %s", len(existing), video_id)
            return ClipGenerationResponse(
                message="Clips already generated (returning cached result).",
                video_id=video_id,
                clip_count=len(existing),
                clips=[ClipCandidate(**c) for c in existing],
            )

    # Load transcript
    transcript = load_transcript(video_id)
    if transcript is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No transcription found for video '{video_id}'. "
                "Please transcribe the video first using POST /api/transcription/{video_id}/transcribe"
            ),
        )

    segments = transcript.get("segments", [])
    if not segments:
        raise HTTPException(
            status_code=422,
            detail=f"Transcription for video '{video_id}' contains no speech segments.",
        )

    # Run clip intelligence engine
    try:
        clips = analyze_transcript(segments, max_clips=max_clips)
    except Exception as e:
        logger.error("Clip generation failed for %s: %s", video_id, e)
        raise HTTPException(status_code=500, detail=f"Clip generation failed: {e}")

    # Save generated clips
    try:
        save_clips(video_id, clips)
    except Exception as e:
        logger.error("Failed to save clips for %s: %s", video_id, e)

    return ClipGenerationResponse(
        message=f"Successfully generated {len(clips)} clip candidates.",
        video_id=video_id,
        clip_count=len(clips),
        clips=[ClipCandidate(**c) for c in clips],
    )


# ---------------------------------------------------------------------------
# GET /api/clips/{video_id}
# ---------------------------------------------------------------------------
@router.get("/{video_id}", response_model=ClipGenerationResponse)
async def get_clips(video_id: str):
    """Retrieve previously generated clips for a video."""
    clips = load_clips(video_id)
    if clips is None:
        raise HTTPException(
            status_code=404,
            detail=f"No generated clips found for video '{video_id}'.",
        )

    return ClipGenerationResponse(
        message=f"Retrieved {len(clips)} clips.",
        video_id=video_id,
        clip_count=len(clips),
        clips=[ClipCandidate(**c) for c in clips],
    )


# ---------------------------------------------------------------------------
# GET /api/clips/{video_id}/{clip_index}
# ---------------------------------------------------------------------------
@router.get("/{video_id}/{clip_index}", response_model=ClipCandidate)
async def get_single_clip(video_id: str, clip_index: int):
    """Retrieve a specific clip candidate by 1-based index."""
    clips = load_clips(video_id)
    if clips is None:
        raise HTTPException(
            status_code=404,
            detail=f"No generated clips found for video '{video_id}'.",
        )

    for clip in clips:
        if clip.get("clip_index") == clip_index:
            return ClipCandidate(**clip)

    raise HTTPException(
        status_code=404,
        detail=f"Clip index {clip_index} not found for video '{video_id}'. Available: 1 to {len(clips)}.",
    )
