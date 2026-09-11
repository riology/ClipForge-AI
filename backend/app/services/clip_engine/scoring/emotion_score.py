"""Emotional Interest scoring — 0 to 15 points.

Does the clip contain emotionally engaging content?

Signals:
- Surprise or unexpected information
- Strong opinions
- Excitement or enthusiasm
- Humor indicators
- Emotional/personal language
"""

import re

# Emotion word categories
SURPRISE_WORDS = {
    "actually", "surprisingly", "shocked", "shocking", "unbelievable",
    "incredible", "crazy", "insane", "wild", "unexpected", "amazed",
    "amazingly", "mind-blowing", "jaw-dropping", "turns out",
    "believe it or not", "plot twist", "wait", "wow",
}

EXCITEMENT_WORDS = {
    "amazing", "awesome", "fantastic", "brilliant", "excellent",
    "extraordinary", "phenomenal", "outstanding", "love", "loved",
    "beautiful", "wonderful", "perfect", "epic", "fire",
    "exciting", "thrilling", "passion", "passionate", "dream",
}

NEGATIVE_EMOTION_WORDS = {
    "terrible", "horrible", "awful", "disgusting", "hate", "hated",
    "frustrating", "frustrated", "angry", "furious", "devastated",
    "heartbreaking", "painful", "scary", "terrifying", "nightmare",
    "disaster", "catastrophe", "depressing", "tragic", "devastating",
}

OPINION_WORDS = {
    "absolutely", "definitely", "honestly", "frankly", "literally",
    "completely", "totally", "utterly", "entirely", "clearly",
    "obviously", "undoubtedly", "without a doubt", "hands down",
    "by far", "no question", "period",
}

PERSONAL_PATTERNS = [
    r"\bi\s+(?:personally|remember|recall|felt|feel|think|believe|learned|realized)\b",
    r"\bmy\s+(?:experience|story|life|journey|biggest|worst|best)\b",
    r"\bwhen\s+i\s+(?:was|first|started|tried|saw|heard)\b",
    r"\bit\s+(?:changed|transformed|ruined|saved)\s+my\b",
]


def score(text: str) -> tuple[int, list[str]]:
    """Score the emotional interest of a clip.

    Args:
        text: Full text of the clip.

    Returns:
        (score 0-15, list of reason strings)
    """
    if not text.strip():
        return 0, []

    lower = text.lower()
    words = set(lower.split())
    points = 0
    reasons = []

    # --- Surprise (up to 4 points) ---
    surprise_count = len(words & SURPRISE_WORDS)
    if surprise_count >= 2:
        points += 4
        reasons.append("Contains surprising/unexpected elements")
    elif surprise_count >= 1:
        points += 2
        reasons.append("Hint of surprise")

    # --- Excitement or strong positive emotion (up to 3 points) ---
    excitement_count = len(words & EXCITEMENT_WORDS)
    if excitement_count >= 2:
        points += 3
        reasons.append("Enthusiastic/excited tone")
    elif excitement_count >= 1:
        points += 1

    # --- Negative emotion / conflict (up to 3 points) ---
    negative_count = len(words & NEGATIVE_EMOTION_WORDS)
    if negative_count >= 2:
        points += 3
        reasons.append("Strong emotional content")
    elif negative_count >= 1:
        points += 2
        reasons.append("Emotional weight")

    # --- Strong opinion (up to 2 points) ---
    opinion_count = len(words & OPINION_WORDS)
    if opinion_count >= 2:
        points += 2
        reasons.append("Strong opinion expressed")
    elif opinion_count >= 1:
        points += 1

    # --- Personal story (up to 3 points) ---
    personal_hits = sum(1 for p in PERSONAL_PATTERNS if re.search(p, lower))
    if personal_hits >= 2:
        points += 3
        reasons.append("Personal story or experience")
    elif personal_hits >= 1:
        points += 2
        reasons.append("Personal perspective")

    # --- Exclamation marks (up to 1 point) ---
    if text.count("!") >= 1:
        points += 1

    return min(points, 15), reasons
