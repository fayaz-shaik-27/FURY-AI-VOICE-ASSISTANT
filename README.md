# 🎙️ AI Voice Assistant – Telegram (Free Voicemail Alternative)

A fully free, production-ready AI voicemail assistant on Telegram.  
Send a **voice message** → get a smart **voice reply** — all automated!

---

## 🏗️ Architecture

```
User Voice Message (.ogg)
        ↓
[Speech-to-Text]  openai-whisper (local)
        ↓
[AI Response]     Groq LLM (llama3-8b) + per-user memory
        ↓
[Text-to-Speech]  gTTS → .ogg (Opus)
        ↓
Voice Reply sent back via Telegram
```

---

## 📁 Project Structure

```
Voice Automation/
├── main.py              # Telegram bot – entry point
├── ai_handler.py        # LLM logic, memory, intent detection
├── speech_to_text.py    # Whisper STT (ogg → wav → text)
├── text_to_speech.py    # gTTS TTS (text → ogg)
├── requirements.txt     # Python dependencies
├── .env.sample          # Environment variable template
└── audio_output/        # Temp audio files (auto-created)
```

---

## ⚡ Quick Start (Local)

### 1. Prerequisites
- Python 3.10+
- **ffmpeg** installed and on PATH
  - Windows: `choco install ffmpeg` or download from https://ffmpeg.org/download.html
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

### 2. Get Your API Keys (Both Free)

| Key | Where to get |
|---|---|
| **Telegram Bot Token** | Message [@BotFather](https://t.me/BotFather) → `/newbot` |
| **Groq API Key** | Sign up at [console.groq.com](https://console.groq.com/) |

### 3. Setup the Project

```bash
# Clone / open the project directory
cd "Voice Automation"

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env template and fill in your keys
copy .env.sample .env      # Windows
# cp .env.sample .env      # macOS/Linux
```

### 4. Fill in `.env`

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama3-8b-8192
WHISPER_MODEL=base
ASSISTANT_NAME=Aria
```

### 5. Run the Bot

```bash
python main.py
```

Open Telegram, find your bot, and send a voice message! 🎉

---

## 🌐 Deploying to Render (Free)

### Steps:

1. **Push project to GitHub** (create a free account if needed)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set the following:

| Setting | Value |
|---|---|
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python main.py` |

5. Add **Environment Variables** in the Render dashboard:
   - `TELEGRAM_BOT_TOKEN`: (Your bot token)
   - `GROQ_API_KEY`: (Your Groq key)
   - `GROQ_MODEL`: `llama-3.3-70b-versatile`
   - `WHISPER_MODEL`: `base`
   - `ASSISTANT_NAME`: `Aria` (or your name)
   - `PORT`: `8080` (Render will use this for the health check)

6. Click **Deploy** and wait ~2 minutes.

> [!TIP]
> **Keep Alive:** To prevent the free tier from sleeping, you can use a free service like [cron-job.org](https://cron-job.org/) to ping your Render URL `https://your-service-name.onrender.com` every 10 minutes.

> [!NOTE]
> Render free tier may have ~30s cold-start delay. The bot will stay responsive after the first wake-up.
> Also note: Whisper downloads the model on first run (~75MB for `base`). This is normal.

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and instructions |
| `/reset` | Clear your conversation memory |
| `/voicemails` | List all stored voice messages |
| *(voice msg)* | Full STT → LLM → TTS pipeline |
| *(text msg)* | LLM → TTS pipeline (skips STT) |

---

## 💾 Memory & Conversation Context

Each user gets their own conversation history stored in memory.  
The bot remembers the last **10 exchanges** (20 messages) per user.
Memory resets on bot restart.

**To add persistent memory:** Replace the in-memory dict in `ai_handler.py` with a SQLite database:

```python
import sqlite3
# Store/load messages per user_id in a local SQLite file
```

---

## 🧠 Intent Detection

The bot automatically detects these intents (rule-based, no ML needed):

| Intent | Example |
|---|---|
| `greeting` | "Hi", "Hello", "Good morning" |
| `farewell` | "Bye", "See you later" |
| `gratitude` | "Thanks", "Thank you" |
| `help` | "Help me with...", "Can you..." |
| `question` | "What is...", "How do I..." |
| `affirmation` | "Yes", "Sure", "Okay" |
| `negation` | "No", "Nope" |

---

## 📱 How to use as a Real Mobile Voicemail (Free)

To have Aria (your AI) answer your phone calls when you miss them, follow these steps:

### 1. The "Call Forwarding" Bridge
Since Telegram cannot answer direct cellular calls, you use a **Conditional Call Forwarding (CCF)** bridge.

**Step A: Get a Google Voice Number (Free)**
1.  Get a free number at [voice.google.com](https://voice.google.com).
2.  Set the Google Voice greeting to something like: *"You've reached Aria, my AI assistant. Please hang up and click the link I just texted you to leave a voice message, or wait for the beep."*

**Step B: Link to Telegram**
1.  On your Android/iPhone, set your **Conditional Call Forwarding** to your Google Voice number.
    - *Common codes:* Dial `*61*YourGVNumber#` (if no answer) or `*67*YourGVNumber#` (if busy/declined).
2.  When you decline a call, it goes to Google Voice.
3.  Google Voice will record the message and send you an email.

### 2. The "Auto-Reply" Method (Recommended & Simplest)
This is the most "interactive" way to use your bot:

1.  **Android (MacroDroid/Tasker):** Create a macro that triggers on a **Missed Call**.
2.  **Action:** Send an SMS to the caller: *"Sorry I missed your call! Direct voicemails are full, but you can leave a voice message for my AI assistant here: https://t.me/YourBotUsername"*
3.  When the caller clicks the link and sends a voice note, **Aria** processes it immediately, saves it to your `/voicemails` box, and even has a conversation with them!

### 3. Checking Your Voicemails
All messages sent to the bot are now saved permanently in a local database (`voicemails.db`).
-   To see them, simply type `/voicemails` in the bot.
-   It will show you the **caller name**, **timestamp**, and the **full transcript**.

---

## 🚀 Future Upgrades

| Upgrade | Description |
|---|---|
| **Twilio Integration** | Handle real phone calls; answer with your AI voice |
| **ElevenLabs TTS** | More human-sounding voice synthesis (free tier: 10K chars/mo) |
| **Persistent Memory** | SQLite or Redis for memory that survives bot restarts |
| **Multi-language** | Auto-detect language from Whisper and reply in same language |
| **Real Call Agent** | Combine with Twilio + LLM for a full AI phone agent |
| **Webhook mode** | Replace polling with webhook for faster response on cloud |
| **Analytics** | Log intents, usage patterns per user for improvements |

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `FileNotFoundError: ffmpeg` | Install ffmpeg and add to PATH |
| Whisper model loads slowly | Normal on first run; model is cached after that |
| `Invalid token` | Double-check your `TELEGRAM_BOT_TOKEN` in `.env` |
| `Groq API error` | Verify your `GROQ_API_KEY` and check free-tier limits |
| No audio reply | Check the `audio_output/` folder for errors in logs |

---

## 📄 License

MIT – Free to use, modify, and deploy. Build something awesome! 🚀
