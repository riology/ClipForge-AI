"""Tests for the transcription service and API endpoints.

NOTE: The test video contains a 440 Hz sine wave tone (not speech),
so faster-whisper will produce few or zero transcript segments.
This is expected — these tests verify the pipeline runs without errors
and returns correctly-structured responses.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.transcription_service import (
    TranscriptionError,
    save_transcript,
    load_transcript,
    has_transcript,
    transcribe_audio,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TEST_FIXTURES = Path(__file__).parent / "fixtures"


def _upload_and_extract(client_) -> str:
    """Upload the test video and extract audio, return the video_id."""
    test_video = TEST_FIXTURES / "test_video.mp4"
    with open(test_video, "rb") as f:
        resp = client_.post(
            "/api/videos/upload",
            files={"file": ("test.mp4", f, "video/mp4")},
        )
    assert resp.status_code == 200
    video_id = resp.json()["video_id"]

    # Extract audio
    resp = client_.post(f"/api/videos/{video_id}/extract-audio")
    assert resp.status_code == 200

    return video_id


# ===========================================================================
# Unit tests — transcript persistence
# ===========================================================================
class TestTranscriptPersistence:
    def test_save_and_load(self, tmp_path):
        """Save a transcript and load it back."""
        import app.services.transcription_service as ts

        original = ts.settings.STORAGE_DIR
        ts.settings.STORAGE_DIR = str(tmp_path)

        try:
            data = {
                "language": "en",
                "language_probability": 0.95,
                "duration_seconds": 10.0,
                "segment_count": 2,
                "segments": [
                    {"start": 0.0, "end": 5.0, "text": "Hello world"},
                    {"start": 5.0, "end": 10.0, "text": "How are you"},
                ],
                "full_text": "Hello world How are you",
            }

            path = save_transcript("test123", data)
            assert path.exists()

            loaded = load_transcript("test123")
            assert loaded is not None
            assert loaded["language"] == "en"
            assert loaded["segment_count"] == 2
            assert len(loaded["segments"]) == 2
        finally:
            ts.settings.STORAGE_DIR = original

    def test_load_nonexistent(self):
        """Loading a nonexistent transcript returns None."""
        result = load_transcript("does_not_exist_xyz")
        assert result is None

    def test_has_transcript_false(self):
        """has_transcript returns False for missing transcripts."""
        assert has_transcript("does_not_exist_xyz") is False


# ===========================================================================
# Integration test — actual transcription with faster-whisper
# ===========================================================================
class TestTranscriptionService:
    def test_transcribe_audio_runs_without_error(self):
        """Transcribe the test audio (sine wave).

        The sine wave will produce minimal/empty segments, but the
        pipeline should complete without errors.
        """
        video_id = _upload_and_extract(client)

        from app.services.video_service import find_audio_path
        audio_path = find_audio_path(video_id)
        assert audio_path is not None

        result = transcribe_audio(audio_path)

        # Verify structure
        assert "language" in result
        assert "segments" in result
        assert isinstance(result["segments"], list)
        assert "full_text" in result
        assert result["duration_seconds"] > 0

    def test_transcribe_missing_audio(self):
        """Transcribing a nonexistent audio file should raise an error."""
        with pytest.raises(TranscriptionError, match="not found"):
            transcribe_audio(Path("/nonexistent/audio.wav"))


# ===========================================================================
# API integration tests
# ===========================================================================
class TestTranscriptionEndpoints:
    def test_transcribe_no_audio(self):
        """Transcription should fail gracefully if audio isn't extracted."""
        response = client.post("/api/transcription/nonexistent123/transcribe")
        assert response.status_code == 404

    def test_transcribe_success(self):
        """Full pipeline: upload → extract audio → transcribe."""
        video_id = _upload_and_extract(client)

        response = client.post(f"/api/transcription/{video_id}/transcribe")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Transcription completed successfully."
        assert data["result"]["video_id"] == video_id
        assert "language" in data["result"]
        assert "segments" in data["result"]
        assert isinstance(data["result"]["segments"], list)

    def test_transcribe_cached(self):
        """Second transcription request should return cached result."""
        video_id = _upload_and_extract(client)

        # First transcription
        resp1 = client.post(f"/api/transcription/{video_id}/transcribe")
        assert resp1.status_code == 200

        # Second transcription (should be cached)
        resp2 = client.post(f"/api/transcription/{video_id}/transcribe")
        assert resp2.status_code == 200
        assert "cached" in resp2.json()["message"].lower()

    def test_get_transcription_not_found(self):
        """GET transcription that doesn't exist should 404."""
        response = client.get("/api/transcription/nonexistent123")
        assert response.status_code == 404

    def test_get_transcription_after_transcribe(self):
        """GET transcription after processing should return results."""
        video_id = _upload_and_extract(client)

        # Transcribe first
        client.post(f"/api/transcription/{video_id}/transcribe")

        # Now GET
        response = client.get(f"/api/transcription/{video_id}")
        assert response.status_code == 200
        assert response.json()["result"]["video_id"] == video_id

    def test_status_no_transcript(self):
        """Status for untranscribed video should show has_transcription=False."""
        response = client.get("/api/transcription/nonexistent123/status")
        assert response.status_code == 200
        assert response.json()["has_transcription"] is False

    def test_status_after_transcribe(self):
        """Status after transcription should show has_transcription=True."""
        video_id = _upload_and_extract(client)
        client.post(f"/api/transcription/{video_id}/transcribe")

        response = client.get(f"/api/transcription/{video_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_transcription"] is True
        assert data["language"] is not None
