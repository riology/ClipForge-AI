"""Tests for the Clip Intelligence Engine and API endpoints."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.clip_engine.text_cleaner import (
    clean_text,
    count_words,
    remove_filler_words,
    split_sentences,
)
from app.services.clip_engine.scoring import (
    hook_score,
    information_score,
    emotion_score,
    context_score,
    completeness_score,
    pacing_score,
    final_score,
)
from app.services.clip_engine.candidate_generator import generate_candidates
from app.services.clip_engine.duplicate_detector import (
    _temporal_overlap,
    _text_similarity,
    remove_duplicates,
)
from app.services.clip_engine.engine import (
    analyze_transcript,
    load_clips,
    save_clips,
)
from app.services.transcription_service import save_transcript


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_segments():
    """Realistic transcript segments spanning ~90 seconds with strong and weak moments."""
    return [
        {"start": 0.0, "end": 4.5, "text": "Why do 90% of creators fail in their first year?"},
        {"start": 4.5, "end": 9.2, "text": "The biggest secret nobody tells you is consistency without strategy leads to burnout."},
        {"start": 9.2, "end": 15.0, "text": "First, you must understand your target audience deeply before ever hitting record."},
        {"start": 15.0, "end": 22.5, "text": "For example, if you make cooking tutorials, don't just teach recipes; teach quick hacks."},
        {"start": 22.5, "end": 31.0, "text": "This step-by-step framework will increase your viewer retention by over forty percent."},
        {"start": 31.0, "end": 37.8, "text": "I was honestly shocked when I looked at my analytics after applying this technique."},
        {"start": 37.8, "end": 45.0, "text": "It was unbelievable how fast the algorithm started recommending my videos."},
        {"start": 45.0, "end": 52.0, "text": "As I mentioned earlier, going back to what we said about equipment in the last chapter,"},
        {"start": 52.0, "end": 58.0, "text": "you really don't need a four thousand dollar camera to get started today."},
        {"start": 58.0, "end": 66.0, "text": "Just use your smartphone, get a twenty dollar lavalier microphone, and face a window."},
        {"start": 66.0, "end": 74.0, "text": "Remember this rule: audio quality matters far more than four K video resolution."},
        {"start": 74.0, "end": 82.5, "text": "If viewers can't hear you clearly, they will click away within the first three seconds."},
        {"start": 82.5, "end": 90.0, "text": "Start implementing this today and you will see immediate improvements."},
    ]


# ---------------------------------------------------------------------------
# Text Cleaner Tests
# ---------------------------------------------------------------------------
def test_clean_text():
    raw = "  Hello   world! [Music] (applause) This is   great.  "
    cleaned = clean_text(raw)
    assert "[Music]" not in cleaned
    assert "(applause)" not in cleaned
    assert "  " not in cleaned
    assert cleaned.startswith("Hello")


def test_remove_filler_words():
    text = "Um, you know, basically like this is actually great."
    filtered = remove_filler_words(text)
    assert "Um," not in filtered
    assert "great." in filtered


def test_split_sentences():
    text = "Here is sentence one! Why sentence two? Finally sentence three."
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Here is sentence one!"


def test_count_words():
    assert count_words("one two three four five") == 5
    assert count_words("") == 0


# ---------------------------------------------------------------------------
# Scoring Module Tests
# ---------------------------------------------------------------------------
def test_hook_scorer_strong_vs_weak():
    strong = "Why do 90% of people make this huge mistake? The biggest secret is simple."
    weak = "The meeting was held on Tuesday afternoon at the office."
    
    score_strong, reasons_strong = hook_score.score(strong)
    score_weak, reasons_weak = hook_score.score(weak)

    assert 0 <= score_strong <= 20
    assert 0 <= score_weak <= 20
    assert score_strong > score_weak
    assert len(reasons_strong) > 0


def test_information_scorer():
    informative = (
        "Here is the step-by-step tutorial. First, configure the settings. "
        "For example, you should set retention to 85 percent because this improves results."
    )
    uninformative = "Yeah, yeah, uh huh, cool, alright then."

    score_info, reasons_info = information_score.score(informative)
    score_uninfo, _ = information_score.score(uninformative)

    assert 0 <= score_info <= 20
    assert 0 <= score_uninfo <= 20
    assert score_info > score_uninfo


def test_emotion_scorer():
    emotional = "I was completely shocked and terrified! It was unbelievable, honestly incredible."
    neutral = "The temperature measured exactly 21 degrees celsius at noon."

    score_emo, reasons_emo = emotion_score.score(emotional)
    score_neu, _ = emotion_score.score(neutral)

    assert 0 <= score_emo <= 15
    assert 0 <= score_neu <= 15
    assert score_emo > score_neu


def test_context_scorer():
    self_contained = "Artificial intelligence is fundamentally revolutionizing video editing for modern creators."
    dependent = "As I mentioned earlier in chapter two, going back to what we said before..."

    score_self, _ = context_score.score(self_contained)
    score_dep, _ = context_score.score(dependent)

    assert 0 <= score_self <= 20
    assert 0 <= score_dep <= 20
    assert score_self > score_dep


def test_completeness_scorer():
    complete = "First, always check your audio. Second, keep the hook under five seconds. This guarantees engagement."
    fragment = "and then because if you"

    score_comp, _ = completeness_score.score(
        complete,
        starts_at_boundary=True,
        ends_at_boundary=True,
    )
    score_frag, _ = completeness_score.score(
        fragment,
        starts_at_boundary=False,
        ends_at_boundary=False,
    )

    assert 0 <= score_comp <= 15
    assert 0 <= score_frag <= 15
    assert score_comp > score_frag


def test_pacing_scorer():
    # Good normal speech rate ~2.5 words/sec, no gaps
    segments = [
        {"start": 0.0, "end": 4.0, "text": "This is a ten word sentence spoken at normal pace."},
        {"start": 4.0, "end": 8.0, "text": "And here is another clean ten word sentence right here."},
    ]
    score_good, _ = pacing_score.score(segments, 8.0)
    assert 0 <= score_good <= 10
    assert score_good >= 5


def test_final_score():
    text = (
        "Why do 90% of beginners quit? The biggest mistake is lack of direction. "
        "First, define your niche clearly. I was completely amazed by how well this works."
    )
    segments = [
        {"start": 0.0, "end": 5.0, "text": "Why do 90% of beginners quit?"},
        {"start": 5.0, "end": 15.0, "text": "The biggest mistake is lack of direction. First, define your niche clearly."},
        {"start": 15.0, "end": 25.0, "text": "I was completely amazed by how well this works."},
    ]
    res = final_score.score_clip(text, segments, starts_at_boundary=True, ends_at_boundary=True)

    assert "clip_quality_score" in res
    assert 0 <= res["clip_quality_score"] <= 100
    assert "scores" in res
    assert isinstance(res["reasons"], list)

    s = res["scores"]
    total = s["hook"] + s["information"] + s["emotion"] + s["context"] + s["completeness"] + s["pacing"]
    assert res["clip_quality_score"] == total


# ---------------------------------------------------------------------------
# Candidate Generator & Deduplication Tests
# ---------------------------------------------------------------------------
def test_generate_candidates(sample_segments):
    candidates = generate_candidates(sample_segments)
    assert len(candidates) > 0

    for cand in candidates:
        assert cand["duration"] >= settings.MIN_CLIP_DURATION
        assert cand["duration"] <= settings.MAX_CLIP_DURATION
        assert len(cand["segments"]) >= 2
        assert cand["text"]


def test_temporal_overlap():
    clip_a = {"start": 0.0, "end": 30.0, "duration": 30.0}
    clip_b = {"start": 15.0, "end": 45.0, "duration": 30.0}
    overlap = _temporal_overlap(clip_a, clip_b)
    # Overlap is 15s out of 30s = 0.5
    assert abs(overlap - 0.5) < 0.01

    clip_c = {"start": 50.0, "end": 80.0, "duration": 30.0}
    assert _temporal_overlap(clip_a, clip_c) == 0.0


def test_text_similarity():
    sim_identical = _text_similarity("hello world how are you", "hello world how are you")
    assert sim_identical == 1.0

    sim_distinct = _text_similarity("apples and oranges", "quantum mechanics physics")
    assert sim_distinct == 0.0


def test_remove_duplicates():
    scored_clips = [
        {
            "clip_index": 1,
            "start": 0.0,
            "end": 30.0,
            "duration": 30.0,
            "text": "Why do creators fail? First understand your audience.",
            "clip_quality_score": 85,
        },
        {
            "clip_index": 2,
            "start": 0.0,
            "end": 35.0,
            "duration": 35.0,
            "text": "Why do creators fail? First understand your audience and test hacks.",
            "clip_quality_score": 75,  # heavily overlaps with clip 1, lower score
        },
        {
            "clip_index": 3,
            "start": 50.0,
            "end": 80.0,
            "duration": 30.0,
            "text": "Smartphone microphones work great. Audio quality is king.",
            "clip_quality_score": 78,
        },
    ]

    deduped = remove_duplicates(scored_clips)
    assert len(deduped) == 2
    # Clip 1 should be kept over Clip 2
    assert deduped[0]["clip_quality_score"] == 85
    assert deduped[1]["clip_quality_score"] == 78


# ---------------------------------------------------------------------------
# Engine Orchestrator Tests
# ---------------------------------------------------------------------------
def test_analyze_transcript(sample_segments):
    clips = analyze_transcript(sample_segments, max_clips=5)
    assert len(clips) > 0
    assert len(clips) <= 5

    # Check order is descending by clip_quality_score
    scores = [c["clip_quality_score"] for c in clips]
    assert scores == sorted(scores, reverse=True)

    # Check structure
    top = clips[0]
    assert top["clip_index"] == 1
    assert "start_formatted" in top
    assert "end_formatted" in top
    assert "scores" in top
    assert "reasons" in top


def test_save_and_load_clips(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    video_id = "test_vid_123"
    clips_data = [
        {
            "clip_index": 1,
            "start": 0.0,
            "end": 30.0,
            "duration": 30.0,
            "start_formatted": "00:00",
            "end_formatted": "00:30",
            "text": "Test clip text",
            "clip_quality_score": 80,
            "scores": {"hook": 15, "information": 15, "emotion": 10, "context": 15, "completeness": 15, "pacing": 10},
            "reasons": ["Strong opening"],
            "segment_count": 3,
        }
    ]

    saved_path = save_clips(video_id, clips_data)
    assert saved_path.exists()

    loaded = load_clips(video_id)
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0]["clip_quality_score"] == 80


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    return TestClient(app)


def test_api_generate_clips_no_transcript(client):
    response = client.post("/api/clips/nonexistent_video_id/generate")
    assert response.status_code == 404
    assert "No transcription found" in response.json()["detail"]


def test_api_generate_and_get_clips(client, tmp_path, sample_segments, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    video_id = "test_api_video"

    # Pre-populate transcription
    transcript_result = {
        "text": "Full transcript text...",
        "language": "en",
        "duration": 90.0,
        "segment_count": len(sample_segments),
        "segments": sample_segments,
    }
    save_transcript(video_id, transcript_result)

    # 1. Generate clips
    res = client.post(f"/api/clips/{video_id}/generate", json={"max_clips": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["video_id"] == video_id
    assert data["clip_count"] > 0
    assert len(data["clips"]) <= 3

    # 2. Re-request returns cached
    res_cached = client.post(f"/api/clips/{video_id}/generate")
    assert res_cached.status_code == 200
    assert "returning cached result" in res_cached.json()["message"]

    # 3. GET all clips
    res_get = client.get(f"/api/clips/{video_id}")
    assert res_get.status_code == 200
    assert res_get.json()["clip_count"] == data["clip_count"]

    # 4. GET specific clip by index
    res_single = client.get(f"/api/clips/{video_id}/1")
    assert res_single.status_code == 200
    assert res_single.json()["clip_index"] == 1

    # 5. GET invalid clip index -> 404
    res_not_found = client.get(f"/api/clips/{video_id}/999")
    assert res_not_found.status_code == 404
