"""
speech_to_text.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.
─────────────────
Converts browser audio into a plain-text transcript using the
Groq Whisper API (cloud-based, no local PyTorch needed).

This keeps the memory footprint tiny — perfect for free-tier hosting.
Groq is free and processes audio in under 1 second.
"""

import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

def _get_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY is not configured in environment variables.")
    return Groq(api_key=key)

# Groq supports: whisper-large-v3, whisper-large-v3-turbo, distil-whisper-large-v3-en
_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")


def transcribe(audio_path: str) -> str:
    """
    Transcribes an audio file using the Groq Whisper API.
    Handles browser formats: .webm, .ogg, .mp4, .wav

    Args:
        audio_path: Path to the audio file to transcribe.

    Returns:
        Transcribed text string, or empty string on failure.
    """
    try:
        logger.info(f"Transcribing via Groq Whisper: {audio_path}")

        client = _get_client()
        with open(audio_path, "rb") as audio_file:
            filename = os.path.basename(audio_path)
            transcription = client.audio.transcriptions.create(
                file=(filename, audio_file.read()),
                model=_WHISPER_MODEL,
                response_format="text",
            )

        # When response_format="text", Groq returns the string directly
        text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
        logger.info(f"Transcription result: '{text[:80]}'")
        return text

    except Exception as e:
        logger.error(f"Groq Whisper transcription failed: {e}", exc_info=True)
        return ""


# Alias used by api.py
transcribe_voice = transcribe
