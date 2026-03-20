# 🎙️ Fury AI – Voice Assistant

> A Gemini-inspired AI voice assistant that lives in your browser.  
> Built with FastAPI, OpenAI Whisper, Groq (Llama 3), and gTTS.  
> © 2024 Fayaz Ahmed Shaik. All rights reserved.

---

## ✨ Features

- 🎙️ **Voice Input** – Record your voice directly in the browser
- 🧠 **AI Intelligence** – Powered by Groq's Llama 3 (free tier)
- 🔊 **Voice Output** – AI replies are spoken back to you
- 💬 **Conversation Memory** – Remembers your chat history per session
- 🌐 **Fully Web-Based** – No app or Telegram required

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI + Uvicorn |
| **Speech-to-Text** | OpenAI Whisper (`tiny` model) |
| **AI / LLM** | Groq API (Llama 3) |
| **Text-to-Speech** | gTTS |
| **Frontend** | React + Vite |
| **Deployment** | Render |

---

## 🚀 Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/fayaz-shaik-27/FURY-AI-Gemini-Inspired.git
cd "FURY-AI-Gemini-Inspired"
```

### 2. Create virtualenv & install dependencies
```bash
python -m venv venv
.\venv\Scripts\python -m pip install -r requirements.txt
```

### 3. Set your environment variables
```bash
cp .env.sample .env
# Edit .env and add your GROQ_API_KEY
```

### 4. Run the backend
```bash
.\venv\Scripts\python api.py
```

### 5. Run the frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```

Visit: **[http://localhost:5173](http://localhost:5173)**

---

## 🌍 Deploy on Render

1. Push to GitHub
2. Create a **Web Service** on [render.com](https://render.com)
3. Set the **Build Command**:
   ```
   cd frontend && npm install && npx vite build && cd .. && pip install -r requirements.txt
   ```
4. Set the **Start Command**:
   ```
   python api.py
   ```
5. Add **Environment Variables**:
   - `GROQ_API_KEY` = your key from [console.groq.com](https://console.groq.com)
   - `WHISPER_MODEL` = `tiny`
   - `ASSISTANT_NAME` = `Fury AI`

---

## 📄 License
MIT © 2024 **Fayaz Ahmed Shaik**. All rights reserved.  
Build something awesome! 🚀
