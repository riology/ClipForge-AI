"""Information Value scoring — 0 to 20 points.

Does the clip contain useful, actionable, or educational content?

Signals:
- Advice / instructional language
- Explanatory language
- Specific examples or data
- Step-by-step or list structure
- Definitions or clarifications
"""

import re

from app.services.clip_engine.text_cleaner import word_count

# Patterns indicating advice/instruction
ADVICE_PATTERNS = [
    r"\byou\s+(?:should|need\s+to|have\s+to|must|gotta|want\s+to)\b",
    r"\bmake\s+sure\b",
    r"\bthe\s+(?:key|trick|secret|important\s+thing)\s+is\b",
    r"\b(?:my|the|a)\s+(?:tip|advice|suggestion|recommendation)\b",
    r"\b(?:first|second|third|next|finally|lastly)\b",
    r"\bstep\s+\d+\b",
    r"\bhere'?s?\s+(?:how|what|why)\b",
    r"\bdon'?t\s+(?:ever|just|forget)\b",
    r"\binstead\s+of\b",
    r"\bthe\s+(?:best|right|wrong|better|proper)\s+way\b",
    r"\balways\s+(?:make|do|check|use|try)\b",
]

# Patterns indicating explanation
EXPLANATION_PATTERNS = [
    r"\bbecause\b",
    r"\bthe\s+reason\s+(?:is|why|for)\b",
    r"\bthis\s+(?:means|shows|proves|suggests|indicates)\b",
    r"\bin\s+other\s+words\b",
    r"\bfor\s+example\b",
    r"\bfor\s+instance\b",
    r"\bin\s+fact\b",
    r"\bbasically\b",
    r"\bessentially\b",
    r"\bwhat\s+(?:this|that|it)\s+means\b",
    r"\bthe\s+(?:point|idea|concept|principle)\s+(?:is|here)\b",
    r"\bso\s+(?:what|the|basically)\b",
]

# Patterns indicating specific data/examples
SPECIFICITY_PATTERNS = [
    r"\b\d+[\d,.]*\s*(?:%|percent|dollars?|hours?|minutes?|days?|years?|times?)\b",
    r"\baccording\s+to\b",
    r"\bresearch\s+(?:shows?|says?|suggests?|found)\b",
    r"\bstud(?:y|ies)\s+(?:show|found|suggest|from)\b",
    r"\bdata\s+(?:shows?|suggests?)\b",
    r"\bspecifically\b",
]


def score(text: str) -> tuple[int, list[str]]:
    """Score the information value of a clip.

    Args:
        text: Full text of the clip.

    Returns:
        (score 0-20, list of reason strings)
    """
    if not text.strip():
        return 0, []

    lower = text.lower()
    points = 0
    reasons = []

    # --- Advice/Instructional content (up to 7 points) ---
    advice_hits = sum(1 for p in ADVICE_PATTERNS if re.search(p, lower))
    if advice_hits >= 3:
        points += 7
        reasons.append("Contains actionable advice")
    elif advice_hits >= 1:
        points += 4
        reasons.append("Contains some instructional content")

    # --- Explanatory content (up to 6 points) ---
    explain_hits = sum(1 for p in EXPLANATION_PATTERNS if re.search(p, lower))
    if explain_hits >= 3:
        points += 6
        reasons.append("Strong explanatory content")
    elif explain_hits >= 1:
        points += 3
        reasons.append("Contains explanation")

    # --- Specific data/examples (up to 5 points) ---
    specific_hits = sum(1 for p in SPECIFICITY_PATTERNS if re.search(p, lower))
    if specific_hits >= 2:
        points += 5
        reasons.append("Contains specific data or examples")
    elif specific_hits >= 1:
        points += 3
        reasons.append("References specific information")

    # --- Word density bonus (up to 2 points) ---
    wc = word_count(text)
    if wc >= 50:
        points += 2
        reasons.append("Substantive content length")
    elif wc >= 30:
        points += 1

    return min(points, 20), reasons
