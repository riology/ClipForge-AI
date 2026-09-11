"""Video export service — cuts video clips and renders 9:16 Shorts with styled captions.

Uses FFmpeg with hardware-independent, high-efficiency encoding.
Supports blurred background padding, center cropping, and customizable subtitle burn-in.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import subprocess
import uuid

from app.core.config import settings
from app.services.subtitle_service import generate_ass_subtitles
from app.services.video_service import (
    FFmpegError,
    _format_duration,
    extract_metadata,
    find_video_path,
)

logger = logging.getLogger("clipforge.export")


def generate_export_id() -> str:
    """Generate a unique export identifier."""
    return uuid.uuid4().hex[:12]


def get_exports_dir() -> Path:
    """Return and ensure the exports storage directory exists."""
    exports_dir = settings.storage_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def find_export_path(export_id: str) -> Path | None:
    """Find the exported MP4 video file for a given export ID."""
    exports_dir = get_exports_dir()
    candidate = exports_dir / f"{export_id}.mp4"
    return candidate if candidate.exists() else None


def get_export_metadata(export_id: str) -> dict | None:
    """Load metadata for a previously exported clip."""
    meta_path = get_exports_dir() / f"{export_id}_meta.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to read export metadata for %s: %s", export_id, e)
        return None


def save_export_metadata(export_id: str, data: dict) -> Path:
    """Save metadata for an exported clip."""
    meta_path = get_exports_dir() / f"{export_id}_meta.json"
    meta_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return meta_path


def list_exports_for_video(video_id: str) -> list[dict]:
    """List all exports created for a given video."""
    exports_dir = get_exports_dir()
    results = []
    for meta_file in sorted(exports_dir.glob("*_meta.json"), reverse=True):
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            if data.get("video_id") == video_id:
                # Verify video file exists
                if (exports_dir / f"{data['export_id']}.mp4").exists():
                    results.append(data)
        except Exception:
            continue
    return results


def export_clip(
    video_path: Path,
    video_id: str,
    start: float,
    end: float,
    clip_index: int | None = None,
    aspect_ratio: str = "9:16",
    layout: str = "blur_background",
    burn_subtitles: bool = True,
    subtitle_color: str = "yellow",
    segments: list[dict] | None = None,
) -> dict:
    """Cut, format, and render an exported video clip or Short.

    Args:
        video_path: Path to source video file.
        video_id: Parent video ID.
        start: Start time in seconds.
        end: End time in seconds.
        clip_index: Optional 1-based index from generated candidates.
        aspect_ratio: Target aspect ratio ('9:16', 'original', '1:1').
        layout: Layout for 9:16 ('blur_background', 'crop', 'fit').
        burn_subtitles: Whether to burn captions into the video.
        subtitle_color: Caption font color ('yellow', 'white', 'cyan', 'green').
        segments: Transcript segments for generating subtitles.

    Returns:
        Dict matching ExportMetadata schema.
    """
    if not video_path.exists():
        raise FFmpegError(f"Source video not found: {video_path}")

    duration = end - start
    if duration <= 0:
        raise FFmpegError(f"Invalid clip duration: start={start}, end={end}")

    export_id = generate_export_id()
    exports_dir = get_exports_dir()
    output_path = exports_dir / f"{export_id}.mp4"

    # Setup subtitle file if requested and segments exist
    ass_filename = None
    if burn_subtitles and segments:
        play_x, play_y = (1080, 1920) if aspect_ratio == "9:16" else ((1080, 1080) if aspect_ratio == "1:1" else (1920, 1080))
        ass_content = generate_ass_subtitles(
            segments=segments,
            clip_start=start,
            clip_end=end,
            play_res_x=play_x,
            play_res_y=play_y,
            color=subtitle_color,
        )
        ass_path = exports_dir / f"{export_id}.ass"
        ass_path.write_text(ass_content, encoding="utf-8")
        ass_filename = f"{export_id}.ass"

    # Construct FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(video_path.resolve()),
    ]

    filter_complex = None
    vf_filter = None

    # Subtitle filter fragment
    sub_filter_chain = f",ass={ass_filename}" if ass_filename else ""

    if aspect_ratio == "9:16":
        out_w, out_h = 1080, 1920
        if layout == "blur_background":
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                f"[0:v]scale=1080:-2:flags=lanczos[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2{sub_filter_chain}[v]"
            )
        elif layout == "crop":
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920{sub_filter_chain}[v]"
            )
        elif layout == "fit":
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(1080-iw)/2:(1920-ih)/2:black{sub_filter_chain}[v]"
            )
        else:
            raise FFmpegError(f"Unsupported layout '{layout}' for 9:16")

    elif aspect_ratio == "1:1":
        out_w, out_h = 1080, 1080
        filter_complex = (
            f"[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080{sub_filter_chain}[v]"
        )

    elif aspect_ratio == "original":
        out_w, out_h = 0, 0  # Will be extracted from ffprobe
        if ass_filename:
            vf_filter = f"ass={ass_filename}"
    else:
        raise FFmpegError(f"Unsupported aspect ratio '{aspect_ratio}'")

    if filter_complex:
        cmd.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "0:a?"])
    elif vf_filter:
        cmd.extend(["-vf", vf_filter, "-map", "0:v", "-map", "0:a?"])
    else:
        cmd.extend(["-map", "0:v", "-map", "0:a?"])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path.resolve()),
    ])

    logger.info(
        "Exporting clip %s: [%.1fs - %.1fs] ratio=%s layout=%s subs=%s",
        export_id, start, end, aspect_ratio, layout, bool(ass_filename),
    )

    try:
        # Run FFmpeg in the exports directory so relative ass=filename works without path escaping bugs
        result = subprocess.run(
            cmd,
            cwd=str(exports_dir.resolve()),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        raise FFmpegError("FFmpeg is not installed or not on PATH.")
    except subprocess.TimeoutExpired:
        raise FFmpegError("FFmpeg export timed out (exceeded 5 minutes).")

    if result.returncode != 0:
        logger.error("FFmpeg export failed: %s", result.stderr)
        raise FFmpegError(f"FFmpeg export failed: {result.stderr.strip()[-500:]}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise FFmpegError("Export finished but output file is missing or empty.")

    # Probe exported file for accurate size, duration, width, height
    file_size = output_path.stat().st_size
    meta = extract_metadata(output_path)

    metadata = {
        "export_id": export_id,
        "video_id": video_id,
        "clip_index": clip_index,
        "start": round(start, 2),
        "end": round(end, 2),
        "duration": round(duration, 2),
        "duration_formatted": _format_duration(duration),
        "aspect_ratio": aspect_ratio,
        "layout": layout if aspect_ratio == "9:16" else aspect_ratio,
        "burn_subtitles": bool(ass_filename),
        "filename": output_path.name,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "width": meta.get("width", 1080),
        "height": meta.get("height", 1920),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    save_export_metadata(export_id, metadata)
    logger.info("Export completed successfully: %s", output_path.name)
    return metadata
