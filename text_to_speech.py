"""
text_to_speech.py
─────────────────
Converts a text string into a Telegram-compatible .ogg voice file
using Google Text-to-Speech (gTTS) — completely free, no API key needed.

Flow:
  text  →  gTTS generates .mp3  →  pydub converts to .ogg (opus)  →  Telegram reads it
"""

import os
import logging
import hashlib
from gtts import gTTS
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Directory for temporary audio output files.
#  Will be created automatically on first use.
# ──────────────────────────────────────────────────────────────
_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio_output")
os.makedirs(_AUDIO_DIR, exist_ok=True)


def _unique_path(text: str, extension: str) -> str:
    """
    Generates a unique file path based on a hash of the text.
    This prevents file name collisions for concurrent users.
    """
    text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
    return os.path.join(_AUDIO_DIR, f"response_{text_hash}.{extension}")


def synthesize(text: str, lang: str = "en") -> str | None:
    """
    Converts text to a .ogg voice file for Telegram.

    Telegram voice messages require OGG-Opus format.
    gTTS produces MP3, which we convert with pydub/ffmpeg.

    Args:
        text: The text to synthesize.
        lang: Language code (default 'en' for English).

    Returns:
        Absolute path to the .ogg file, or None on failure.
    """
    try:
        mp3_path = _unique_path(text, "mp3")
        ogg_path = _unique_path(text, "ogg")

        # Step 1: Generate MP3 with gTTS
        logger.info(f"Synthesizing TTS for text: '{text[:60]}...'")
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(mp3_path)
        logger.debug(f"MP3 saved: {mp3_path}")

        # Step 2: Convert MP3 → OGG (Opus codec required by Telegram)
        audio = AudioSegment.from_mp3(mp3_path)
        audio.export(ogg_path, format="ogg", codec="libopus")
        logger.debug(f"OGG saved: {ogg_path}")

        # Clean up intermediate MP3
        os.remove(mp3_path)

        return ogg_path

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}", exc_info=True)
        return None


def cleanup(file_path: str) -> None:
    """
    Deletes a temporary audio file after it has been sent.

    Args:
        file_path: Path to remove.
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up: {file_path}")
    except OSError as e:
        logger.warning(f"Could not delete {file_path}: {e}")
