"""Pacing scoring — 0 to 10 points.

Does the clip maintain reasonable conversational pacing?

Signals:
- Words per second (speech rate)
- Not too many long silences (gaps between segments)
- Reasonable segment density
"""


def score(segments: list[dict], full_text: str | float | None = None) -> tuple[int, list[str]]:
    """Score the pacing of a clip based on its segments.

    Args:
        segments: List of dicts with 'start', 'end', 'text' keys.
        full_text: Combined text of all segments (or duration float, or omitted).

    Returns:
        (score 0-10, list of reason strings)
    """
    if not segments:
        return 0, []

    if isinstance(full_text, (int, float)) or full_text is None:
        text_str = " ".join(s.get("text", "") for s in segments)
    else:
        text_str = str(full_text)

    if not text_str.strip():
        return 0, []

    points = 0
    reasons = []

    # --- Calculate speech rate (words per second) ---
    total_duration = segments[-1]["end"] - segments[0]["start"]
    if total_duration <= 0:
        return 0, ["Invalid segment timing"]

    word_count = len(text_str.split())
    wps = word_count / total_duration

    # Ideal speech rate: 2.0 - 3.5 words per second (conversational)
    if 2.0 <= wps <= 3.5:
        points += 5
        reasons.append("Good conversational pacing")
    elif 1.5 <= wps < 2.0 or 3.5 < wps <= 4.5:
        points += 3
        reasons.append("Acceptable speech rate")
    elif 1.0 <= wps < 1.5:
        points += 1
        reasons.append("Slow pacing")
    elif wps > 4.5:
        points += 1
        reasons.append("Very fast pacing")
    else:
        reasons.append("Very slow or sparse speech")

    # --- Check for large gaps (dead air) ---
    if len(segments) >= 2:
        gaps = []
        for i in range(1, len(segments)):
            gap = segments[i]["start"] - segments[i - 1]["end"]
            if gap > 0:
                gaps.append(gap)

        if gaps:
            max_gap = max(gaps)
            avg_gap = sum(gaps) / len(gaps)

            if max_gap <= 2.0 and avg_gap <= 1.0:
                points += 3
                reasons.append("Consistent flow, minimal pauses")
            elif max_gap <= 4.0 and avg_gap <= 2.0:
                points += 2
                reasons.append("Some natural pauses")
            elif max_gap > 6.0:
                reasons.append("Contains long silence gaps")
            else:
                points += 1
        else:
            points += 3
            reasons.append("Continuous speech")

    # --- Segment density (up to 2 points) ---
    segments_per_minute = len(segments) / (total_duration / 60) if total_duration > 0 else 0
    if segments_per_minute >= 3:
        points += 2
        reasons.append("Active speech throughout")
    elif segments_per_minute >= 1.5:
        points += 1

    return min(points, 10), reasons
