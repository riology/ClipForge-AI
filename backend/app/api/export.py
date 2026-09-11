"""Video export and Shorts generation API endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.export import (
    ExportListResponse,
    ExportMetadata,
    ExportRequest,
    ExportResponse,
)
from app.services.clip_engine.engine import load_clips
from app.services.export_service import (
    export_clip,
    find_export_path,
    get_export_metadata,
    list_exports_for_video,
)
from app.services.transcription_service import load_transcript
from app.services.video_service import FFmpegError, find_video_path

logger = logging.getLogger("clipforge.api.export")

router = APIRouter(prefix="/export", tags=["export"])


# ---------------------------------------------------------------------------
# POST /api/export/{video_id}
# ---------------------------------------------------------------------------
@router.post("/{video_id}", response_model=ExportResponse)
async def create_export(video_id: str, request: ExportRequest | None = None):
    """Cut and export a video clip as a high-quality vertical Short.

    Specify either:
      - `clip_index`: 1-based index of a generated candidate clip
      - OR explicit `start` and `end` timestamps in seconds

    Customization options:
      - `aspect_ratio`: '9:16' (Shorts/Reels/TikTok), 'original', '1:1'
      - `layout`: 'blur_background' (recommended), 'crop', 'fit'
      - `burn_subtitles`: True/False (renders bold captions in platform safe-zone)
      - `subtitle_color`: 'yellow', 'white', 'cyan', 'green'
    """
    req = request or ExportRequest()

    # Locate source video
    video_path = find_video_path(video_id)
    if video_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found. Please upload a video first.",
        )

    # Determine start and end
    start = req.start
    end = req.end
    clip_index = req.clip_index

    if clip_index is not None:
        saved_clips = load_clips(video_id)
        if not saved_clips:
            raise HTTPException(
                status_code=404,
                detail=f"No generated clips found for video '{video_id}'. Please generate clips first.",
            )
        target = next((c for c in saved_clips if c.get("clip_index") == clip_index), None)
        if target is None:
            raise HTTPException(
                status_code=404,
                detail=f"Clip index {clip_index} not found. Available indices: 1 to {len(saved_clips)}.",
            )
        start = target["start"]
        end = target["end"]

    if start is None or end is None:
        raise HTTPException(
            status_code=400,
            detail="Must specify either 'clip_index' or both 'start' and 'end' timestamps.",
        )

    if end <= start:
        raise HTTPException(
            status_code=400,
            detail=f"End time ({end}s) must be strictly greater than start time ({start}s).",
        )

    # Load transcript segments if burning subtitles
    segments = None
    if req.burn_subtitles:
        transcript = load_transcript(video_id)
        if transcript and "segments" in transcript:
            segments = transcript["segments"]

    # Execute export
    try:
        meta = export_clip(
            video_path=video_path,
            video_id=video_id,
            start=start,
            end=end,
            clip_index=clip_index,
            aspect_ratio=req.aspect_ratio,
            layout=req.layout,
            burn_subtitles=req.burn_subtitles,
            subtitle_color=req.subtitle_color,
            segments=segments,
        )
    except FFmpegError as e:
        logger.error("Export failed for video %s: %s", video_id, e)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during export for video %s", video_id)
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    export_id = meta["export_id"]
    return ExportResponse(
        message=f"Short exported successfully as {meta['filename']}.",
        export=ExportMetadata(**meta),
        download_url=f"/api/export/{export_id}/download",
    )


# ---------------------------------------------------------------------------
# GET /api/export/{export_id}
# ---------------------------------------------------------------------------
@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(export_id: str):
    """Retrieve metadata for an exported clip."""
    meta = get_export_metadata(export_id)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Export '{export_id}' not found.",
        )

    return ExportResponse(
        message="Export metadata retrieved.",
        export=ExportMetadata(**meta),
        download_url=f"/api/export/{export_id}/download",
    )


# ---------------------------------------------------------------------------
# GET /api/export/{export_id}/download
# ---------------------------------------------------------------------------
@router.get("/{export_id}/download")
async def download_export(export_id: str):
    """Download the exported video file directly."""
    video_file = find_export_path(export_id)
    if video_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Exported video file for ID '{export_id}' not found.",
        )

    return FileResponse(
        path=str(video_file),
        media_type="video/mp4",
        filename=video_file.name,
    )


# ---------------------------------------------------------------------------
# GET /api/export/list/{video_id}
# ---------------------------------------------------------------------------
@router.get("/list/{video_id}", response_model=ExportListResponse)
async def list_exports(video_id: str):
    """List all exported clips created for a specific video."""
    exports = list_exports_for_video(video_id)
    return ExportListResponse(
        video_id=video_id,
        total_exports=len(exports),
        exports=[ExportMetadata(**e) for e in exports],
    )
