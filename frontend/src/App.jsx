import React, { useState, useRef, useEffect, useCallback } from 'react';

// ── Waveform Animation Component ────────────────────────────────────────────
function VoiceWaveform({ active, color = '#8ab4f8' }) {
  const NUM_BARS = 28;
  return (
    <div className="waveform-container" aria-hidden="true">
      {Array.from({ length: NUM_BARS }).map((_, i) => (
        <div
          key={i}
          className="waveform-bar"
          style={{
            background: color,
            animationDelay: `${(i * 80) % 700}ms`,
            animationDuration: `${600 + (i * 97) % 500}ms`,
            animationPlayState: active ? 'running' : 'paused',
            height: active ? undefined : '4px',
          }}
        />
      ))}
    </div>
  );
}

// ── Gemini Orb (idle / thinking / speaking states) ──────────────────────────
function GeminiOrb({ state }) {
  // state: 'idle' | 'recording' | 'processing' | 'speaking'
  const gradients = {
    idle:       ['#4285f4', '#9c27b0'],
    recording:  ['#ea4335', '#f97316'],
    processing: ['#34a853', '#4285f4'],
    speaking:   ['#8ab4f8', '#c084fc'],
  };
  const [c1, c2] = gradients[state] || gradients.idle;

  return (
    <div className={`orb-wrapper state-${state}`}>
      {/* Ripple rings */}
      {(state === 'recording' || state === 'speaking') && (
        <>
          <div className="ripple ripple-1" style={{ borderColor: c1 }} />
          <div className="ripple ripple-2" style={{ borderColor: c2 }} />
          <div className="ripple ripple-3" style={{ borderColor: c1 }} />
        </>
      )}
      {/* Core orb */}
      <div
        className="orb-core"
        style={{ background: `linear-gradient(135deg, ${c1}, ${c2})` }}
      >
        {state === 'idle' && (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
            <path d="M12 15c1.66 0 3-1.34 3-3V6c0-1.66-1.34-3-3-3S9 4.34 9 6v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V6z"/>
            <path d="M17 12c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-2.08c3.39-.49 6-3.39 6-6.92h-2z"/>
          </svg>
        )}
        {state === 'recording' && (
          <div className="rec-dot" />
        )}
        {state === 'processing' && (
          <div className="thinking-dots">
            <span /><span /><span />
          </div>
        )}
        {state === 'speaking' && (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
          </svg>
        )}
      </div>
    </div>
  );
}

// ── Message Bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg, index }) {
  const isUser = msg.role === 'user';
  return (
    <div
      className={`bubble-row ${isUser ? 'bubble-row-user' : 'bubble-row-ai'}`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {!isUser && (
        <div className="bubble-avatar">
          <div className="avatar-gem" />
        </div>
      )}
      <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-ai'}`}>
        {msg.text}
      </div>
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [orbState, setOrbState] = useState('idle');   // idle | recording | processing | speaking
  const [history, setHistory] = useState([
    { role: 'ai', text: 'Hi! I\'m Fury AI, your AI voice assistant. Tap the mic to start talking.' }
  ]);
  const [statusText, setStatusText] = useState('Tap the microphone to begin');
  const [error, setError] = useState('');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef   = useRef([]);
  const chatEndRef        = useRef(null);
  const audioRef          = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  const startRecording = useCallback(async () => {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? { mimeType: 'audio/webm;codecs=opus' }
        : {};
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await processVoice(blob);
      };

      mediaRecorderRef.current.start(200); // collect in 200ms chunks
      setOrbState('recording');
      setStatusText('Listening… tap again to send');
    } catch (err) {
      setError('Microphone access denied. Please allow microphone permissions and refresh.');
      setOrbState('idle');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setOrbState('processing');
      setStatusText('Fury AI is thinking…');
    }
  }, []);

  const processVoice = async (blob) => {
    const formData = new FormData();
    formData.append('file', blob, 'voice.webm');

    try {
      const res = await fetch('/api/voice/process', { method: 'POST', body: formData });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }
      const data = await res.json();

      setHistory((prev) => [
        ...prev,
        { role: 'user', text: data.transcript },
        { role: 'ai',   text: data.ai_text    },
      ]);

      // Play audio response
      if (data.audio_base64) {
        setOrbState('speaking');
        setStatusText('Fury AI is speaking…');
        const audio = new Audio(`data:audio/mp3;base64,${data.audio_base64}`);
        audioRef.current = audio;
        audio.onended = () => {
          setOrbState('idle');
          setStatusText('Tap the microphone to begin');
        };
        audio.onerror = () => {
          setOrbState('idle');
          setStatusText('Tap the microphone to begin');
        };
        audio.play().catch(() => {});
      } else {
        setOrbState('idle');
        setStatusText('Tap the microphone to begin');
      }
    } catch (err) {
      console.error(err);
      setError(`Error: ${err.message}`);
      setOrbState('idle');
      setStatusText('Tap the microphone to begin');
    }
  };

  const handleMicClick = () => {
    if (orbState === 'recording') {
      stopRecording();
    } else if (orbState === 'idle') {
      startRecording();
    }
  };

  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setOrbState('idle');
    setStatusText('Tap the microphone to begin');
  };

  const clearHistory = () => {
    setHistory([{ role: 'ai', text: 'Conversation cleared. How can I help you?' }]);
  };

  const isActive = orbState === 'recording' || orbState === 'speaking';

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="logo">
          <div className="logo-gem" />
          <span className="logo-text">Fury <span className="logo-sub">AI</span></span>
        </div>
        <nav className="header-nav">
          <button className="nav-btn" onClick={clearHistory} title="Clear chat">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
            </svg>
            Clear
          </button>
        </nav>
      </header>

      {/* ── Body ── */}
      <main className="app-main">
        {/* ── Conversation ── */}
        <section className="chat-section">
          <div className="chat-messages">
            {history.map((msg, i) => (
              <MessageBubble key={i} msg={msg} index={i} />
            ))}
            <div ref={chatEndRef} />
          </div>
        </section>

        {/* ── Voice Stage ── */}
        <section className="voice-stage">
          {/* Waveform top (recording) */}
          <div className={`waveform-area waveform-top ${orbState === 'recording' ? 'wf-visible' : ''}`}>
            <VoiceWaveform active={orbState === 'recording'} color="#ea4335" />
          </div>

          {/* Orb */}
          <button
            className={`orb-btn ${orbState === 'processing' ? 'orb-btn-inactive' : ''}`}
            onClick={orbState === 'speaking' ? stopSpeaking : handleMicClick}
            disabled={orbState === 'processing'}
            aria-label={orbState === 'recording' ? 'Stop recording' : 'Start recording'}
          >
            <GeminiOrb state={orbState} />
          </button>

          {/* Waveform bottom (speaking) */}
          <div className={`waveform-area waveform-bottom ${orbState === 'speaking' ? 'wf-visible' : ''}`}>
            <VoiceWaveform active={orbState === 'speaking'} color="#8ab4f8" />
          </div>

          {/* Status */}
          <p className="status-text">{statusText}</p>

          {/* Error */}
          {error && (
            <div className="error-banner">
              <span>⚠️ {error}</span>
              <button onClick={() => setError('')}>✕</button>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
