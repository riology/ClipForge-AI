"""Hook Strength scoring — 0 to 20 points.

Does the opening of the clip grab attention?

Signals:
- Starts with a question
- Contains strong/surprising statement
- Uses power words (biggest, secret, mistake, never, always)
- Opens with a number or statistic
- Short, punchy opening sentence
"""

import re

from app.services.clip_engine.text_cleaner import get_sentences, word_count

# Curated word lists for hook detection
QUESTION_WORDS = {"who", "what", "where", "when", "why", "how", "which", "whose",
                  "would", "could", "should", "can", "do", "does", "did", "is", "are", "was"}

POWER_WORDS = {
    "secret", "secrets", "mistake", "mistakes", "biggest", "worst", "best",
    "most", "never", "always", "actually", "truth", "proven", "guaranteed",
    "surprising", "shocking", "incredible", "unbelievable", "critical",
    "essential", "crucial", "dangerous", "powerful", "ultimate", "hack",
    "hacks", "trick", "tricks", "myth", "myths", "wrong", "stop",
    "warning", "urgent", "important", "revolutionary", "game-changer",
    "breakthrough", "hidden", "unknown", "overlooked", "underrated",
    "overrated", "real", "honest", "brutal", "hard", "painful",
}

CURIOSITY_PATTERNS = [
    r"\bhere'?s?\s+(the\s+)?(thing|deal|problem|truth|secret|reason)\b",
    r"\blet\s+me\s+tell\s+you\b",
    r"\bwhat\s+(?:most\s+)?people\s+don'?t\b",
    r"\byou\s+(?:won'?t|wouldn'?t)\s+believe\b",
    r"\bno\s+one\s+(?:talks?|tells?|knows?)\b",
    r"\bthe\s+(?:real|actual|biggest)\s+(?:reason|problem|issue|mistake)\b",
    r"\bif\s+you(?:'re)?\s+(?:still|not)\b",
    r"\bstop\s+doing\b",
    r"\bthis\s+is\s+(?:why|how|what)\b",
    r"\bi\s+(?:was|got)\s+(?:wrong|shocked|surprised)\b",
    r"\bnumber\s+\d+\b",
    r"\b\d+\s+(?:things?|ways?|reasons?|tips?|steps?|mistakes?)\b",
]


def score(text: str) -> tuple[int, list[str]]:
    """Score the hook strength of a clip's opening.

    Args:
        text: Full text of the clip.

    Returns:
        (score 0-20, list of reason strings)
    """
    sentences = get_sentences(text)
    if not sentences:
        return 0, []

    opening = sentences[0].lower().strip()
    opening_words = opening.split()
    points = 0
    reasons = []

    # --- Question opening (up to 5 points) ---
    if opening.rstrip().endswith("?"):
        points += 5
        reasons.append("Opens with a question")
    elif opening_words and opening_words[0] in QUESTION_WORDS:
        points += 3
        reasons.append("Starts with a question word")

    # --- Power words (up to 5 points) ---
    power_found = [w for w in POWER_WORDS if w in opening]
    if power_found:
        points += min(len(power_found) * 2, 5)
        reasons.append(f"Strong language: {', '.join(power_found[:3])}")

    # --- Curiosity patterns (up to 5 points) ---
    curiosity_hits = 0
    for pattern in CURIOSITY_PATTERNS:
        if re.search(pattern, opening, re.IGNORECASE):
            curiosity_hits += 1
    if curiosity_hits > 0:
        points += min(curiosity_hits * 3, 5)
        reasons.append("Curiosity-triggering opening")

    # --- Number/statistic in opening (up to 3 points) ---
    if re.search(r"\b\d+[\d,.]*\s*(%|percent|million|billion|thousand|x|times)\b", opening):
        points += 3
        reasons.append("Contains a statistic")
    elif re.search(r"\b\d+\b", opening):
        points += 1
        reasons.append("Contains a number")

    # --- Short punchy opening (up to 2 points) ---
    opening_wc = word_count(sentences[0])
    if 3 <= opening_wc <= 12:
        points += 2
        reasons.append("Short, punchy opening")

    return min(points, 20), reasons
