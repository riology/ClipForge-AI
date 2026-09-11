"""Clean and normalize transcript text for analysis."""

import re


def clean_text(text: str) -> str:
    """Normalize transcript text for scoring and analysis.

    - Collapse whitespace
    - Fix common Whisper artifacts
    - Normalize punctuation
    """
    if not text:
        return ""

    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()

    # Remove sound/ambient descriptions like [Music], (applause)
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text)

    # Remove filler sounds that Whisper sometimes includes
    text = re.sub(r"\b(uh|um|uhm|hmm|huh|mhm)\b", "", text, flags=re.IGNORECASE)

    # Collapse spaces again after removal
    text = re.sub(r"\s+", " ", text).strip()

    return text


def get_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries.

    Handles common cases like Mr./Dr./etc. abbreviations.
    """
    if not text.strip():
        return []

    # Protect common abbreviations
    protected = text
    abbrevs = ["Mr.", "Mrs.", "Dr.", "Ms.", "Prof.", "Jr.", "Sr.", "vs.", "etc.", "e.g.", "i.e."]
    for abbr in abbrevs:
        protected = protected.replace(abbr, abbr.replace(".", "<<DOT>>"))

    # Split on sentence-ending punctuation
    parts = re.split(r"(?<=[.!?])\s+", protected)

    # Restore abbreviations
    sentences = []
    for part in parts:
        restored = part.replace("<<DOT>>", ".")
        restored = restored.strip()
        if restored:
            sentences.append(restored)

    return sentences


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split()) if text.strip() else 0


def count_words(text: str) -> int:
    """Alias for word_count."""
    return word_count(text)


def split_sentences(text: str) -> list[str]:
    """Alias for get_sentences."""
    return get_sentences(text)


def remove_filler_words(text: str) -> str:
    """Remove filler words and phrases from text."""
    if not text:
        return ""
    fillers = [
        r"\b(uh|um|uhm|hmm|huh|mhm)\b",
        r"\b(you know|like|basically|actually)\b",
    ]
    result = text
    for pattern in fillers:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", result).strip()

