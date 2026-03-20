"""
main.py
───────
Entry point for the AI Voice Assistant Telegram bot.

Handles:
  - /start       → Welcome message
  - /reset        → Clears conversation memory for the user
  - Voice messages → Full STT → LLM → TTS pipeline
  - Text messages  → LLM → TTS pipeline (text input also supported)

Dependencies: python-telegram-bot v21, whisper, gTTS, groq, pydub
Run:  python main.py
"""

import os
import logging
import tempfile
import os
import logging
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Load .env variables BEFORE importing other modules that read os.getenv()
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import speech_to_text as stt
import text_to_speech as tts
import ai_handler as ai

# ──────────────────────────────────────────────────────────────
#  Logging setup — INFO to console, useful for debugging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

async def _send_voice_reply(update: Update, response_text: str) -> None:
    """
    Converts response_text to a .ogg file and sends it as a Telegram voice message.
    Falls back to plain text if TTS fails.
    """
    ogg_path = tts.synthesize(response_text)

    if ogg_path:
        with open(ogg_path, "rb") as audio_file:
            await update.message.reply_voice(voice=audio_file)
        tts.cleanup(ogg_path)
    else:
        # Graceful fallback: send text if TTS fails
        logger.warning("TTS failed – falling back to text reply.")
        await update.message.reply_text(
            f"🔇 (Voice synthesis failed)\n\n{response_text}"
        )


async def _send_thinking_indicator(update: Update) -> None:
    """Sends a 'typing…' action so the user knows the bot is processing."""
    await update.message.chat.send_action(action="record_voice")


# ──────────────────────────────────────────────────────────────
#  Command Handlers
# ──────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the custom voice greeting as soon as the user starts the bot."""
    user = update.effective_user
    greeting_text = (
        "I am fayaz's voice assistant. Sorry for not lifting the call, "
        "you can leave a voice mail after the beep."
    )
    
    logger.info(f"Start command from user {user.id}. Sending voicemail greeting.")
    
    # Send the voice greeting automatically
    await _send_voice_reply(update, greeting_text)
    
    # Also send a small hint text for clarity
    await update.message.reply_text(
        "🎙️ *Voicemail Mode Active*\n"
        "Please send your voice message now.",
        parse_mode="Markdown"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the conversation memory for this user."""
    user_id = update.effective_user.id
    ai.clear_history(user_id)
    await update.message.reply_text(
        "🧹 Memory cleared! Let's start fresh — say hello anytime."
    )

async def cmd_voicemails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists the most recent stored voicemails."""
    voicemails = ai.get_voicemails(15)
    if not voicemails:
        await update.message.reply_text("📭 Your voicemail box is empty.")
        return

    text = "📂 *Recent Voicemails:*\n\n"
    for vid, username, transcript, timestamp in voicemails:
        user_display = username if username else "Unknown Caller"
        # Convert timestamp to a nicer format if needed, but SQLite default is fine
        text += f"🆔 {vid} | 👤 *{user_display}*\n"
        text += f"📅 {timestamp}\n"
        text += f"💬 \"{transcript}\"\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ──────────────────────────────────────────────────────────────
#  Voice Message Handler  (the main pipeline)
# ──────────────────────────────────────────────────────────────

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Full voice pipeline:
      1. Download .ogg file from Telegram servers
      2. Transcribe with Whisper (STT)
      3. Generate AI response (LLM + memory)
      4. Synthesize reply as audio (TTS)
      5. Send voice message back to user
    """
    user = update.effective_user
    logger.info(f"Voice message received from user {user.id} (@{user.username})")

    await _send_thinking_indicator(update)

    # ── Step 1: Download the voice file ──────────────────────
    voice_file = await update.message.voice.get_file()

    # Store in a temp directory; auto-cleaned when the 'with' block exits
    with tempfile.TemporaryDirectory() as tmp_dir:
        ogg_path = os.path.join(tmp_dir, "voice.ogg")
        await voice_file.download_to_drive(ogg_path)
        logger.info(f"Downloaded voice file to: {ogg_path}")

        # ── Step 2: Speech → Text ─────────────────────────────
        transcript = stt.transcribe(ogg_path)

    if not transcript:
        await update.message.reply_text(
            "🔇 I couldn't make out what you said. Could you try again, a bit louder?"
        )
        return

    logger.info(f"Transcript for user {user.id}: '{transcript}'")

    # Show what the bot heard (optional transparency feature)
    await update.message.reply_text(f"🎙️ _I heard:_ \"{transcript}\"", parse_mode="Markdown")

    # ── Step 3: Generate AI response ─────────────────────────
    response_text = ai.generate_response(user.id, transcript)

    # ── Step 3.5: Save to Voicemail Box (Persistent Storage) ──
    ai.save_voicemail(user.id, user.username, transcript)

    # ── Steps 4 & 5: TTS + Send voice reply ──────────────────
    await _send_voice_reply(update, response_text)


# ──────────────────────────────────────────────────────────────
#  Text Message Handler  (bonus: support typed input too)
# ──────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles plain text messages.
    Sends an AI response as a voice message (same pipeline, skips STT).
    """
    user = update.effective_user
    user_text = update.message.text.strip()

    if not user_text:
        return

    logger.info(f"Text message from user {user.id}: '{user_text[:80]}'")
    await _send_thinking_indicator(update)

    # Generate AI response
    response_text = ai.generate_response(user.id, user_text)

    # Reply with voice audio
    await _send_voice_reply(update, response_text)


# ──────────────────────────────────────────────────────────────
#  Error Handler
# ──────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs unexpected errors without crashing the bot."""
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)

    # Attempt to notify the user if we have a valid update
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ Something went wrong on my end. Please try again in a moment!"
        )

# ──────────────────────────────────────────────────────────────
#  Health Check Server (For Cloud Deployment)
# ──────────────────────────────────────────────────────────────

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP server to satisfy Render/Railway health checks."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_server():
    """Starts the health check server on port 8080 (or PORT env var)."""
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server running on port {port}")
    server.serve_forever()


# ──────────────────────────────────────────────────────────────
#  Application Bootstrap
# ──────────────────────────────────────────────────────────────

def main() -> None:
    """Builds the Telegram application and starts polling for updates."""

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set! "
            "Copy .env.sample to .env and fill in your token."
        )

    logger.info("🤖 Starting AI Voice Assistant bot...")

    app = Application.builder().token(token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("voicemails", cmd_voicemails))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    # run_polling: keeps the bot alive and handles reconnections automatically
    # Start health check server in a separate thread
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
