"""Candidate clip generator — groups transcript segments into clip candidates.

Strategy:
  1. Slide a window over the transcript segments
  2. For each position, try to build clips of varying duration (30-60s preferred)
  3. Prefer to start at topic/sentence boundaries
  4. Prefer to end at sentence boundaries
  5. Ensure clips fall within 15-90 second limits
"""

import logging
import re
from app.core.config import settings
from app.services.clip_engine.text_cleaner import clean_text

logger = logging.getLogger("clipforge.clip_engine.candidates")

# Signals that a segment might be a good starting point
STRONG_START_PATTERNS = [
    r"^(?:so|now|okay|alright|let'?s?|here|the|one|first|if|when|what|why|how|who)\b",
    r"^(?:i\s+(?:want|think|believe|personally)|you\s+(?:know|should|need))\b",
    r"^(?:the\s+(?:biggest|most|key|real|first|main))\b",
    r"\?$",  # Questions are good openers
]


def _is_strong_start(text: str) -> bool:
    """Check if a segment's text is a good clip opening."""
    lower = text.lower().strip()
    return any(re.search(p, lower) for p in STRONG_START_PATTERNS)


def _is_sentence_end(text: str) -> bool:
    """Check if text ends at a sentence boundary."""
    stripped = text.strip()
    return bool(stripped) and stripped[-1] in ".!?"


def generate_candidates(segments: list[dict]) -> list[dict]:
    """Generate clip candidates from transcript segments.

    Args:
        segments: List of transcript segments, each with 'start', 'end', 'text'.

    Returns:
        List of candidate dicts, each with:
          - start: float (start time in seconds)
          - end: float (end time in seconds)
          - segments: list of included segments
          - text: combined cleaned text
          - duration: float
          - segment_indices: (start_idx, end_idx)
    """
    if not segments:
        return []

    min_dur = settings.MIN_CLIP_DURATION
    pref_min = settings.PREFERRED_CLIP_DURATION_MIN
    pref_max = settings.PREFERRED_CLIP_DURATION_MAX
    max_dur = settings.MAX_CLIP_DURATION

    candidates = []
    n = len(segments)

    for i in range(n):
        # Build clips starting at segment i
        combined_text = ""
        clip_segments = []

        for j in range(i, n):
            seg = segments[j]
            seg_text = clean_text(seg["text"])
            if not seg_text:
                continue

            clip_segments.append(seg)
            combined_text = (combined_text + " " + seg_text).strip()

            duration = seg["end"] - segments[i]["start"]

            # Too short — keep adding
            if duration < min_dur:
                continue

            # Too long — stop
            if duration > max_dur:
                break

            # Within range — evaluate if this is a good clip boundary
            is_preferred = pref_min <= duration <= pref_max
            ends_cleanly = _is_sentence_end(seg_text)
            starts_strongly = _is_strong_start(segments[i]["text"])

            # Create candidate if:
            # 1. Preferred duration AND ends at sentence, OR
            # 2. Preferred duration AND strong start, OR
            # 3. At max preferred and ends at sentence, OR
            # 4. Every N segments as a fallback
            should_emit = (
                (is_preferred and ends_cleanly)
                or (is_preferred and starts_strongly and j - i >= 2)
                or (duration >= pref_max and ends_cleanly)
                or (duration >= pref_min and j == n - 1)  # End of transcript
            )

            if should_emit and len(clip_segments) >= 2:
                candidates.append({
                    "start": segments[i]["start"],
                    "end": seg["end"],
                    "segments": list(clip_segments),
                    "text": combined_text,
                    "duration": round(duration, 2),
                    "segment_indices": (i, j),
                    "starts_at_boundary": True,
                    "ends_at_boundary": ends_cleanly,
                })

    logger.info("Generated %d raw candidates from %d segments", len(candidates), n)
    return candidates
