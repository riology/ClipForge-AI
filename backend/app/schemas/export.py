"""Pydantic schemas for video export and Shorts generation."""

from datetime import datetime
from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Request model for exporting a video clip / Short."""

    clip_index: int | None = Field(default=None, description="1-based index from generated clips")
    start: float | None = Field(default=None, description="Start timestamp in seconds")
    end: float | None = Field(default=None, description="End timestamp in seconds")
    aspect_ratio: str = Field(default="9:16", description="Target aspect ratio: '9:16', 'original', '1:1'")
    layout: str = Field(default="blur_background", description="Layout mode for 9:16: 'blur_background', 'crop', 'fit'")
    burn_subtitles: bool = Field(default=True, description="Whether to burn stylized captions directly into video")
    subtitle_color: str = Field(default="yellow", description="Subtitle color: 'yellow', 'white', 'cyan', 'green'")


class ExportMetadata(BaseModel):
    """Metadata for an exported clip."""

    export_id: str
    video_id: str
    clip_index: int | None = None
    start: float
    end: float
    duration: float
    duration_formatted: str
    aspect_ratio: str
    layout: str
    burn_subtitles: bool
    filename: str
    file_size_bytes: int
    file_size_mb: float
    width: int
    height: int
    created_at: str


class ExportResponse(BaseModel):
    """Response model for export completion."""

    message: str
    export: ExportMetadata
    download_url: str


class ExportListResponse(BaseModel):
    """Response model for listing exports of a video."""

    video_id: str
    total_exports: int
    exports: list[ExportMetadata]
