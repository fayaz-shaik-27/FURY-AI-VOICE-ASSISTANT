"""
FastAPI backend for Fury AI Voice Assistant web interface.
© 2026 Fayaz Ahmed Shaik. All rights reserved.
IMPORTANT: load_dotenv() MUST run before importing ai_handler/tts/stt
           because those modules read env vars at import time.
"""
import os
import uuid
import logging
import base64
import random
# ── Load env variables FIRST before any other local imports ──────────────────

from dotenv import load_dotenv
load_dotenv()

# ── FastAPI imports ───────────────────────────────────────────────────────────
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

# ── Local modules (imported AFTER load_dotenv) ────────────────────────────────
import speech_to_text as stt
import ai_handler as ai
import text_to_speech as tts
import auth_handler as auth
import email_handler as em

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Fury AI Voice Assistant API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory for audio processing
TEMP_DIR = os.path.join(os.getcwd(), "temp_audio_web")
os.makedirs(TEMP_DIR, exist_ok=True)


# ── Pydantic Models ───────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str
    password: str

class OTPRequest(BaseModel):
    email: str
    otp: str

class VoiceResponse(BaseModel):
    transcript: str
    ai_text: str
    audio_base64: str


# ── Helper: extract Bearer token ──────────────────────────────────────────────

def _get_token(authorization: Optional[str]) -> str:
    """Extracts the JWT from the Authorization header or raises 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    return authorization.split(" ", 1)[1]


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Fury AI Backend is running ✅"}


# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.post("/api/auth/signup")
async def signup(body: AuthRequest):
    """
    Step 1 of Signup: Check for existing account, generate OTP, send email.
    NO Supabase account is created here — only after OTP verification in Step 2.
    Uses sign_in to safely detect existing accounts (no side effects).
    """
    try:
        # Basic validation
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

        # Check if this email is already registered in Supabase BEFORE sending OTP.
        # Uses a database RPC function — read-only, no side effects.
        if auth.email_exists(body.email):
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please log in instead."
            )

        # Check if there's already a pending registration for this email
        if body.email in auth._pending_registrations:
            logger.info(f"Re-sending OTP for pending registration: {body.email}")

        # Generate a 6-digit OTP
        otp = f"{random.randint(100000, 999999)}"

        # Store credentials + OTP in memory ONLY (no Supabase account yet)
        auth._pending_registrations[body.email] = {
            "password": body.password,
            "otp": otp,
        }

        # Send the verification email
        success = em.send_otp_email(body.email, otp)
        if not success:
            del auth._pending_registrations[body.email]
            raise HTTPException(status_code=500, detail="Failed to send verification email. Please try again.")

        return {"status": "pending_otp", "message": "OTP sent to your email."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signup.")


@app.post("/api/auth/verify-otp")
async def verify_otp(body: OTPRequest):
    """
    Step 2 of Signup: Verify OTP, THEN create the Supabase account.
    Only after successful OTP verification does the account get created.
    """
    pending = auth._pending_registrations.get(body.email)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending registration found. Please sign up again.")

    if pending["otp"] != body.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code. Please try again.")

    # OTP is correct — NOW create the Supabase account
    try:
        signup_result = auth.sign_up(body.email, pending["password"])

        # If Supabase has "Confirm email" enabled, sign_up won't return a session.
        # Since we've already verified the email via our own OTP, sign in to get a token.
        if not signup_result.get("access_token"):
            signup_result = auth.sign_in(body.email, pending["password"])

        # Clean up the pending registration
        del auth._pending_registrations[body.email]

        # Send Welcome Email (non-blocking, best-effort)
        em.send_welcome_email(body.email)

        return signup_result

    except Exception as e:
        err_msg = str(e).lower()
        if "already signed up" in err_msg or "already registered" in err_msg or "log in" in err_msg:
            del auth._pending_registrations[body.email]
            raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")
        if "email not confirmed" in err_msg:
            raise HTTPException(status_code=400, detail="Account created, but Supabase requires email confirmation. Please disable 'Confirm email' under Supabase Auth -> Providers -> Email settings.")
        logger.error(f"Account creation failed after OTP verification: {e}")
        raise HTTPException(status_code=500, detail="Verification succeeded but account creation failed. Please try again.")


@app.post("/api/auth/resend-otp")
async def resend_otp(body: AuthRequest):
    """Resend a new OTP for a pending registration."""
    pending = auth._pending_registrations.get(body.email)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending registration found. Please sign up first.")

    # Generate a fresh OTP
    new_otp = f"{random.randint(100000, 999999)}"
    pending["otp"] = new_otp

    success = em.send_otp_email(body.email, new_otp)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to resend verification email. Please try again.")

    return {"status": "pending_otp", "message": "A new OTP has been sent to your email."}


@app.post("/api/auth/login")
async def login(body: AuthRequest):
    """Log in an existing user. Returns user info + access token."""
    try:
        result = auth.sign_in(body.email, body.password)
        return result
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Log out the current session."""
    token = _get_token(authorization)
    auth.sign_out(token)
    return {"message": "Logged out successfully."}


