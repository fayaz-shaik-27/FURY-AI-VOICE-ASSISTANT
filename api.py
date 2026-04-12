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

# ── Load env variables FIRST before any other local imports ──────────────────
from dotenv import load_dotenv
load_dotenv()

# ── FastAPI imports ───────────────────────────────────────────────────────────
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
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
    """Register a new user. Returns user info + access token."""
    try:
        result = auth.sign_up(body.email, body.password)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Receive audio blob from browser → STT → LLM → TTS → return base64 audio.
    Now supports session-based context.
    """
    token = _get_token(authorization)
    user = auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token.")

    user_id = user["id"]
    
    # 1. Handle Session ID
    if not x_session_id:
        # If no session ID provided, we can't maintain context correctly across turns
        # but for safety let's generate one if missing
        session_id = uuid.uuid4().hex
    else:
        session_id = x_session_id

    # 2. Ensure session history is loaded in AI memory if it's a resume
    existing_mem = ai.get_history(session_id)
    if not existing_mem:
        # Try loading from DB
        db_history = auth.get_history(token, user_id, session_id=session_id)
        if db_history:
            ai.load_history_to_memory(session_id, db_history)

    # Temporary request ID for logging
    request_id = uuid.uuid4().hex[:8] 

    # Determine file extension
    content_type = file.content_type or "audio/webm"
    ext = ".ogg" if "ogg" in content_type else ".webm"
    input_path = os.path.join(TEMP_DIR, f"{request_id}_in{ext}")

    try:
        # ── 1. Save uploaded audio ────────────────────────────────────────────
        content = await file.read()
        if len(content) < 100:
            raise HTTPException(status_code=400, detail="Audio file too small — no audio captured")

        with open(input_path, "wb") as f:
            f.write(content)

        logger.info(f"[{session_id}] User {user['email']} | Received {len(content)} bytes ({content_type})")

        # ── 2. Speech → Text ──────────────────────────────────────────────────
        transcript = stt.transcribe_voice(input_path)
        if not transcript or not transcript.strip():
            raise HTTPException(status_code=400, detail="Could not transcribe audio — please speak clearly")

        logger.info(f"[{session_id}] Transcript: {transcript[:80]}")

        # ── 3. LLM response ───────────────────────────────────────────────────
        ai_text = ai.generate_response(session_id, transcript)
        logger.info(f"[{request_id}] AI reply: {ai_text[:80]}")

        # ── 4. Generate Title if session is new ──────────────────────────────
        session_title = None
        # Check if this is the first exchange (now 1 user message in memory)
        history = ai.get_history(session_id)
        if len(history) <= 2: # User msg + AI reply
            session_title = ai.generate_session_title(transcript)
            logger.info(f"[{request_id}] Generated session title: {session_title}")

        # ── 5. Persist both messages to Supabase ──────────────────────────────
        auth.save_message(token, user_id, "user", transcript, session_id=session_id, session_title=session_title)
        auth.save_message(token, user_id, "assistant", ai_text, session_id=session_id, session_title=session_title)

        # ── 5. Text → Speech ──────────────────────────────────────────────────
        ogg_path = await tts.synthesize(ai_text)
        if not ogg_path or not os.path.exists(ogg_path):
            raise HTTPException(status_code=500, detail="TTS synthesis failed")

        # ── 6. Encode audio to base64 ─────────────────────────────────────────
        with open(ogg_path, "rb") as audio_file:
            audio_b64 = base64.b64encode(audio_file.read()).decode("utf-8")

        tts.cleanup(ogg_path)

        return VoiceResponse(
            transcript=transcript,
            ai_text=ai_text,
            audio_base64=audio_b64,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except OSError:
                pass


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
    app.mount("/", StaticFiles(directory=FRONTEND_DIST), name="ui")


if __name__ == "__main__":
    import uvicorn
    # Use 127.0.0.1 for local dev to ensure perfect mapping with Vite proxy
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Fury AI Backend on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
