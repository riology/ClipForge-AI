"""Completeness scoring — 0 to 15 points.

Does the clip have a natural beginning, middle, and end?

Signals:
- Starts at a sentence boundary (not mid-sentence)
- Ends at a sentence boundary
- Contains a complete thought arc
- Doesn't feel abruptly cut off
"""

import re

from app.services.clip_engine.text_cleaner import get_sentences, word_count


def score(
    text: str,
    starts_at_segment_boundary: bool = True,
    ends_at_segment_boundary: bool = True,
    starts_at_boundary: bool | None = None,
    ends_at_boundary: bool | None = None,
) -> tuple[int, list[str]]:
    """Score the completeness of a clip.

    Args:
        text: Full text of the clip.
        starts_at_segment_boundary: Whether the clip starts at a transcript
            segment boundary (not mid-segment).
        ends_at_segment_boundary: Whether the clip ends at a transcript
            segment boundary.
        starts_at_boundary: Alias for starts_at_segment_boundary.
        ends_at_boundary: Alias for ends_at_segment_boundary.

    Returns:
        (score 0-15, list of reason strings)
    """
    if starts_at_boundary is not None:
        starts_at_segment_boundary = starts_at_boundary
    if ends_at_boundary is not None:
        ends_at_segment_boundary = ends_at_boundary
    if not text.strip():
        return 0, []

    sentences = get_sentences(text)
    points = 0
    reasons = []

    # --- Natural start (up to 5 points) ---
    if starts_at_segment_boundary:
        points += 3
    else:
        reasons.append("May start mid-thought")

    if sentences:
        first = sentences[0].strip()
        # Starts with capital letter (natural sentence start)
        if first and first[0].isupper():
            points += 2
            reasons.append("Natural sentence opening")

    # --- Natural ending (up to 5 points) ---
    if ends_at_segment_boundary:
        points += 3
    else:
        reasons.append("May end mid-thought")

    if sentences:
        last = sentences[-1].strip()
        # Ends with proper punctuation
        if last and last[-1] in ".!?":
            points += 2
            reasons.append("Ends with complete sentence")

    # --- Complete thought arc (up to 5 points) ---
    num_sentences = len(sentences)
    wc = word_count(text)

    if num_sentences >= 3 and wc >= 30:
        points += 5
        reasons.append("Complete multi-sentence idea")
    elif num_sentences >= 2 and wc >= 20:
        points += 3
        reasons.append("Contains a developed thought")
    elif num_sentences >= 1 and wc >= 10:
        points += 1
        reasons.append("Contains a basic thought")

    if not reasons:
        reasons.append("Partial completeness")

    return min(points, 15), reasons
