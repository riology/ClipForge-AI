"""Subtitle generation service — creates styled ASS and standard SRT files.

Provides high-impact, modern subtitle formatting for vertical video (Shorts/Reels/TikTok):
- Large bold typography
- High-contrast colors (yellow/white) with thick dark outlines
- Positioned in the vertical safe zone (above platform UI overlays)
"""

from pathlib import Path
import re


def _format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp format: H:MM:SS.cs"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _format_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp format: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


COLOR_PALETTES = {
    "yellow": "&H0000FFFF",   # B=00, G=FF, R=FF
    "white": "&H00FFFFFF",    # B=FF, G=FF, R=FF
    "cyan": "&H00FFFF00",     # B=FF, G=FF, R=00
    "green": "&H0000FF55",    # Neon green
}


def filter_clip_segments(
    segments: list[dict],
    clip_start: float,
    clip_end: float,
) -> list[dict]:
    """Filter segments falling within [clip_start, clip_end] and shift timestamps to 0-based."""
    filtered = []
    clip_duration = clip_end - clip_start

    for seg in segments:
        s_start = seg.get("start", 0.0)
        s_end = seg.get("end", 0.0)
        text = seg.get("text", "").strip()

        # Check if segment overlaps with the clip window
        if s_end <= clip_start or s_start >= clip_end:
            continue
        if not text:
            continue

        # Shift relative to clip start
        rel_start = max(0.0, s_start - clip_start)
        rel_end = min(clip_duration, s_end - clip_start)

        if rel_end > rel_start:
            filtered.append({
                "start": round(rel_start, 2),
                "end": round(rel_end, 2),
                "text": text,
            })

    return filtered


def generate_ass_subtitles(
    segments: list[dict],
    clip_start: float,
    clip_end: float,
    play_res_x: int = 1080,
    play_res_y: int = 1920,
    color: str = "yellow",
    font_size: int = 58,
    margin_v: int = 340,
) -> str:
    """Generate an Advanced SubStation Alpha (.ass) subtitle file content.

    Tailored specifically for 9:16 vertical short-form videos with bold,
    easily-readable, high-contrast captions placed in the platform safe zone.
    """
    primary_color = COLOR_PALETTES.get(color.lower(), COLOR_PALETTES["yellow"])
    outline_color = "&H00000000"  # Solid black outline
    shadow_color = "&H80000000"   # Semi-transparent black shadow

    header = f"""[Script Info]
Title: ClipForge AI Captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {play_res_x}
PlayResY: {play_res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{primary_color},&H000000FF,{outline_color},{shadow_color},-1,0,0,0,100,100,0,0,1,4.5,2.0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogues = []
    rel_segments = filter_clip_segments(segments, clip_start, clip_end)

    for seg in rel_segments:
        start_str = _format_ass_time(seg["start"])
        end_str = _format_ass_time(seg["end"])
        text = seg["text"].strip().upper()

        # Word wrap text if too long (more than ~30 characters per line)
        words = text.split()
        if len(words) > 5 and len(text) > 28:
            mid = len(words) // 2
            text = " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])

        dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")

    return header + "\n".join(dialogues) + "\n"


def generate_srt_subtitles(
    segments: list[dict],
    clip_start: float,
    clip_end: float,
) -> str:
    """Generate standard SRT subtitle format content."""
    rel_segments = filter_clip_segments(segments, clip_start, clip_end)
    entries = []

    for i, seg in enumerate(rel_segments, start=1):
        start_str = _format_srt_time(seg["start"])
        end_str = _format_srt_time(seg["end"])
        text = seg["text"].strip()
        entries.append(f"{i}\n{start_str} --> {end_str}\n{text}\n")

    return "\n".join(entries)
