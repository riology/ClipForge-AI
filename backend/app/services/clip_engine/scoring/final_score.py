"""Final Score — combines all 6 scoring dimensions into a Clip Quality Score.

Score breakdown:
  Hook Strength:      0–20
  Information Value:  0–20
  Emotional Interest: 0–15
  Standalone Context: 0–20
  Completeness:       0–15
  Pacing:             0–10
  ─────────────────────────
  Total:              0–100
"""

from app.services.clip_engine.scoring import (
    hook_score,
    information_score,
    emotion_score,
    context_score,
    completeness_score,
    pacing_score,
)


def score_clip(
    text: str,
    segments: list[dict],
    starts_at_boundary: bool = True,
    ends_at_boundary: bool = True,
) -> dict:
    """Score a clip candidate across all 6 dimensions.

    Args:
        text: Full combined text of the clip.
        segments: List of transcript segments in the clip.
        starts_at_boundary: Whether clip starts at a segment boundary.
        ends_at_boundary: Whether clip ends at a segment boundary.

    Returns:
        Dict with clip_quality_score, individual scores, and reasons.
    """
    # Run each scorer
    hook_pts, hook_reasons = hook_score.score(text)
    info_pts, info_reasons = information_score.score(text)
    emo_pts, emo_reasons = emotion_score.score(text)
    ctx_pts, ctx_reasons = context_score.score(text)
    comp_pts, comp_reasons = completeness_score.score(
        text, starts_at_boundary, ends_at_boundary
    )
    pace_pts, pace_reasons = pacing_score.score(segments, text)

    # Combine
    total = hook_pts + info_pts + emo_pts + ctx_pts + comp_pts + pace_pts

    # Collect all non-empty reasons
    all_reasons = []
    for reasons in [hook_reasons, info_reasons, emo_reasons,
                    ctx_reasons, comp_reasons, pace_reasons]:
        all_reasons.extend(reasons)

    return {
        "clip_quality_score": min(total, 100),
        "scores": {
            "hook": hook_pts,
            "information": info_pts,
            "emotion": emo_pts,
            "context": ctx_pts,
            "completeness": comp_pts,
            "pacing": pace_pts,
        },
        "reasons": all_reasons,
    }
