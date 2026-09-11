"""Local transcription service using faster-whisper.

Runs entirely on CPU (or GPU if available). No API keys or cloud services.
Model is loaded once and cached for reuse across transcriptions.
"""

import json
import logging
import time
from pathlib import Path
from threading import Lock

from app.core.config import settings

logger = logging.getLogger("clipforge.transcription")

# ---------------------------------------------------------------------------
# Module-level model cache (loaded once, reused)
# ---------------------------------------------------------------------------
_model = None
_model_lock = Lock()
_loaded_model_name = None


class TranscriptionError(Exception):
    """Raised when transcription fails."""


def _get_model():
    """Load or return the cached faster-whisper model.

    Thread-safe: only one thread can load the model at a time.
    """
    global _model, _loaded_model_name

    target_model = settings.WHISPER_MODEL

    with _model_lock:
        if _model is not None and _loaded_model_name == target_model:
            return _model

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError(
                "faster-whisper is not installed. "
                "Run: pip install faster-whisper"
            )

        logger.info(
            "Loading Whisper model '%s' (device=%s, compute_type=%s)...",
            target_model,
            settings.WHISPER_DEVICE,
            settings.WHISPER_COMPUTE_TYPE,
        )

        load_start = time.time()
        try:
            _model = WhisperModel(
                target_model,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
        except Exception as e:
            raise TranscriptionError(f"Failed to load Whisper model: {e}")

        _loaded_model_name = target_model
        load_time = time.time() - load_start
        logger.info("Whisper model loaded in %.1f seconds.", load_time)

        return _model


# ---------------------------------------------------------------------------
# Core transcription
# ---------------------------------------------------------------------------
def transcribe_audio(audio_path: Path, language: str | None = None) -> dict:
    """Transcribe an audio file using faster-whisper.

    Args:
        audio_path: Path to a WAV audio file.
        language: Optional language code (e.g. 'en'). Auto-detects if None.

    Returns:
        Dict with keys: language, language_probability, duration_seconds,
        segment_count, segments (list of {start, end, text}), full_text.

    Raises:
        TranscriptionError: If transcription fails.
    """
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    model = _get_model()

    logger.info("Starting transcription: %s (language=%s)", audio_path.name, language or "auto")
    start_time = time.time()

    try:
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            vad_filter=True,       # Filter out silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )
    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}")

    # Collect segments
    segments = []
    for segment in segments_iter:
        segments.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
        })

    elapsed = time.time() - start_time
    full_text = " ".join(s["text"] for s in segments)

    logger.info(
        "Transcription complete: %d segments, %.1f sec audio, %.1f sec processing, language=%s (%.0f%%)",
        len(segments),
        info.duration,
        elapsed,
        info.language,
        info.language_probability * 100,
    )

    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration_seconds": round(info.duration, 2),
        "segment_count": len(segments),
        "segments": segments,
        "full_text": full_text,
    }


# ---------------------------------------------------------------------------
# Transcript persistence
# ---------------------------------------------------------------------------
def save_transcript(video_id: str, transcript_data: dict) -> Path:
    """Save a transcript to the storage directory as JSON.

    Returns the path to the saved transcript file.
    """
    transcript_dir = settings.storage_path / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = transcript_dir / f"{video_id}.json"
    transcript_path.write_text(
        json.dumps(transcript_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Transcript saved: %s (%d segments)", transcript_path.name, transcript_data["segment_count"])
    return transcript_path


def load_transcript(video_id: str) -> dict | None:
    """Load a previously saved transcript.

    Returns the transcript dict or None if not found.
    """
    transcript_path = settings.storage_path / "transcripts" / f"{video_id}.json"
    if not transcript_path.exists():
        return None

    try:
        return json.loads(transcript_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load transcript %s: %s", video_id, e)
        return None


def has_transcript(video_id: str) -> bool:
    """Check if a transcript exists for the given video."""
    transcript_path = settings.storage_path / "transcripts" / f"{video_id}.json"
    return transcript_path.exists()
