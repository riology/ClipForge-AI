"""Standalone Context scoring — 0 to 20 points.

Can a viewer understand this clip without watching the full video?

Signals:
- Does NOT heavily reference previous context ("as I mentioned", "going back to")
- Introduces its own topic/subject clearly
- Self-contained idea
- Doesn't start with "and", "but", "so" in a continuation sense
"""

import re

from app.services.clip_engine.text_cleaner import get_sentences

# Patterns that suggest the clip DEPENDS on external context (negative signals)
DEPENDENCY_PATTERNS = [
    r"^(?:and|but|so|also|plus|or)\s",       # Starts with conjunction (continuation)
    r"\bas\s+(?:i|we)\s+(?:said|mentioned|discussed|talked|showed|explained)\b",
    r"\bgoing\s+back\s+to\b",
    r"\bremember\s+(?:when|what|how)\s+(?:i|we)\b",
    r"\blike\s+(?:i|we)\s+said\b",
    r"\bearlier\s+(?:i|we)\b",
    r"\bthis\s+(?:one|thing|part)\b(?!\s+(?:is|was|shows))",  # "this one" without intro
    r"\bthat\s+(?:thing|part|section|point)\s+(?:i|we)\b",
    r"\bcontinuing\s+(?:from|with|on)\b",
    r"\banyway(?:s)?,?\s+(?:so|back)\b",
]

# Patterns that suggest the clip INTRODUCES its own context (positive signals)
SELF_INTRO_PATTERNS = [
    r"\btoday\s+(?:i|we|i'm|we're)\b",
    r"\blet'?s?\s+talk\s+about\b",
    r"\bi\s+want\s+to\s+(?:talk|share|tell|show|discuss)\b",
    r"\bso\s+(?:there'?s?|here'?s?|the)\b",  # "so there's this thing"
    r"\bwhen\s+it\s+comes\s+to\b",
    r"\b(?:the|a)\s+(?:biggest|most\s+important|key|main|first|real)\s+(?:thing|point|issue|problem|question|lesson)\b",
    r"\bif\s+you(?:'re)?\s+(?:a|new|trying|wondering|looking)\b",
    r"\bone\s+(?:of\s+the|thing)\b",
    r"\bthere(?:'s| is| are)\s+(?:a|one|something|this)\b",
]


def score(text: str) -> tuple[int, list[str]]:
    """Score how well the clip stands alone without additional context.

    Args:
        text: Full text of the clip.

    Returns:
        (score 0-20, list of reason strings)
    """
    if not text.strip():
        return 0, []

    lower = text.lower()
    sentences = get_sentences(text)
    points = 0
    reasons = []

    # --- Check for dependency signals (subtract from base) ---
    # Start with a base score of 12, then adjust
    points = 12

    dependency_hits = sum(1 for p in DEPENDENCY_PATTERNS if re.search(p, lower))
    if dependency_hits >= 3:
        points -= 8
        reasons.append("Heavily references prior context")
    elif dependency_hits >= 2:
        points -= 5
        reasons.append("References prior context")
    elif dependency_hits >= 1:
        points -= 3
        reasons.append("Minor dependency on prior context")

    # --- Opening sentence starts with a weak conjunction ---
    if sentences:
        first_lower = sentences[0].lower().strip()
        if re.match(r"^(?:and|but|so|also)\s", first_lower):
            points -= 2
            reasons.append("Opens with continuation word")

    # --- Self-introduction patterns (positive) ---
    intro_hits = sum(1 for p in SELF_INTRO_PATTERNS if re.search(p, lower))
    if intro_hits >= 2:
        points += 5
        reasons.append("Clearly introduces its own topic")
    elif intro_hits >= 1:
        points += 3
        reasons.append("Some self-contained context")

    # --- Contains a clear subject/topic early ---
    if sentences and len(sentences) >= 2:
        # If the first two sentences set up a topic, bonus
        first_two = " ".join(sentences[:2]).lower()
        if re.search(r"\b(?:is|are|means?|about|called|known)\b", first_two):
            points += 3
            reasons.append("Establishes subject early")

    if not reasons:
        reasons.append("Adequate standalone context")

    return max(0, min(points, 20)), reasons
