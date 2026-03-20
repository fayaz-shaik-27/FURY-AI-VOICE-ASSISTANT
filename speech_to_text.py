"""
speech_to_text.py
© 2024 Fayaz Ahmed Shaik. All rights reserved.
─────────────────
Converts a Telegram .ogg voice file into a plain-text transcript
using OpenAI Whisper (runs fully locally – no API key needed).

Flow:
  .ogg file  →  pydub converts to .wav  →  Whisper transcribes  →  text
"""

import os
import logging
import whisper
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Load the Whisper model once at import time.
#  Model size comes from .env (tiny/base/small/medium/large).
#  'tiny' is recommended for free-tier servers (uses ~150MB RAM).
#  'base' uses ~500MB RAM and may crash on Render Free Tier.
# ──────────────────────────────────────────────────────────────
_WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "tiny")
_model = None  # Lazy-loaded on first use to save startup time


def _get_model() -> whisper.Whisper:
    """Lazily loads the Whisper model so startup stays fast."""
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {_WHISPER_MODEL_SIZE} ...")
        _model = whisper.load_model(_WHISPER_MODEL_SIZE)
        logger.info("Whisper model loaded successfully.")
    return _model


def _convert_to_wav(audio_path: str) -> str:
    """
    Converts any browser audio format to 16kHz mono WAV.
    Handles: .ogg, .webm, .mp4, .m4a, .wav
    """
    wav_path = os.path.splitext(audio_path)[0] + "_converted.wav"
    ext = os.path.splitext(audio_path)[1].lower()

    try:
        if ext in (".ogg",):
            audio = AudioSegment.from_ogg(audio_path)
        elif ext in (".webm", ".mp4", ".m4a"):
            audio = AudioSegment.from_file(audio_path, format=ext.lstrip("."))
        elif ext == ".wav":
            return audio_path  # Already WAV
        else:
            audio = AudioSegment.from_file(audio_path)  # Let pydub auto-detect

        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_path, format="wav")
        logger.debug(f"Converted {audio_path} → {wav_path}")
        return wav_path
    except Exception as e:
        logger.warning(f"pydub conversion failed ({e}), passing raw file to Whisper")
        return audio_path  # Let Whisper try natively with ffmpeg


# Keep old name for backward compatibility
def ogg_to_wav(ogg_path: str) -> str:
    return _convert_to_wav(ogg_path)


def transcribe(audio_path: str) -> str:
    """
    Transcribes any audio file using Whisper.
    Handles browser formats: .webm, .ogg, .mp4, .wav
    """
    wav_path = None
    try:
        # Convert to WAV for best Whisper accuracy
        original_ext = os.path.splitext(audio_path)[1].lower()
        if original_ext != ".wav":
            wav_path = _convert_to_wav(audio_path)
        else:
            wav_path = audio_path

        model = _get_model()
        logger.info(f"Transcribing: {wav_path}")

        result = model.transcribe(
            wav_path,
            fp16=False,    # Disable half-precision; most CPUs don't support it
            language=None  # Auto-detect language
        )

        text = result.get("text", "").strip()
        logger.info(f"Transcription result: '{text[:80]}'")
        return text

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        return ""

    finally:
        # Clean up converted WAV (but not if it's the original)
        if wav_path and wav_path != audio_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass


# Alias used by api.py
transcribe_voice = transcribe
