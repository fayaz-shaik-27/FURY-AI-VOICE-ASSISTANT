"""
ai_handler.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.
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
import re
import time
import logging
from collections import defaultdict
from datetime import datetime
from groq import Groq

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Groq client – uses GROQ_API_KEY from .env automatically
# ──────────────────────────────────────────────────────────────
def _get_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY is not configured in environment variables.")
    return Groq(api_key=key)

def _clean_response_text(text: str) -> str:
    """Strips internal reasoning <think>...</think> tags and extra whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if "<think>" in cleaned:
        parts = cleaned.split("<think>")
        cleaned = parts[0].strip()
    return cleaned

_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
_ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Fury AI")

# Fallback model chain – cycled through automatically on any transient error
# (rate limits, output_parse_failed, overloaded, etc.)
_FALLBACK_MODELS_TEXT = ["openai/gpt-oss-20b", "groq/compound", "groq/compound-mini"]
_FALLBACK_MODELS_VISION = [os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")]  # vision only has one option

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
_MAX_HISTORY_PAIRS = 4  # 4 pairs = 8 messages kept (keeps token footprint low to avoid 429 rate limits)


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

def get_history(session_id: str) -> list[dict]:
    """Returns the stored conversation history for a specific session."""
    return _memory[session_id]


def add_to_history(session_id: str, role: str, content: str) -> None:
    """
    Appends a message to the session's history and trims older messages.
    """
    _memory[session_id].append({"role": role, "content": content})

    # Trim: keep only the most recent N exchanges (2 msgs per exchange)
    max_messages = _MAX_HISTORY_PAIRS * 2
    if len(_memory[session_id]) > max_messages:
        _memory[session_id] = _memory[session_id][-max_messages:]


def load_history_to_memory(session_id: str, messages: list[dict]) -> None:
    """
    Pre-populates the in-memory context from the database history.
    Messages should be a list of {"role": "user"|"assistant", "message": "..."}.
    """
    if session_id in _memory and len(_memory[session_id]) > 0:
        return # Already loaded or active
    
    formatted = []
    for m in messages:
        # Convert DB 'assistant' role to AI handler's 'assistant'
        role = 'assistant' if m['role'] in ['assistant', 'ai'] else 'user'
        formatted.append({"role": role, "content": m['message']})
    
    _memory[session_id] = formatted
    logger.info(f"Loaded {len(formatted)} messages into memory for session {session_id}")


def clear_history(session_id: str) -> None:
    """Wipes conversation memory for a session."""
    _memory[session_id] = []
    logger.info(f"Memory cleared for session {session_id}.")


def generate_session_title(user_text: str) -> str:
    """
    Generates a very short (3-5 word) title for the conversation based on the first input.
    """
    try:
        prompt = f"Generate a 3 to 4 word title for a conversation that starts with: '{user_text}'. Return ONLY the title, no quotes or punctuation."
        response = _get_client().chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.5
        )
        title = _clean_response_text(response.choices[0].message.content)
        # Clean up in case LLM added quotes or extra formatting
        title = title.replace('"', '').replace("'", "").split("\n")[0].strip()
        return title or "New Conversation"
    except Exception as e:
        logger.error(f"Title generation failed: {e}")
        return "New Conversation"


# ──────────────────────────────────────────────────────────────
#  Main AI response function
# ──────────────────────────────────────────────────────────────

_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")

