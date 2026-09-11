"""Video processing service — validation, metadata, and audio extraction.

Uses FFmpeg/ffprobe for all media operations. No paid APIs required.
"""

import json
import logging
import subprocess
import uuid
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("clipforge.video")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm"}
ALLOWED_MIME_PREFIXES = {"video/"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class VideoValidationError(Exception):
    """Raised when a video file fails validation."""


class FFmpegError(Exception):
    """Raised when an FFmpeg/ffprobe operation fails."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_video_file(filename: str, file_size: int) -> None:
    """Validate that the uploaded file is an acceptable video.

    Raises VideoValidationError with a human-readable message on failure.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise VideoValidationError(
            f"Unsupported file format '{ext}'. Allowed formats: {allowed}"
        )

    if file_size <= 0:
        raise VideoValidationError("Uploaded file is empty.")

    if file_size > MAX_FILE_SIZE_BYTES:
        max_gb = MAX_FILE_SIZE_BYTES / (1024 ** 3)
        raise VideoValidationError(
            f"File is too large. Maximum allowed size is {max_gb:.0f} GB."
        )


# ---------------------------------------------------------------------------
# File storage helpers
# ---------------------------------------------------------------------------
def generate_video_id() -> str:
    """Generate a unique ID for a video project."""
    return uuid.uuid4().hex[:12]


def get_upload_path(video_id: str, original_filename: str) -> Path:
    """Return the storage path for an uploaded video."""
    ext = Path(original_filename).suffix.lower()
    upload_dir = settings.storage_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir / f"{video_id}{ext}"


async def save_upload(video_id: str, original_filename: str, file_content: bytes) -> Path:
    """Save uploaded file bytes to the storage directory.

    Returns the path to the saved file.
    """
    dest = get_upload_path(video_id, original_filename)
    dest.write_bytes(file_content)
    logger.info("Saved upload: %s (%d bytes)", dest.name, len(file_content))
    return dest


# ---------------------------------------------------------------------------
# Metadata extraction  (ffprobe)
# ---------------------------------------------------------------------------
def _format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def extract_metadata(video_path: Path) -> dict:
    """Extract video metadata using ffprobe.

    Returns a dict with keys matching the VideoMetadata schema.
    Raises FFmpegError if ffprobe fails.
    """
    if not video_path.exists():
        raise FFmpegError(f"Video file not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise FFmpegError(
            "FFmpeg/ffprobe is not installed or not on PATH. "
            "Please install FFmpeg: https://ffmpeg.org/download.html"
        )
    except subprocess.TimeoutExpired:
        raise FFmpegError("ffprobe timed out while reading video metadata.")

    if result.returncode != 0:
        raise FFmpegError(f"ffprobe failed: {result.stderr.strip()}")

    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise FFmpegError("ffprobe returned invalid JSON output.")

    # Find the video stream
    video_stream = None
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    if video_stream is None:
        raise FFmpegError("No video stream found in the file.")

    # Extract values
    duration = float(probe.get("format", {}).get("duration", 0))
    file_size = video_path.stat().st_size
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    codec = video_stream.get("codec_name", "unknown")

    # Parse FPS from r_frame_rate (e.g. "30000/1001")
    fps = None
    r_frame_rate = video_stream.get("r_frame_rate", "")
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        if int(den) > 0:
            fps = round(int(num) / int(den), 2)

    return {
        "filename": video_path.name,
        "original_filename": video_path.name,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "duration_seconds": round(duration, 2),
        "duration_formatted": _format_duration(duration),
        "width": width,
        "height": height,
        "codec": codec,
        "fps": fps,
    }


# ---------------------------------------------------------------------------
# Audio extraction  (ffmpeg)
# ---------------------------------------------------------------------------
def extract_audio(video_path: Path, video_id: str) -> dict:
    """Extract audio from a video file as 16 kHz mono WAV (optimal for Whisper).

    Returns a dict with audio file info.
    Raises FFmpegError if the extraction fails.
    """
    if not video_path.exists():
        raise FFmpegError(f"Video file not found: {video_path}")

    audio_dir = settings.storage_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{video_id}.wav"

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",                    # No video
        "-acodec", "pcm_s16le",   # 16-bit PCM
        "-ar", "16000",           # 16 kHz sample rate (Whisper optimal)
        "-ac", "1",               # Mono
        "-y",                     # Overwrite if exists
        str(audio_path),
    ]

    logger.info("Extracting audio: %s → %s", video_path.name, audio_path.name)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for long videos
        )
    except FileNotFoundError:
        raise FFmpegError(
            "FFmpeg is not installed or not on PATH. "
            "Please install FFmpeg: https://ffmpeg.org/download.html"
        )
    except subprocess.TimeoutExpired:
        raise FFmpegError("Audio extraction timed out (exceeded 10 minutes).")

    if result.returncode != 0:
        raise FFmpegError(f"FFmpeg audio extraction failed: {result.stderr.strip()}")

    if not audio_path.exists():
        raise FFmpegError("Audio file was not created by FFmpeg.")

    audio_size = audio_path.stat().st_size
    if audio_size == 0:
        audio_path.unlink()
        raise FFmpegError("FFmpeg produced an empty audio file. The video may have no audio track.")

    # Get audio duration via ffprobe
    duration = 0.0
    try:
        dur_cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-print_format", "json",
            str(audio_path),
        ]
        dur_result = subprocess.run(dur_cmd, capture_output=True, text=True, timeout=10)
        if dur_result.returncode == 0:
            dur_data = json.loads(dur_result.stdout)
            duration = float(dur_data.get("format", {}).get("duration", 0))
    except Exception:
        logger.warning("Could not determine audio duration, defaulting to 0.")

    logger.info(
        "Audio extracted: %s (%.1f MB, %.1f sec)",
        audio_path.name,
        audio_size / (1024 * 1024),
        duration,
    )

    return {
        "audio_filename": audio_path.name,
        "audio_path": str(audio_path),
        "audio_size_bytes": audio_size,
        "audio_size_mb": round(audio_size / (1024 * 1024), 2),
        "duration_seconds": round(duration, 2),
    }


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------
def find_video_path(video_id: str) -> Path | None:
    """Find the uploaded video file for a given video ID."""
    upload_dir = settings.storage_path / "uploads"
    if not upload_dir.exists():
        return None
    for ext in ALLOWED_EXTENSIONS:
        candidate = upload_dir / f"{video_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def find_audio_path(video_id: str) -> Path | None:
    """Find the extracted audio file for a given video ID."""
    audio_path = settings.storage_path / "audio" / f"{video_id}.wav"
    return audio_path if audio_path.exists() else None
