"""Tests for the Video Export Service and Shorts API endpoints."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.subtitle_service import (
    _format_ass_time,
    _format_srt_time,
    filter_clip_segments,
    generate_ass_subtitles,
    generate_srt_subtitles,
)
from app.services.export_service import (
    export_clip,
    find_export_path,
    get_export_metadata,
    list_exports_for_video,
)
from app.services.clip_engine.engine import save_clips
from app.services.transcription_service import save_transcript


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def test_video_path():
    """Path to the synthetic test video fixture."""
    path = Path(__file__).parent / "fixtures" / "test_video.mp4"
    assert path.exists(), "test_video.mp4 fixture is missing"
    return path


@pytest.fixture
def mock_segments():
    return [
        {"start": 0.0, "end": 1.5, "text": "Why do creators fail?"},
        {"start": 1.5, "end": 3.0, "text": "Here is the key insight."},
    ]


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Subtitle Service Tests
# ---------------------------------------------------------------------------
def test_format_ass_time():
    assert _format_ass_time(0.0) == "0:00:00.00"
    assert _format_ass_time(65.42) == "0:01:05.42"
    assert _format_ass_time(3661.05) == "1:01:01.05"


def test_format_srt_time():
    assert _format_srt_time(0.0) == "00:00:00,000"
    assert _format_srt_time(65.42) == "00:01:05,420"
    assert _format_srt_time(3661.05) == "01:01:01,050"


def test_filter_clip_segments(mock_segments):
    filtered = filter_clip_segments(mock_segments, clip_start=0.5, clip_end=2.5)
    assert len(filtered) == 2
    # Segment 1 was [0.0, 1.5] -> relative to 0.5 becomes [0.0, 1.0]
    assert filtered[0]["start"] == 0.0
    assert filtered[0]["end"] == 1.0
    # Segment 2 was [1.5, 3.0] -> relative to 0.5 becomes [1.0, 2.0]
    assert filtered[1]["start"] == 1.0
    assert filtered[1]["end"] == 2.0


def test_generate_ass_subtitles(mock_segments):
    ass = generate_ass_subtitles(
        segments=mock_segments,
        clip_start=0.0,
        clip_end=3.0,
        color="yellow",
    )
    assert "[Script Info]" in ass
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1920" in ass
    assert "WHY DO CREATORS FAIL?" in ass
    assert "Dialogue: 0," in ass


def test_generate_srt_subtitles(mock_segments):
    srt = generate_srt_subtitles(
        segments=mock_segments,
        clip_start=0.0,
        clip_end=3.0,
    )
    assert "1\n00:00:00,000 -->" in srt
    assert "Why do creators fail?" in srt


# ---------------------------------------------------------------------------
# Video Export Service Tests
# ---------------------------------------------------------------------------
def test_export_clip_blur_background(tmp_path, test_video_path, mock_segments, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    video_id = "test_vid_export"
    meta = export_clip(
        video_path=test_video_path,
        video_id=video_id,
        start=0.0,
        end=2.0,
        aspect_ratio="9:16",
        layout="blur_background",
        burn_subtitles=True,
        subtitle_color="yellow",
        segments=mock_segments,
    )

    assert meta["video_id"] == video_id
    assert meta["aspect_ratio"] == "9:16"
    assert meta["layout"] == "blur_background"
    assert meta["width"] == 1080
    assert meta["height"] == 1920
    assert meta["burn_subtitles"] is True
    assert meta["duration"] == 2.0
    assert meta["file_size_bytes"] > 0

    export_id = meta["export_id"]
    output_file = find_export_path(export_id)
    assert output_file is not None
    assert output_file.exists()


def test_export_clip_crop(tmp_path, test_video_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    video_id = "test_crop_vid"
    meta = export_clip(
        video_path=test_video_path,
        video_id=video_id,
        start=0.5,
        end=2.0,
        aspect_ratio="9:16",
        layout="crop",
        burn_subtitles=False,
    )

    assert meta["width"] == 1080
    assert meta["height"] == 1920
    assert meta["burn_subtitles"] is False


def test_list_exports_for_video(tmp_path, test_video_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    video_id = "test_list_vid"
    export_clip(
        video_path=test_video_path,
        video_id=video_id,
        start=0.0,
        end=1.5,
        burn_subtitles=False,
    )

    exports = list_exports_for_video(video_id)
    assert len(exports) == 1
    assert exports[0]["video_id"] == video_id


# ---------------------------------------------------------------------------
# Export API Endpoint Tests
# ---------------------------------------------------------------------------
def test_api_export_missing_video(client):
    res = client.post("/api/export/nonexistent_vid", json={"start": 0.0, "end": 2.0})
    assert res.status_code == 404


def test_api_export_missing_timestamps(client, tmp_path, test_video_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    # Place video in uploads
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    video_id = "vid_upload_test"
    (uploads_dir / f"{video_id}.mp4").write_bytes(test_video_path.read_bytes())

    # Request without clip_index or start/end
    res = client.post(f"/api/export/{video_id}", json={})
    assert res.status_code == 400


def test_api_export_flow(client, tmp_path, test_video_path, mock_segments, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    # 1. Setup video and transcript
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    video_id = "vid_full_flow"
    (uploads_dir / f"{video_id}.mp4").write_bytes(test_video_path.read_bytes())

    save_transcript(video_id, {
        "text": "Full text...",
        "language": "en",
        "duration": 3.0,
        "segment_count": 2,
        "segments": mock_segments,
    })

    save_clips(video_id, [
        {
            "clip_index": 1,
            "start": 0.0,
            "end": 2.0,
            "duration": 2.0,
            "start_formatted": "00:00",
            "end_formatted": "00:02",
            "text": "Why do creators fail?",
            "clip_quality_score": 85,
            "scores": {"hook": 15, "information": 15, "emotion": 10, "context": 15, "completeness": 15, "pacing": 10},
            "reasons": ["Opening question"],
            "segment_count": 1,
        }
    ])

    # 2. Export via clip_index
    res = client.post(
        f"/api/export/{video_id}",
        json={
            "clip_index": 1,
            "aspect_ratio": "9:16",
            "layout": "blur_background",
            "burn_subtitles": True,
            "subtitle_color": "yellow",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "download_url" in data
    export_id = data["export"]["export_id"]

    # 3. Get export metadata
    res_get = client.get(f"/api/export/{export_id}")
    assert res_get.status_code == 200
    assert res_get.json()["export"]["export_id"] == export_id

    # 4. Download file
    res_dl = client.get(f"/api/export/{export_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.headers["content-type"] == "video/mp4"
    assert len(res_dl.content) > 0

    # 5. List exports
    res_list = client.get(f"/api/export/list/{video_id}")
    assert res_list.status_code == 200
    assert res_list.json()["total_exports"] == 1