def generate_response(session_id: str, user_text: str, image_data: str = None) -> str:
    """
    Generates an AI response using Groq LLM, with full conversation memory.
    Supports optional image data (base64 string) for vision tasks.
    """
    intent = detect_intent(user_text)
    logger.info(f"Session {session_id} | Intent: {intent} | Input: '{user_text[:80]}' | Image: {'Yes' if image_data else 'No'}")

    if intent == "creator":
        creator_reply = "My creator is Fayaz Ahmed, His screen name is Fury So he named me Fury"
        add_to_history(session_id, "user", user_text)
        add_to_history(session_id, "assistant", creator_reply)
        return creator_reply

    # Build the full message list for the API call
    # We don't store the image in history to keep it lean, but we use it for the current turn
    
    current_model = _VISION_MODEL if image_data else _MODEL
    
    if image_data:
        # Groq vision models expect a specific format for multimodal content
        current_user_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }
                }
            ]
        }
    else:
        current_user_msg = {"role": "user", "content": user_text}

    # Store user's message in memory (only text part for history)
    add_to_history(session_id, "user", user_text)

    # Build history (excluding current turn which we handle specially if it has an image)
    raw_history = get_history(session_id)[:-1] # All except the one we just added
    
    # Filter out old fallback error messages that contaminate vision context
    history = []
    for m in raw_history:
        if m.get("role") == "assistant":
            c_lower = (m.get("content") or "").lower()
            if "hiccup" in c_lower or ("see" in c_lower and "image" in c_lower) or ("view" in c_lower and "image" in c_lower):
                continue
        history.append(m)

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + history + [current_user_msg]

    try:
        response = _get_client().chat.completions.create(
            model=current_model,
            messages=messages,
            top_p=0.9,
            max_tokens=2500 if image_data else 300,  # Vision models (qwen) need large budget to finish <think> + answer
        )

        reply = _clean_response_text(response.choices[0].message.content)
        
        # If vision model returned empty (reasoning tokens exhausted), retry with more budget
        if not reply and image_data:
            logger.warning(f"Vision model returned empty for session {session_id}, retrying with higher token budget...")
            try:
                retry_response = _get_client().chat.completions.create(
                    model=current_model,
                    messages=messages,
                    max_tokens=3000,
                    temperature=0.5,
                )
                reply = _clean_response_text(retry_response.choices[0].message.content)
            except Exception as retry_err:
                logger.warning(f"Vision retry failed: {retry_err}")

        if not reply and image_data:
            reply = "I see the image you uploaded! What specific details or questions do you have about it?"

        logger.info(f"AI reply for session {session_id}: '{reply[:80]}'")

        # Store assistant's reply in memory for next turn
        add_to_history(session_id, "assistant", reply)

        # ── Image context injection ────────────────────────────────────────────
        # After a successful image analysis, inject the AI's description as a
        # hidden [Image context] note so follow-up questions (without image data)
        # still have full context of what was in the image.
        if image_data and reply and "I see the image you uploaded" not in reply:
            context_note = f"[Image context from previous turn: {reply}]"
            add_to_history(session_id, "assistant", context_note)

        return reply

    except Exception as e:
        err_str = str(e).lower()

        # ── Unified Transient Error Retry ─────────────────────────────────────
        # Catches: 429 rate limit, 400 output_parse_failed, 503 overloaded, etc.
        # Cycles through the fallback model list with increasing wait times.
        is_transient = (
            "429" in err_str
            or "rate limit" in err_str
            or "rate_limit_exceeded" in err_str
            or "output_parse_failed" in err_str
            or "overloaded" in err_str
            or "parsing failed" in err_str
            or ("400" in err_str and "failed_generation" in err_str)
        )
        if is_transient:
            fallback_list = _FALLBACK_MODELS_VISION if image_data else _FALLBACK_MODELS_TEXT
            logger.warning(
                f"Transient Groq error for session {session_id}: {str(e)[:120]}. "
                f"Retrying across {len(fallback_list)} fallback model(s)..."
            )
            for attempt, fb_model in enumerate(fallback_list, start=1):
                time.sleep(1.0 * attempt)  # 1s, 2s, 3s progressive back-off
                try:
                    response = _get_client().chat.completions.create(
                        model=fb_model,
                        messages=messages,
                        max_tokens=800 if image_data else 150,
                        temperature=0.7,
                    )
                    reply = _clean_response_text(response.choices[0].message.content)
                    if not reply and image_data:
                        reply = "I see the image you uploaded! What specific details or questions do you have about it?"
                    if reply:
                        logger.info(f"Recovered with fallback model '{fb_model}' (attempt {attempt})")
                        add_to_history(session_id, "assistant", reply)
                        return reply
                except Exception as retry_err:
                    logger.warning(f"Fallback attempt {attempt} ({fb_model}) failed: {retry_err}")

        # ── Fallback: multimodal → plain-text retry ───────────────────────────
        if image_data and "content must be a string" in err_str:
            logger.info("Retrying vision prompt as plain text string...")
            try:
                fallback_msg = {"role": "user", "content": f"{user_text} [Note: User attached an image file]"}
                messages[-1] = fallback_msg
                response = _get_client().chat.completions.create(
                    model=current_model,
                    messages=messages,
                    max_tokens=150,
                    temperature=0.75,
                )
                reply = _clean_response_text(response.choices[0].message.content)
                add_to_history(session_id, "assistant", reply)
                return reply
            except Exception as retry_err:
                logger.error(f"Vision plain-text retry failed: {retry_err}")

        logger.error(f"LLM call failed for session {session_id}: {e}", exc_info=True)
        # Final friendly fallback so the bot doesn't go silent on errors
        return "I'm sorry, I ran into a little hiccup. Could you try saying that again?"
