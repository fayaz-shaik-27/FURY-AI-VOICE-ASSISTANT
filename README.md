# 🎙️ Fury AI – Advanced Voice Assistant

> A multimodal AI voice assistant with image analysis, secure OTP authentication, and persistent multi-session chat history.  
> Built with FastAPI, Groq (Llama 4 Scout, Llama 3.3 & Whisper), Supabase, and edge-tts.  
> © 2026 **Fayaz Ahmed Shaik**. All rights reserved.

---

## ✨ Features

- 🖼️ **Multimodal Image Analysis** – Upload images and ask questions about them using Llama 4 Scout vision model.
- 🌊 **Organic Audio Visualizer** – Real-time, reactive waveforms for both user input and AI speech.
- 🎙️ **Voice Input & Output** – Hands-free interaction directly in your browser.
- ⌨️ **Text Input** – Type your questions when voice isn't convenient.
- 🔐 **Secure OTP Authentication** – Email-verified accounts powered by **Supabase Auth** with custom OTP flow.
- 🧠 **Multi-Session History** – Persistent, session-based chat threads. Browse, resume, or delete past conversations.
- 🚀 **High Performance** – Powered by **Groq's** lightning-fast inference engine.
- 🔊 **Human-like Voice** – High-quality neural text-to-speech using **edge-tts**.
- 📱 **Responsive Design** – Premium dark-themed, glassmorphism UI optimized for desktop and mobile.
- 📧 **Transactional Emails** – OTP verification and welcome emails via **Brevo SMTP**.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | `FastAPI` (Python) | Core server and API logic |
| **Frontend** | `React 18` + `Vite` | Sleek, interactive user interface |
| **Authentication** | `Supabase Auth` | User login, signup, and session management |
| **Database** | `Supabase (PostgreSQL)` | Secure storage for chat history with RLS |
| **Email Service** | `Brevo SMTP` | OTP verification and welcome emails |
| **STT (Speech)** | `Groq Whisper-v3-turbo` | Near-instant voice-to-text transcription |
| **LLM (Text)** | `Groq Llama 3.1-8b-instant` | Fast reasoning and conversational responses |
| **LLM (Vision)** | `Groq Llama 4 Scout` | Multimodal image understanding and analysis |
| **TTS (Speech)** | `edge-tts` | Microsoft Azure Neural voices for natural speech |
| **Visualizer** | `Web Audio API` | Real-time frequency analysis & organic waveforms |

---

## 📂 Project Structure

```
Voice Assistant/
├── api.py                 # FastAPI server – routes, auth, voice processing
├── ai_handler.py          # LLM integration, vision, conversation memory
├── speech_to_text.py      # Groq Whisper STT
├── text_to_speech.py      # edge-tts wrapper
├── auth_handler.py        # Supabase Auth + chat history persistence
├── email_handler.py       # Brevo SMTP (OTP & welcome emails)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not committed)
├── .env.sample            # Template for .env configuration
└── frontend/
    ├── src/
    │   ├── App.jsx        # Main React app (chat, voice, image upload)
    │   └── index.css      # Global styles (glassmorphism, responsive)
    ├── package.json
    └── vite.config.js
```

---

## 🚀 Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/fayaz-shaik-27/FURY-AI-VOICE-ASSISTANT.git
cd FURY-AI-VOICE-ASSISTANT
```

### 2. Install Dependencies
```bash
# Install Python backend requirements
pip install -r requirements.txt

# Install Frontend requirements
cd frontend
npm install
cd ..
```

### 3. Database Setup (Supabase)
1. Create a free project at [supabase.com](https://supabase.com).
2. Go to the **SQL Editor** and run the following to create the history table:
```sql
CREATE TABLE chat_history (
  id             BIGSERIAL PRIMARY KEY,
  user_id        UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  session_id     TEXT NOT NULL,
  session_title  TEXT,
  role           TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  message        TEXT NOT NULL,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

-- Allow users to only see their own history
CREATE POLICY "Users can access own history"
  ON chat_history FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
```

### 4. Email Setup (Brevo SMTP)
1. Create a free account at [brevo.com](https://www.brevo.com).
2. Go to **Settings → SMTP & API → SMTP tab** to get your credentials.
3. Add your Brevo SMTP login and password to the `.env` file.

### 5. Configuration
Copy `.env.sample` to `.env` and fill in your values.

On macOS / Linux:
```bash
cp .env.sample .env
```

On Windows (PowerShell):
```powershell
Copy-Item .env.sample -Destination .env
```

Then open `.env` and fill values. Example `.env` entries:

```env
# ── Server ─────────────────────────────────────────────────────
# Optional: port the backend should listen on (default 8000)
PORT=8000

# ── AI (Groq – Free Tier) ─────────────────────────────────────
GROQ_API_KEY=your_groq_api_key_here
# Recommended models (provider-dependent): llama-3.1-8b-instant | openai/gpt-oss-120b
GROQ_MODEL=llama-3.1-8b-instant
# Vision model used for image understanding
GROQ_VISION_MODEL=qwen/qwen3.6-27b
# Whisper STT model
WHISPER_MODEL=whisper-large-v3-turbo
ASSISTANT_NAME=Fury AI

# ── Text-to-Speech (edge-tts) ─────────────────────────────────
TTS_VOICE=en-US-AriaNeural
TTS_RATE=+30%

# ── Supabase (Auth + Database) ────────────────────────────────
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-public-key-here

# ── Email Service (Brevo SMTP) ────────────────────────────────
BREVO_SMTP_LOGIN=your-brevo-account-email@gmail.com
BREVO_SMTP_PASSWORD=your-brevo-smtp-key-here
SENDER_EMAIL=your-brevo-account-email@gmail.com
```

### 6. Start the Application

**Production mode** (serves built frontend):
```bash
cd frontend && npm run build && cd ..
python api.py
```
Visit: **[http://localhost:8000](http://localhost:8000)**

**Development mode** (hot-reload for frontend):
```bash
# Terminal 1 – Backend
python api.py

# Terminal 2 – Frontend dev server
cd frontend
npm run dev
```
Visit: **[http://localhost:5173](http://localhost:5173)**

---

## 🖼️ Multimodal Image Analysis

Fury AI supports uploading images alongside your text or voice queries. Simply click the image icon in the chat input to attach an image, then ask your question.

**Supported capabilities:**
- Describe image contents
- Read and extract text from documents, certificates, and screenshots
- Answer questions about visual content
- Analyze charts, diagrams, and photos

**Powered by:** `meta-llama/llama-4-scout-17b-16e-instruct` via Groq's free API.

---

## 🔐 Authentication Flow

1. **Signup** → User provides email + password → Server generates OTP → Verification email sent via Brevo SMTP.
2. **OTP Verification** → User enters the 6-digit code → Server validates → Supabase account created only after verification.
3. **Login** → Standard email/password authentication via Supabase Auth.
4. **Session Management** → JWT-based auth with Bearer tokens for all API calls.

---

## 🌍 Deployment

### Deploy on Render
1. Push your code to GitHub.
2. Link your repo to **Render.com**.
3. **Build Command**: 
   `cd frontend && npm install && npm run build && cd .. && pip install -r requirements.txt`
4. **Start Command**: `python api.py`
5. Add your `.env` variables in the Render dashboard.

---

## 📄 License
MIT © 2026 **Fayaz Ahmed Shaik**. All rights reserved.  
Build something awesome! 🚀
