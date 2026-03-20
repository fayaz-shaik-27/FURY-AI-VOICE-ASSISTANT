"""
ai_handler.py
© 2024 Fayaz Ahmed Shaik. All rights reserved.
─────────────
Handles all AI intelligence:
  - Maintains per-user conversation memory (in-memory dict)
  - Detects basic intent (greeting, question, farewell, etc.)
  - Sends prompts to Groq LLM and returns the response
  - Applies a friendly, human-like assistant personality

All free – uses Groq's generous free tier (no credit card required).
Sign up at: https://console.groq.com/
"""

import os
import logging
from collections import defaultdict
from datetime import datetime
from groq import Groq

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Groq client – uses GROQ_API_KEY from .env automatically
# ──────────────────────────────────────────────────────────────
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
_ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Fury AI")

# ──────────────────────────────────────────────────────────────
#  System prompt – personality & instructions for the LLM
#  Injected at the start of every conversation.
# ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = f"""
You are {_ASSISTANT_NAME}, a warm, friendly, and highly intelligent AI voice assistant.
Your job is to help users via voice and text messages – just like a helpful personal assistant.

Personality guidelines:
- Be conversational, empathetic, and concise (keep replies under 3 sentences when possible).
- Use natural spoken language – avoid bullet points, markdown, or headers.
- Show personality: be warm and occasionally witty, but always professional.
- If you don't know something, say so honestly rather than making things up.
- Adapt your tone to the user's mood (if they sound stressed, be calming).

Important: Your replies will be converted to audio, so respond as you would speak – naturally.
Today's date is {datetime.now().strftime("%A, %B %d, %Y")}.
""".strip()

# ──────────────────────────────────────────────────────────────
#  Per-user conversation memory
#  Key: platform user_id (int or str)
#  Value: list of {"role": "user"|"assistant", "content": str}
#
#  Note: This is in-memory only. Memory is lost on bot restart.
#  For persistence, swap this dict with a SQLite/Redis store.
# ──────────────────────────────────────────────────────────────
_memory: dict[str | int, list[dict]] = defaultdict(list)

# How many past messages to keep per user (controls context window)
_MAX_HISTORY_PAIRS = 10  # 10 pairs = 20 messages kept


# ──────────────────────────────────────────────────────────────
#  Intent Detection  (rule-based, no ML needed)
# ──────────────────────────────────────────────────────────────

_INTENT_PATTERNS: dict[str, list[str]] = {
    "creator": ["who is your creator", "who created you", "who made you", "who is your developer"],
    "greeting": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy", "sup"],
    "farewell": ["bye", "goodbye", "see you", "take care", "later", "ciao", "gotta go"],
    "gratitude": ["thank", "thanks", "thank you", "appreciate", "cheers"],
    "help": ["help", "can you", "could you", "assist", "support", "i need"],
    "question": ["what", "when", "where", "why", "how", "who", "which", "?"],
    "affirmation": ["yes", "yeah", "yep", "sure", "okay", "ok", "absolutely", "of course"],
    "negation": ["no", "nope", "nah", "not really", "i don't think so"],
}


def detect_intent(text: str) -> str:
    """
    Returns the dominant intent category of the user's message.
    Uses simple keyword matching — no ML required.

    Args:
        text: Raw transcribed user input.

    Returns:
        Intent label (e.g., 'greeting', 'question', 'unknown').
    """
    text_lower = text.lower()
    for intent, keywords in _INTENT_PATTERNS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "unknown"


# ──────────────────────────────────────────────────────────────
#  Memory helpers
# ──────────────────────────────────────────────────────────────

def get_history(user_id: str | int) -> list[dict]:
    """Returns the stored conversation history for a user."""
    return _memory[user_id]


def add_to_history(user_id: str | int, role: str, content: str) -> None:
    """
    Appends a message to the user's history and trims older messages
    to stay within the _MAX_HISTORY_PAIRS limit.
    """
    _memory[user_id].append({"role": role, "content": content})

    # Trim: keep only the most recent N exchanges (2 msgs per exchange)
    max_messages = _MAX_HISTORY_PAIRS * 2
    if len(_memory[user_id]) > max_messages:
        _memory[user_id] = _memory[user_id][-max_messages:]


def clear_history(user_id: str | int) -> None:
    """Wipes conversation memory for a user. Useful for /reset command."""
    _memory[user_id] = []
    logger.info(f"Memory cleared for user {user_id}.")


# ──────────────────────────────────────────────────────────────
#  Main AI response function
# ──────────────────────────────────────────────────────────────

def generate_response(user_id: str | int, user_text: str) -> str:
    """
    Generates an AI response using Groq LLM, with full conversation memory.

    Steps:
      1. Detect user intent (for logging/future routing)
      2. Add user message to memory
      3. Build message list: system + history
      4. Call Groq API
      5. Save assistant response to memory
      6. Return the response text

    Args:
        user_id: Telegram user ID (used as memory key).
        user_text: Transcribed speech from the user.

    Returns:
        AI-generated response string.
    """
    intent = detect_intent(user_text)
    logger.info(f"User {user_id} | Intent: {intent} | Input: '{user_text[:80]}'")

    if intent == "creator":
        creator_reply = "My creator is Fayaz Ahmed, His screen name is Fury So he named me Fury"
        add_to_history(user_id, "user", user_text)
        add_to_history(user_id, "assistant", creator_reply)
        return creator_reply

    # Store user's message in memory
    add_to_history(user_id, "user", user_text)

    # Build the full message list for the API call
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + get_history(user_id)

    try:
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=messages,
            max_tokens=300,       # Keep responses concise for voice
            temperature=0.75,     # Balanced creativity vs. consistency
            top_p=0.9,
        )

        reply = response.choices[0].message.content.strip()
        logger.info(f"AI reply for user {user_id}: '{reply[:80]}'")

        # Store assistant's reply in memory for next turn
        add_to_history(user_id, "assistant", reply)

        return reply

    except Exception as e:
        logger.error(f"LLM call failed for user {user_id}: {e}", exc_info=True)
        # Friendly fallback so the bot doesn't go silent on errors
        return "I'm sorry, I ran into a little hiccup. Could you try saying that again?"