@app.get("/api/auth/sessions")
async def get_sessions(authorization: Optional[str] = Header(None)):
    """Fetch all unique conversation tabs for the user."""
    token = _get_token(authorization)
    user = auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token.")
    return {"sessions": auth.get_sessions(token, user["id"])}


@app.get("/api/auth/history")
async def get_history(session_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Fetch chat history, optionally filtered by session_id."""
    token = _get_token(authorization)
    user = auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    
    history = auth.get_history(token, user["id"], session_id=session_id)
    return {"history": history}


@app.delete("/api/auth/sessions/{session_id}")
async def delete_session(session_id: str, authorization: Optional[str] = Header(None)):
    """Deletes a specific chat session for the user."""
    token = _get_token(authorization)
    user = auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token or user session.")
    try:
        auth.delete_history_session(token, user["id"], session_id)
        return {"status": "success", "message": "Session deleted permanently."}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session.")


# ── Voice Processing Routes ──────────────────────────────────────────────────


@app.post("/api/voice/process", response_model=VoiceResponse)
async def process_voice(
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Multimodal processing:
    1. (Optional) Audio → STT
    2. (Optional) Image → Base64
    3. (Optional) Text
    4. Combine → LLM (Vision if image present) → TTS → return transcript + ai_text + audio_base64
    """
    token = _get_token(authorization)
    user = auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token.")

    user_id = user["id"]
    session_id = x_session_id or uuid.uuid4().hex

    # Ensure session history is loaded
    existing_mem = ai.get_history(session_id)
    if not existing_mem:
        db_history = auth.get_history(token, user_id, session_id=session_id)
        if db_history:
            ai.load_history_to_memory(session_id, db_history)

    request_id = uuid.uuid4().hex[:8]
    transcript = text or ""
    image_b64 = None

    # ── 1. Handle Image ───────────────────────────────────────────────────────
    if image:
        img_content = await image.read()
        image_b64 = base64.b64encode(img_content).decode("utf-8")
        logger.info(f"[{session_id}] Image received: {len(img_content)} bytes")

    # ── 2. Handle Audio (STT) ──────────────────────────────────────────────────
    input_path = None
    if file:
        content_type = file.content_type or "audio/webm"
        ext = ".ogg" if "ogg" in content_type else ".webm"
        input_path = os.path.join(TEMP_DIR, f"{request_id}_in{ext}")

        try:
            content = await file.read()
            if len(content) > 100:
                with open(input_path, "wb") as f:
                    f.write(content)

                logger.info(f"[{session_id}] User {user['email']} | Received {len(content)} bytes ({content_type})")
                audio_transcript = stt.transcribe_voice(input_path)
                if audio_transcript and audio_transcript.strip():
                    transcript = (transcript + " " + audio_transcript).strip()
        except Exception as e:
            logger.error(f"STT Error: {e}")
        finally:
            if input_path and os.path.exists(input_path):
                try:
                    os.remove(input_path)
                except OSError:
                    pass

    if not transcript and not image_b64:
        raise HTTPException(status_code=400, detail="No input provided (voice, text, or image)")

    if not transcript and image_b64:
        transcript = "What is in this image?"  # Default prompt if only image sent

    logger.info(f"[{session_id}] Transcript: {transcript[:80]}")

    # ── 3. LLM response (multimodal if image_b64 is set) ──────────────────────
    try:
        ai_text = ai.generate_response(session_id, transcript, image_data=image_b64)
        logger.info(f"[{request_id}] AI reply: {ai_text[:80]}")
    except Exception as e:
        logger.exception(f"[{request_id}] LLM error: {e}")
        raise HTTPException(status_code=500, detail="AI response generation failed")

    # ── 4. Generate Title if session is new ──────────────────────────────────
    session_title = None
    history = ai.get_history(session_id)
    if len(history) <= 2:
        session_title = ai.generate_session_title(transcript)
        logger.info(f"[{request_id}] Generated session title: {session_title}")

    # ── 5. Persist both messages to Supabase ──────────────────────────────────
    auth.save_message(token, user_id, "user", transcript, session_id=session_id, session_title=session_title)
    auth.save_message(token, user_id, "assistant", ai_text, session_id=session_id, session_title=session_title)

    # ── 6. Text → Speech ─────────────────────────────────────────────────────
    audio_b64 = ""
    try:
        ogg_path = await tts.synthesize(ai_text)
        if ogg_path and os.path.exists(ogg_path):
            with open(ogg_path, "rb") as audio_file:
                audio_b64 = base64.b64encode(audio_file.read()).decode("utf-8")
            tts.cleanup(ogg_path)
    except Exception as e:
        logger.error(f"TTS Error: {e}")

    return VoiceResponse(
        transcript=transcript,
        ai_text=ai_text,
        audio_base64=audio_b64,
    )


# ── Serve Frontend ────────────────────────────────────────────────────────────
# IMPORTANT: This MUST come AFTER all API routes
FRONTEND_DIST = os.path.join(os.getcwd(), "frontend", "dist")

@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
async def serve_index():
    if os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
    return {"message": "Fury AI API is live. (Frontend not built yet)"}

if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    # Use 0.0.0.0 to allow external access in cloud environments (Render, etc.)
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Fury AI Backend on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

