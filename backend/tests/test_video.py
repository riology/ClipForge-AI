"""Tests for video upload, validation, metadata, and audio extraction."""

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.video_service import (
    VideoValidationError,
    validate_video_file,
    extract_metadata,
    extract_audio,
    _format_duration,
)

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
TEST_VIDEO_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module", autouse=True)
def create_test_video():
    """Generate a tiny 3-second test video using FFmpeg (runs once per module)."""
    TEST_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    test_video = TEST_VIDEO_DIR / "test_video.mp4"

    if not test_video.exists():
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:size=320x240:duration=3:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264",  "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k",
            "-shortest",
            str(test_video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"Failed to create test video: {result.stderr}"

    yield test_video

    # Cleanup is optional; leaving fixtures around speeds up re-runs.


def get_test_video_path() -> Path:
    return TEST_VIDEO_DIR / "test_video.mp4"


# ===========================================================================
# Unit tests — validation
# ===========================================================================
class TestValidation:
    def test_valid_mp4(self):
        validate_video_file("my_video.mp4", 1024)  # should not raise

    def test_valid_mkv(self):
        validate_video_file("recording.mkv", 1024)

    def test_valid_mov(self):
        validate_video_file("clip.MOV", 1024)  # case-insensitive

    def test_valid_webm(self):
        validate_video_file("stream.webm", 1024)

    def test_reject_unsupported_format(self):
        with pytest.raises(VideoValidationError, match="Unsupported"):
            validate_video_file("document.avi", 1024)

    def test_reject_non_video(self):
        with pytest.raises(VideoValidationError, match="Unsupported"):
            validate_video_file("notes.txt", 1024)

    def test_reject_empty_file(self):
        with pytest.raises(VideoValidationError, match="empty"):
            validate_video_file("video.mp4", 0)

    def test_reject_oversized_file(self):
        with pytest.raises(VideoValidationError, match="too large"):
            validate_video_file("huge.mp4", 6 * 1024 * 1024 * 1024)


# ===========================================================================
# Unit tests — helpers
# ===========================================================================
class TestHelpers:
    def test_format_duration_short(self):
        assert _format_duration(45) == "00:45"

    def test_format_duration_minutes(self):
        assert _format_duration(125) == "02:05"

    def test_format_duration_hours(self):
        assert _format_duration(3661) == "01:01:01"


# ===========================================================================
# Unit tests — metadata extraction (uses real FFmpeg)
# ===========================================================================
class TestMetadata:
    def test_extract_metadata(self):
        video = get_test_video_path()
        meta = extract_metadata(video)

        assert meta["width"] == 320
        assert meta["height"] == 240
        assert meta["codec"] == "h264"
        assert meta["duration_seconds"] >= 2.5  # ~3 seconds
        assert meta["file_size_bytes"] > 0
        assert meta["fps"] is not None and meta["fps"] > 0


# ===========================================================================
# Unit tests — audio extraction (uses real FFmpeg)
# ===========================================================================
class TestAudioExtraction:
    def test_extract_audio(self, tmp_path):
        """Extract audio from test video and verify the WAV file."""
        import app.services.video_service as vs

        # Temporarily override storage path
        original = vs.settings.STORAGE_DIR
        vs.settings.STORAGE_DIR = str(tmp_path)

        try:
            video = get_test_video_path()
            result = extract_audio(video, "test_audio_001")

            assert result["audio_filename"] == "test_audio_001.wav"
            assert result["audio_size_bytes"] > 0
            assert result["duration_seconds"] >= 2.5

            # Verify actual WAV file
            audio_file = tmp_path / "audio" / "test_audio_001.wav"
            assert audio_file.exists()
        finally:
            vs.settings.STORAGE_DIR = original


# ===========================================================================
# API integration tests
# ===========================================================================
class TestUploadEndpoint:
    def test_upload_valid_video(self):
        video = get_test_video_path()
        with open(video, "rb") as f:
            response = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Video uploaded successfully."
        assert "video_id" in data
        assert data["metadata"]["width"] == 320
        assert data["metadata"]["height"] == 240
        assert data["metadata"]["original_filename"] == "test.mp4"

    def test_upload_invalid_format(self):
        response = client.post(
            "/api/videos/upload",
            files={"file": ("test.txt", b"not a video", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]

    def test_upload_empty_file(self):
        response = client.post(
            "/api/videos/upload",
            files={"file": ("test.mp4", b"", "video/mp4")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"]


class TestMetadataEndpoint:
    def test_metadata_not_found(self):
        response = client.get("/api/videos/nonexistent123/metadata")
        assert response.status_code == 404

    def test_metadata_for_uploaded_video(self):
        # First upload
        video = get_test_video_path()
        with open(video, "rb") as f:
            upload = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        video_id = upload.json()["video_id"]

        # Then get metadata
        response = client.get(f"/api/videos/{video_id}/metadata")
        assert response.status_code == 200
        assert response.json()["codec"] == "h264"


class TestAudioExtractionEndpoint:
    def test_extract_audio_not_found(self):
        response = client.post("/api/videos/nonexistent123/extract-audio")
        assert response.status_code == 404

    def test_extract_audio_success(self):
        # Upload first
        video = get_test_video_path()
        with open(video, "rb") as f:
            upload = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        video_id = upload.json()["video_id"]

        # Extract audio
        response = client.post(f"/api/videos/{video_id}/extract-audio")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Audio extracted successfully."
        assert data["audio_filename"].endswith(".wav")
        assert data["audio_size_bytes"] > 0


class TestStatusEndpoint:
    def test_status_not_found(self):
        response = client.get("/api/videos/nonexistent123/status")
        assert response.status_code == 404

    def test_status_after_upload(self):
        video = get_test_video_path()
        with open(video, "rb") as f:
            upload = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        video_id = upload.json()["video_id"]

        response = client.get(f"/api/videos/{video_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_video"] is True
        assert data["metadata"] is not None
