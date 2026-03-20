"""
speech_to_text.py
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
#  'base' is recommended for free-tier servers.
# ──────────────────────────────────────────────────────────────
_WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
_model = None  # Lazy-loaded on first use to save startup time


def _get_model() -> whisper.Whisper:
    """Lazily loads the Whisper model so startup stays fast."""
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {_WHISPER_MODEL_SIZE} ...")
        _model = whisper.load_model(_WHISPER_MODEL_SIZE)
        logger.info("Whisper model loaded successfully.")
    return _model


def ogg_to_wav(ogg_path: str) -> str:
    """
    Converts an .ogg audio file to .wav format.
    Whisper works best with 16kHz mono WAV audio.

    Args:
        ogg_path: Absolute path to the source .ogg file.

    Returns:
        Absolute path to the generated .wav file.
    """
    wav_path = ogg_path.replace(".ogg", ".wav")
    audio = AudioSegment.from_ogg(ogg_path)

    # Whisper prefers 16kHz mono audio — keeps file size small too.
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(wav_path, format="wav")

    logger.debug(f"Converted {ogg_path} → {wav_path}")
    return wav_path


def transcribe(audio_path: str) -> str:
    """
    Transcribes a WAV (or OGG) audio file using Whisper.

    Args:
        audio_path: Path to the audio file.

    Returns:
        Transcribed text string. Empty string on failure.
    """
    try:
        # Convert to WAV if we received an OGG file directly
        if audio_path.endswith(".ogg"):
            audio_path = ogg_to_wav(audio_path)

        model = _get_model()
        logger.info(f"Transcribing: {audio_path}")

        result = model.transcribe(
            audio_path,
            fp16=False,   # Disable half-precision; most CPUs don't support it
            language=None  # Auto-detect language
        )

        text = result.get("text", "").strip()
        logger.info(f"Transcription result: '{text}'")
        return text

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        return ""

    finally:
        # Clean up temporary audio files to save disk space
        for path in [audio_path, audio_path.replace(".wav", ".ogg")]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
