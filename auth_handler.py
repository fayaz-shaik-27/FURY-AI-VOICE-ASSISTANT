"""
auth_handler.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.
─────────────────────────────────────────────
Handles all Supabase interactions:
  - User sign up / sign in / sign out
  - Token validation (get_user)
  - Saving and loading per-user chat history
"""

import os
import logging
from supabase import create_client, Client
from supabase.client import ClientOptions

logger = logging.getLogger(__name__)

_pending_registrations = {}  # email -> {password, otp, expires}
_supabase_instance: Client | None = None


def _get_supabase_client(access_token: str = None) -> Client:
    """
    Safely retrieves or initializes a Supabase client.
    Prevents server crash at import time if environment variables are missing.
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")

    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_ANON_KEY is not set.")
        raise ValueError("Supabase credentials (SUPABASE_URL and SUPABASE_ANON_KEY) are not configured.")

    if access_token:
        opts = ClientOptions(headers={"Authorization": f"Bearer {access_token}"})
        return create_client(url, key, options=opts)

    global _supabase_instance
    if _supabase_instance is None:
        _supabase_instance = create_client(url, key)
    return _supabase_instance


# ── Auth helpers ─────────────────────────────────────────────────────────────


def email_exists(email: str) -> bool:
    """
    Safely checks if a user with the given email already exists in Supabase.
    Uses a database RPC function (check_email_exists) that queries auth.users directly.
    """
    try:
        client = _get_supabase_client()
        res = client.rpc("check_email_exists", {"lookup_email": email}).execute()
        return res.data is True
    except Exception as e:
        logger.warning(f"email_exists RPC check failed: {e}")
        return False


def sign_up(email: str, password: str) -> dict:
    """
    Registers a new user with Supabase Auth.
    Returns: { "user": {...}, "access_token": "..." }
    Raises: Exception with a user-friendly message on failure.
    """
    try:
        client = _get_supabase_client()
        res = client.auth.sign_up({"email": email, "password": password})
        if res.user is None:
            raise Exception("Sign-up failed. Please try again.")

        # Supabase security feature: if user already exists and confirm email is enabled,
        # it returns success but identities array is empty.
        if hasattr(res.user, 'identities') and res.user.identities is not None and len(res.user.identities) == 0:
            raise Exception("You are already signed up please use log in tab")

        return {
            "user": {"id": str(res.user.id), "email": res.user.email},
            "access_token": res.session.access_token if res.session else None,
        }
    except Exception as e:
        logger.error(f"sign_up error: {e}")
        err_str = str(e).lower()
        if "already registered" in err_str or "already exists" in err_str:
            raise Exception("You are already signed up please use log in tab")
        raise


def sign_in(email: str, password: str) -> dict:
    """
    Signs in an existing user.
    Returns: { "user": {...}, "access_token": "..." }
    Raises: Exception on bad credentials or network error.
    """
    try:
        client = _get_supabase_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.user is None or res.session is None:
            raise Exception("Invalid email or password.")
        return {
            "user": {"id": str(res.user.id), "email": res.user.email},
            "access_token": res.session.access_token,
        }
    except Exception as e:
        logger.error(f"sign_in error: {e}")
        raise


def sign_out(access_token: str) -> None:
    """Signs out the current user session."""
    try:
        client = _get_supabase_client(access_token)
        client.auth.sign_out()
    except Exception as e:
        logger.warning(f"sign_out error (non-critical): {e}")


def get_user(access_token: str) -> dict | None:
    """
    Validates an access token and returns user info.
    Returns: { "id": "...", "email": "..." } or None if invalid.
    """
    try:
        client = _get_supabase_client(access_token)
        res = client.auth.get_user(access_token)
        if res and res.user:
            return {"id": str(res.user.id), "email": res.user.email}
        return None
    except Exception as e:
        logger.warning(f"get_user error: {e}")
        return None


# ── Chat history helpers ──────────────────────────────────────────────────────


def save_message(access_token: str, user_id: str, role: str, message: str, session_id: str = None, session_title: str = None) -> None:
    """
    Saves a single chat message to Supabase for the given user.
    Uses the user's access token so RLS policies apply correctly.
    """
    try:
        user_client = _get_supabase_client(access_token)

        data = {
            "user_id": user_id,
            "role": role,
            "message": message,
        }
        if session_id:
            data["session_id"] = session_id
        if session_title:
            data["session_title"] = session_title

        user_client.table("chat_history").insert(data).execute()
    except Exception as e:
        logger.error(f"save_message error for user {user_id}: {e}")


def get_history(access_token: str, user_id: str, session_id: str = None) -> list[dict]:
    """
    Fetches the full chat history for the logged-in user from Supabase.
    If session_id is provided, only fetches messages for that session.
    """
    try:
        user_client = _get_supabase_client(access_token)

        query = (
            user_client.table("chat_history")
            .select("role, message, created_at, session_id, session_title")
            .eq("user_id", user_id)
        )

        if session_id:
            query = query.eq("session_id", session_id)

        res = query.order("created_at", desc=False).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"get_history error for user {user_id}: {e}")
        return []


def get_sessions(access_token: str, user_id: str) -> list[dict]:
    """
    Fetches a list of unique conversation sessions for the user.
    """
    try:
        user_client = _get_supabase_client(access_token)

        res = (
            user_client.table("chat_history")
            .select("session_id, session_title, message, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        if not res.data:
            return []

        sessions = {}
        for item in res.data:
            sid = item['session_id']
            if sid not in sessions:
                sessions[sid] = {
                    "session_id": sid,
                    "session_title": item.get('session_title') or "Untitled Chat",
                    "last_message": item['message'],
                    "created_at": item['created_at']
                }

        return list(sessions.values())
    except Exception as e:
        logger.error(f"get_sessions error: {e}")
        return []


def delete_history_session(access_token: str, user_id: str, session_id: str) -> None:
    """
    Deletes all messages associated with a specific session for the user.
    """
    try:
        user_client = _get_supabase_client(access_token)
        user_client.table("chat_history").delete().eq("user_id", user_id).eq("session_id", session_id).execute()
        logger.info(f"Deleted session {session_id} for user {user_id}")
    except Exception as e:
        logger.error(f"delete_history_session error: {e}")
        raise
