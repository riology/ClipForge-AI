"""Video upload, metadata, and audio extraction API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.schemas.video import (
    AudioExtractionResponse,
    VideoMetadata,
    VideoStatusResponse,
    VideoUploadResponse,
)
from app.services.video_service import (
    FFmpegError,
    VideoValidationError,
    extract_audio,
    extract_metadata,
    find_audio_path,
    find_video_path,
    generate_video_id,
    save_upload,
    validate_video_file,
)

logger = logging.getLogger("clipforge.api.videos")

router = APIRouter(prefix="/videos", tags=["videos"])


# ---------------------------------------------------------------------------
# POST /api/videos/upload
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file for processing.

    Accepts MP4, MKV, MOV, and WEBM files up to 5 GB.
    Returns the assigned video ID and extracted metadata.
    """
    # Read file content
    content = await file.read()
    original_filename = file.filename or "unknown_video"

    # Validate
    try:
        validate_video_file(original_filename, len(content))
    except VideoValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save
    video_id = generate_video_id()
    try:
        video_path = await save_upload(video_id, original_filename, content)
    except Exception as e:
        logger.error("Failed to save upload: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    # Extract metadata
    try:
        meta = extract_metadata(video_path)
        meta["original_filename"] = original_filename
    except FFmpegError as e:
        logger.error("Metadata extraction failed: %s", e)
        raise HTTPException(status_code=422, detail=str(e))

    logger.info(
        "Video uploaded: %s → %s (%.1f MB, %s)",
        original_filename,
        video_id,
        meta["file_size_mb"],
        meta["duration_formatted"],
    )

    return VideoUploadResponse(
        message="Video uploaded successfully.",
        video_id=video_id,
        metadata=VideoMetadata(**meta),
    )


# ---------------------------------------------------------------------------
# GET /api/videos/{video_id}/metadata
# ---------------------------------------------------------------------------
@router.get("/{video_id}/metadata", response_model=VideoMetadata)
async def get_video_metadata(video_id: str):
    """Get metadata for a previously uploaded video."""
    video_path = find_video_path(video_id)
    if video_path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found.")

    try:
        meta = extract_metadata(video_path)
    except FFmpegError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return VideoMetadata(**meta)


# ---------------------------------------------------------------------------
# POST /api/videos/{video_id}/extract-audio
# ---------------------------------------------------------------------------
@router.post("/{video_id}/extract-audio", response_model=AudioExtractionResponse)
async def extract_video_audio(video_id: str):
    """Extract the audio track from an uploaded video.

    Produces a 16 kHz mono WAV file optimised for speech transcription.
    """
    video_path = find_video_path(video_id)
    if video_path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found.")

    try:
        result = extract_audio(video_path, video_id)
    except FFmpegError as e:
        logger.error("Audio extraction failed for %s: %s", video_id, e)
        raise HTTPException(status_code=422, detail=str(e))

    return AudioExtractionResponse(
        message="Audio extracted successfully.",
        video_id=video_id,
        audio_filename=result["audio_filename"],
        audio_size_bytes=result["audio_size_bytes"],
        audio_size_mb=result["audio_size_mb"],
        duration_seconds=result["duration_seconds"],
    )


# ---------------------------------------------------------------------------
# GET /api/videos/{video_id}/status
# ---------------------------------------------------------------------------
@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """Check the current processing status of a video."""
    video_path = find_video_path(video_id)
    audio_path = find_audio_path(video_id)

    if video_path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found.")

    meta = None
    try:
        meta_dict = extract_metadata(video_path)
        meta = VideoMetadata(**meta_dict)
    except FFmpegError:
        pass

    return VideoStatusResponse(
        video_id=video_id,
        original_filename=video_path.name,
        has_video=True,
        has_audio=audio_path is not None,
        metadata=meta,
    )
