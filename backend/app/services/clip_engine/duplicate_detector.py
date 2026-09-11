"""Duplicate clip detection — prevents returning near-identical clips.

Two strategies:
1. Temporal overlap: if two clips cover mostly the same time range, keep the better one.
2. Text similarity: if two clips have very similar text (Jaccard), keep the better one.
"""

import logging

logger = logging.getLogger("clipforge.clip_engine.duplicates")


def _temporal_overlap(clip_a: dict, clip_b: dict) -> float:
    """Calculate the overlap ratio between two clips.

    Returns the overlap duration divided by the shorter clip's duration.
    0.0 = no overlap, 1.0 = one clip fully contains the other.
    """
    overlap_start = max(clip_a["start"], clip_b["start"])
    overlap_end = min(clip_a["end"], clip_b["end"])
    overlap = max(0, overlap_end - overlap_start)

    shorter_duration = min(clip_a["duration"], clip_b["duration"])
    if shorter_duration <= 0:
        return 0.0

    return overlap / shorter_duration


def _text_similarity(text_a: str, text_b: str) -> float:
    """Simple Jaccard similarity between word sets of two texts.

    Returns 0.0 (completely different) to 1.0 (identical words).
    """
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def remove_duplicates(
    scored_clips: list[dict],
    overlap_threshold: float = 0.5,
    similarity_threshold: float = 0.7,
) -> list[dict]:
    """Remove duplicate or near-duplicate clips.

    Clips should already be sorted by score (highest first).
    For each pair of clips, if they overlap temporally (>50%)
    or have similar text (>70% Jaccard), keep only the higher-scored one.

    Args:
        scored_clips: List of clip dicts, sorted by clip_quality_score descending.
        overlap_threshold: Max temporal overlap ratio before deduplication.
        similarity_threshold: Max text similarity before deduplication.

    Returns:
        Deduplicated list of clips.
    """
    if len(scored_clips) <= 1:
        return scored_clips

    kept = []
    removed_count = 0

    for clip in scored_clips:
        is_duplicate = False

        for existing in kept:
            # Check temporal overlap
            overlap = _temporal_overlap(clip, existing)
            if overlap >= overlap_threshold:
                is_duplicate = True
                break

            # Check text similarity
            sim = _text_similarity(clip["text"], existing["text"])
            if sim >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(clip)
        else:
            removed_count += 1

    logger.info(
        "Deduplication: %d clips → %d clips (%d removed)",
        len(scored_clips), len(kept), removed_count,
    )
    return kept
