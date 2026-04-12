# 🎙️ Fury AI – Advanced Voice Assistant

> A Gemini-inspired AI voice assistant with secure authentication and persistent multi-user chat history.  
> Built with FastAPI, Groq (Llama 3.3 & Whisper), Supabase, and edge-tts.  
> © 2026 **Fayaz Ahmed Shaik**. All rights reserved.

---

## ✨ Features

- 🎙️ **Voice Input & Output** – Hands-free interaction directly in your browser.
- 🔐 **Secure Authentication** – Personal accounts powered by **Supabase Auth**.
- 🧠 **Persistent History** – Never lose a conversation. History is saved to a cloud database and tied to your account.
- 🚀 **High Performance** – Powered by **Groq's** lightning-fast Llama 3.3 and Whisper models.
- 🔊 **Human-like Voice** – High-quality neural text-to-speech using **edge-tts**.
- 📱 **Responsive Design** – Premium dark-themed, glassmorphism UI that works on mobile and desktop.
- 📧 **Verification Emails** – Secure account verification via **Resend**.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | `FastAPI` (Python) | Core server and API logic |
| **Frontend** | `React` + `Vite` | Sleek, interactive user interface |
| **Authentication** | `Supabase Auth` | User login, signup, and session management |
| **Database** | `Supabase (PostgreSQL)` | Secure storage for chat history with RLS |
| **Email Service** | `Resend` | Professional transactional email delivery |
| **STT (Speech)** | `Groq Whisper-v3` | Near-instant voice-to-text transcription |
| **LLM (AI)** | `Groq Llama 3.3-70b` | High-intelligence reasoning and responses |
| **TTS (Speech)** | `edge-tts` | Microsoft Azure Neural voices for natural speech |

---

## 🚀 Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/fayaz-shaik-27/FURY-AI-Gemini-Inspired.git
cd "FURY-AI-Gemini-Inspired"
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

### 4. Email Setup (Resend)
To ensure your signup emails actually reach your inbox:
1. Create a free account at [Resend.com](https://resend.com).
2. Create an **API Key** with "Full Access".
3. In Supabase Dashboard, go to **Settings -> Authentication -> SMTP**.
4. Enable **Custom SMTP** and enter:
   - **Sender Email:** `onboarding@resend.dev` (if using testing domain)
   - **Host:** `smtp.resend.com`
   - **Port:** `587`
   - **User:** `resend`
   - **Password:** *Your Resend API Key*

### 5. Configuration
Create a `.env` file in the root directory:
```env
# AI API Keys
GROQ_API_KEY=your_groq_api_key_here

# Supabase Keys
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-public-key-here
```

### 6. Start the Application
You only need to run the backend; it will serve the built frontend automatically.
```bash
python api.py
```
Visit: **[http://localhost:8000](http://localhost:8000)**

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
