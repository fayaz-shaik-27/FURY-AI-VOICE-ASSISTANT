"""
FastAPI backend for Fury AI Voice Assistant web interface.
© 2024 Fayaz Ahmed Shaik. All rights reserved.
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
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── Local modules (imported AFTER load_dotenv) ────────────────────────────────
import speech_to_text as stt
import ai_handler as ai
import text_to_speech as tts

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Fury AI Voice Assistant API", version="1.0.0")

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


class VoiceResponse(BaseModel):
    transcript: str
    ai_text: str
    audio_base64: str


# ── Root / Health Check ────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Fury AI Backend is running ✅"}


@app.post("/api/voice/process", response_model=VoiceResponse)
async def process_voice(file: UploadFile = File(...)):
    """
    Receive audio blob from browser → STT → LLM → TTS → return base64 audio.
    Browser sends audio/webm (Chrome) or audio/ogg (Firefox).
    Whisper handles both via ffmpeg under the hood.
    """
    session_id = uuid.uuid4().hex[:10]

    # Determine file extension from MIME type
    content_type = file.content_type or "audio/webm"
    ext = ".ogg" if "ogg" in content_type else ".webm"
    input_path  = os.path.join(TEMP_DIR, f"{session_id}_in{ext}")

    try:
        # ── 1. Save uploaded audio ────────────────────────────────────────────
        content = await file.read()
        if len(content) < 100:
            raise HTTPException(status_code=400, detail="Audio file too small — no audio captured")

        with open(input_path, "wb") as f:
            f.write(content)

        logger.info(f"[{session_id}] Received {len(content)} bytes ({content_type})")

        # ── 2. Speech → Text ──────────────────────────────────────────────────
        transcript = stt.transcribe_voice(input_path)
        if not transcript or not transcript.strip():
            raise HTTPException(status_code=400, detail="Could not transcribe audio — please speak clearly")

        logger.info(f"[{session_id}] Transcript: {transcript[:80]}")

        # ── 3. LLM response ───────────────────────────────────────────────────
        # Use user_id=999 for the web interface (session-less for now)
        ai_text = ai.generate_response(999, transcript)
        logger.info(f"[{session_id}] AI reply: {ai_text[:80]}")

        # ── 4. Text → Speech ──────────────────────────────────────────────────
        ogg_path = tts.synthesize(ai_text)
        if not ogg_path or not os.path.exists(ogg_path):
            raise HTTPException(status_code=500, detail="TTS synthesis failed")

        # ── 5. Encode audio to base64 ─────────────────────────────────────────
        with open(ogg_path, "rb") as audio_file:
            audio_b64 = base64.b64encode(audio_file.read()).decode("utf-8")

        # Cleanup the synthesized file
        tts.cleanup(ogg_path)

        return VoiceResponse(
            transcript=transcript,
            ai_text=ai_text,
            audio_base64=audio_b64,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] Unexpected error: {e}")
        # Return the actual error message for local debugging
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
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
