"""Clip Intelligence Engine — main orchestrator.

Pipeline:
  Transcript segments
  → Generate candidates (sliding window)
  → Score each candidate (6 dimensions)
  → Sort by Clip Quality Score
  → Remove duplicates
  → Return top N clips
"""

import json
import logging
from pathlib import Path

from app.core.config import settings
from app.services.clip_engine.candidate_generator import generate_candidates
from app.services.clip_engine.duplicate_detector import remove_duplicates
from app.services.clip_engine.scoring.final_score import score_clip
from app.services.clip_engine.text_cleaner import clean_text

logger = logging.getLogger("clipforge.clip_engine")


class ClipEngineError(Exception):
    """Raised when clip generation fails."""


def _format_time(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def analyze_transcript(segments: list[dict], max_clips: int | None = None) -> list[dict]:
    """Run the full clip intelligence pipeline on transcript segments.

    Args:
        segments: List of transcript segments with 'start', 'end', 'text'.
        max_clips: Maximum clips to return (default from settings).

    Returns:
        List of clip dicts, sorted by clip_quality_score descending.
        Each clip contains:
          - clip_index: int
          - start / end / duration
          - start_formatted / end_formatted
          - text: cleaned combined text
          - clip_quality_score: 0-100
          - scores: {hook, information, emotion, context, completeness, pacing}
          - reasons: list of explanation strings
          - segment_count: number of transcript segments
    """
    if max_clips is None:
        max_clips = settings.MAX_CLIPS_RETURNED

    if not segments:
        logger.warning("No segments provided for clip analysis")
        return []

    logger.info("Starting clip analysis on %d segments", len(segments))

    # Step 1: Generate candidates
    candidates = generate_candidates(segments)
    if not candidates:
        logger.warning("No candidates generated from %d segments", len(segments))
        return []

    logger.info("Generated %d candidates", len(candidates))

    # Step 2: Score each candidate
    scored = []
    for cand in candidates:
        score_result = score_clip(
            text=cand["text"],
            segments=cand["segments"],
            starts_at_boundary=cand.get("starts_at_boundary", True),
            ends_at_boundary=cand.get("ends_at_boundary", True),
        )

        scored.append({
            **cand,
            **score_result,
        })

    # Step 3: Sort by score (descending)
    scored.sort(key=lambda c: c["clip_quality_score"], reverse=True)

    logger.info(
        "Scored %d candidates. Top score: %d, Bottom score: %d",
        len(scored),
        scored[0]["clip_quality_score"] if scored else 0,
        scored[-1]["clip_quality_score"] if scored else 0,
    )

    # Step 4: Remove duplicates (keeps highest-scored)
    deduplicated = remove_duplicates(scored)

    # Step 5: Take top N
    top_clips = deduplicated[:max_clips]

    # Step 6: Format output
    results = []
    for idx, clip in enumerate(top_clips):
        results.append({
            "clip_index": idx + 1,
            "start": clip["start"],
            "end": clip["end"],
            "duration": clip["duration"],
            "start_formatted": _format_time(clip["start"]),
            "end_formatted": _format_time(clip["end"]),
            "text": clip["text"],
            "clip_quality_score": clip["clip_quality_score"],
            "scores": clip["scores"],
            "reasons": clip["reasons"],
            "segment_count": len(clip["segments"]),
        })

    logger.info("Returning %d clips (from %d candidates)", len(results), len(candidates))
    return results


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_clips(video_id: str, clips: list[dict]) -> Path:
    """Save generated clips to JSON."""
    clips_dir = settings.storage_path / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    clips_path = clips_dir / f"{video_id}_clips.json"
    clips_path.write_text(
        json.dumps(clips, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Saved %d clips for %s", len(clips), video_id)
    return clips_path


def load_clips(video_id: str) -> list[dict] | None:
    """Load previously generated clips."""
    clips_path = settings.storage_path / "clips" / f"{video_id}_clips.json"
    if not clips_path.exists():
        return None
    try:
        return json.loads(clips_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load clips for %s: %s", video_id, e)
        return None
