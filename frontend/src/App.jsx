import React, { useState, useRef, useEffect, useCallback } from 'react';

function VoiceWaveform({ active, color = '#8ab4f8', analyser }) {
  const NUM_BARS = 28;
  const barsRef = useRef([]);
  // Store the current "decayed" heights to create organic movement
  const currentHeights = useRef(new Float32Array(NUM_BARS));

  useEffect(() => {
    if (!active || !analyser) {
      // Smoothly return to baseline when idle
      barsRef.current.forEach((bar, i) => { 
        if (bar) bar.style.height = '4px'; 
        currentHeights.current[i] = 0;
      });
      return;
    }

    let animationId;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const update = () => {
      analyser.getByteFrequencyData(dataArray);
      
      for (let i = 0; i < NUM_BARS; i++) {
        const bar = barsRef.current[i];
        if (!bar) continue;

        // Symmetric frequency mapping: Lows in the middle, Highs on the ends
        const centerOffset = Math.abs(i - (NUM_BARS - 1) / 2);
        // Map to frequency bins (using lower/mid range for better visibility)
        const freqIndex = Math.floor(Math.pow(centerOffset / (NUM_BARS / 2), 1.5) * (dataArray.length / 4));
        const rawVal = dataArray[freqIndex] || 0;
        
        // Target height based on volume (0 to 64px)
        const targetHeight = (rawVal / 255) * 60;
        
        let h = currentHeights.current[i];
        if (targetHeight > h) {
          // Fast Attack: Jump up to the new peak
          h = targetHeight;
        } else {
          // Gravity Decay: Fall back down slowly for a fluid feel
          h -= (h - targetHeight) * 0.15;
        }
        
        currentHeights.current[i] = h;
        // Apply with a tiny bit of random jitter for the "alive" feel
        const jitter = (Math.random() - 0.5) * 1.5;
        bar.style.height = `${Math.max(4, h + jitter)}px`;
      }
      animationId = requestAnimationFrame(update);
    };

    update();
    return () => cancelAnimationFrame(animationId);
  }, [active, analyser]);

  return (
    <div className="waveform-container" aria-hidden="true">
      {Array.from({ length: NUM_BARS }).map((_, i) => (
        <div
          key={i}
          ref={el => (barsRef.current[i] = el)}
          className="waveform-bar"
          style={{
            background: color,
            height: '4px', // Start at baseline
          }}
        />
      ))}
    </div>
  );
}

// ── Gemini Orb ────────────────────────────────────────────────────────────────
function GeminiOrb({ state }) {
  const gradients = {
    idle: ['#4285f4', '#9c27b0'],
    recording: ['#ea4335', '#f97316'],
    processing: ['#34a853', '#4285f4'],
    speaking: ['#8ab4f8', '#c084fc'],
  };
  const [c1, c2] = gradients[state] || gradients.idle;
  return (
    <div className={`orb-wrapper state-${state}`}>
      {(state === 'recording' || state === 'speaking') && (
        <>
          <div className="ripple ripple-1" style={{ borderColor: c1 }} />
          <div className="ripple ripple-2" style={{ borderColor: c2 }} />
          <div className="ripple ripple-3" style={{ borderColor: c1 }} />
        </>
      )}
      <div className="orb-core" style={{ background: `linear-gradient(135deg, ${c1}, ${c2})` }}>
        {state === 'idle' && (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
            <path d="M12 15c1.66 0 3-1.34 3-3V6c0-1.66-1.34-3-3-3S9 4.34 9 6v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V6z" />
            <path d="M17 12c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-2.08c3.39-.49 6-3.39 6-6.92h-2z" />
          </svg>
        )}
        {state === 'recording' && <div className="rec-dot" />}
        {state === 'processing' && (
          <div className="thinking-dots"><span /><span /><span /></div>
        )}
        {state === 'speaking' && (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
          </svg>
        )}
      </div>
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────
function MessageBubble({ msg, index }) {
  const isUser = msg.role === 'user';
  return (
    <div
      className={`bubble-row ${isUser ? 'bubble-row-user' : 'bubble-row-ai'}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {!isUser && (
        <div className="bubble-avatar">
          <img src="/logo.png" alt="FuryAI" />
        </div>
      )}
      <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-ai'}`}>
        {msg.text}
      </div>
    </div>
  );
}

// ── Auth Screen ───────────────────────────────────────────────────────────────
function AuthScreen({ onAuthSuccess }) {
  const [tab, setTab] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [isPendingOtp, setIsPendingOtp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setInfo('');
    if (!email || !password) { setError('Please enter your email and password.'); return; }
    setLoading(true);
    const endpoint = tab === 'login' ? '/api/auth/login' : '/api/auth/signup';
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Something went wrong.');
      
      if (tab === 'signup' && data.status === 'pending_otp') {
        setIsPendingOtp(true);
        setInfo('A 6-digit verification code has been sent to your email.');
      } else {
        localStorage.setItem('fury_token', data.access_token);
        localStorage.setItem('fury_user', JSON.stringify(data.user));
        onAuthSuccess(data.user, data.access_token);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError(''); setInfo('');
    if (!otp || otp.length < 6) { setError('Please enter the 6-digit code.'); return; }
    setLoading(true);
    try {
      const res = await fetch('/api/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Invalid OTP.');
      
      localStorage.setItem('fury_token', data.access_token);
      localStorage.setItem('fury_user', JSON.stringify(data.user));
      onAuthSuccess(data.user, data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (isPendingOtp) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="auth-logo">
            <img src="/logo.png" alt="FuryAI Logo" className="logo-img" />
            <span className="logo-text">Fury <span className="logo-sub">AI</span></span>
          </div>
          <h2 className="auth-otp-title">Verify Your Email</h2>
          <p className="auth-tagline">Enter the 6-digit code sent to <strong>{email}</strong></p>
          <form className="auth-form" onSubmit={handleVerifyOtp}>
            <div className="auth-field">
              <label htmlFor="auth-otp">Verification Code</label>
              <input
                id="auth-otp"
                type="text"
                className="auth-input otp-input"
                placeholder="000000"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                required
              />
            </div>
            {error && <div className="auth-error">⚠️ {error}</div>}
            {info && <div className="auth-info">✅ {info}</div>}
            <button type="submit" className="auth-btn" disabled={loading}>
              {loading ? 'Verifying…' : 'Verify & Create Account'}
            </button>
            <button
              type="button"
              className="auth-link"
              style={{ width: '100%', marginTop: '1rem' }}
              onClick={() => setIsPendingOtp(false)}
            >
              ← Back to signup
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-logo">
          <img src="/logo.png" alt="FuryAI Logo" className="logo-img" />
          <span className="logo-text">Fury <span className="logo-sub">AI</span></span>
        </div>
        <p className="auth-tagline">Your personal AI voice assistant</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="auth-email">Email</label>
            <input id="auth-email" type="email" className="auth-input" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
          </div>
          <div className="auth-field">
            <label htmlFor="auth-password">Password</label>
            <div className="password-input-wrapper">
              <input
                id="auth-password"
                type={isPasswordVisible ? 'text' : 'password'}
                className="auth-input"
                placeholder={tab === 'signup' ? 'Min. 6 characters' : 'Your password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setIsPasswordVisible(!isPasswordVisible)}
                tabIndex="-1"
                aria-label={isPasswordVisible ? 'Hide password' : 'Show password'}
              >
                {isPasswordVisible ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          {error && <div className="auth-error">⚠️ {error}</div>}
          {info && <div className="auth-info">✅ {info}</div>}
          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? (tab === 'login' ? 'Logging in…' : 'Sending OTP…') : (tab === 'login' ? 'Login' : 'Create Account')}
          </button>
        </form>
        <p className="auth-switch">
          {tab === 'login'
            ? <>New here? <button className="auth-link" onClick={() => { setTab('signup'); setError(''); setInfo(''); }}>Create an account</button></>
            : <>Already have an account? <button className="auth-link" onClick={() => { setTab('login'); setError(''); setInfo(''); }}>Login</button></>}
        </p>
      </div>
    </div>
  );
}


// ── History View ──────────────────────────────────────────────────────────────
function HistoryView({ accessToken, onSessionSelect, onBack, onUnauthorized }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sessionToDelete, setSessionToDelete] = useState(null);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/auth/sessions', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.status === 401) {
        if (onUnauthorized) onUnauthorized();
        return;
      }
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to load sessions.');
      setSessions(data.sessions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [accessToken]);

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation(); // Prevents card click
    setSessionToDelete(sessionId);
  };

  const confirmDelete = async () => {
    if (!sessionToDelete) return;
    try {
      const res = await fetch(`/api/auth/sessions/${sessionToDelete}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.session_id !== sessionToDelete));
        setSessionToDelete(null);
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to delete session.");
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  };


  return (
    <div className="history-view">
      {/* History Header */}
      <div className="history-header">
        <button className="history-back-btn" onClick={onBack} id="history-back-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z" />
          </svg>
          Back
        </button>
        <h2 className="history-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" />
          </svg>
          Your Conversations
        </h2>
        <div className="history-count">
          {sessions.length} chats
        </div>
      </div>

      {/* Sessions list */}
      <div className="history-body">
        {loading && (
          <div className="history-loading">
            <div className="history-spinner" />
            <p>Gathering your thoughts…</p>
          </div>
        )}

        {!loading && error && (
          <div className="history-empty">
            <p>⚠️ {error}</p>
          </div>
        )}

        {!loading && !error && sessions.length === 0 && (
          <div className="history-empty">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.2 }}>
              <path d="M12 15c1.66 0 3-1.34 3-3V6c0-1.66-1.34-3-3-3S9 4.34 9 6v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V6z" />
              <path d="M17 12c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-2.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
            <p>No conversations yet.</p>
            <p className="history-empty-sub">Start a chat to see it listed here!</p>
          </div>
        )}
        {!loading && !error && sessions.map((session) => (
          <div key={session.session_id} className="session-card-wrapper">
            <button 
              className="session-card"
              onClick={() => onSessionSelect(session.session_id)}
            >
              <div className="session-card-info">
                <h3 className="session-card-title">{session.session_title || "New Conversation"}</h3>
                <p className="session-card-preview">{session.last_message}</p>
              </div>
              <div className="session-card-meta">
                <span className="session-card-date">
                  {new Date(session.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </span>
                <div 
                  className="session-card-delete-inline" 
                  onClick={(e) => handleDeleteSession(e, session.session_id)}
                  title="Delete conversation"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                  </svg>
                </div>
                <svg className="card-arrow" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z" />
                </svg>
              </div>
            </button>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Modal */}
      {sessionToDelete && (
        <div className="confirm-overlay">
          <div className="confirm-dialog">
            <h3>Delete Conversation?</h3>
            <p>This will permanently remove this chat history. This action cannot be undone.</p>
            <div className="confirm-actions">
              <button className="confirm-btn-cancel" onClick={() => setSessionToDelete(null)}>Cancel</button>
              <button className="confirm-btn-delete" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [view, setView] = useState('chat'); // 'chat' | 'history'
  const [orbState, setOrbState] = useState('idle');
  const [history, setHistory] = useState([]);
  const [statusText, setStatusText] = useState('Tap the microphone to begin');
  const [error, setError] = useState('');
  const [currentSessionId, setCurrentSessionId] = useState(crypto.randomUUID());
  const [sessionToDelete, setSessionToDelete] = useState(null); // Used for history view and current session deletion

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef(null);
  const chatEndRef = useRef(null);
  const audioRef = useRef(new Audio()); // Reuse one audio instance for better visualizer performance
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const micSourceRef = useRef(null);
  const aiSourceRef = useRef(null);

  // Initialize Audio Context on first interaction
  const initAudio = () => {
    if (audioCtxRef.current) return;
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512; // Higher resolution for more "life"
    analyser.smoothingTimeConstant = 0.4; // Responsive smoothing balance
    audioCtxRef.current = ctx;
    analyserRef.current = analyser;

    // Connect AI audio element
    if (audioRef.current) {
      const source = ctx.createMediaElementSource(audioRef.current);
      source.connect(analyser); // For visualization
      source.connect(ctx.destination); // For hearing AI response
      aiSourceRef.current = source;
    }
  };

  // Auto-login from localStorage
  useEffect(() => {
    const savedToken = localStorage.getItem('fury_token');
    const savedUser = localStorage.getItem('fury_user');
    if (savedToken && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
        setAccessToken(savedToken);
      } catch {
        localStorage.removeItem('fury_token');
        localStorage.removeItem('fury_user');
      }
    }
  }, []);

  // Initialize fresh chat on startup
  useEffect(() => {
    if (!user || !accessToken) return;
    if (history.length === 0) {
      setHistory([{ role: 'ai', text: `Hi! I'm Fury AI, your voice assistant. Try saying something!` }]);
    }
  }, [user, accessToken]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  const handleSessionSelect = async (sessionId) => {
    setView('chat');
    setCurrentSessionId(sessionId);
    setHistory([]);
    try {
      const res = await fetch(`/api/auth/history?session_id=${sessionId}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      const data = await res.json();
      if (data.history) {
        setHistory(data.history.map((h) => ({
          role: h.role === 'assistant' ? 'ai' : 'user',
          text: h.message,
        })));
      }
    } catch (err) {
      console.error("Failed to load session history:", err);
    }
  };

  const startNewChat = () => {
    setCurrentSessionId(crypto.randomUUID());
    setHistory([{ role: 'ai', text: "New conversation started! How can I help you today?" }]);
    setView('chat');
  };

  const handleAuthSuccess = (userData, token) => {
    setUser(userData);
    setAccessToken(token);
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
    } catch { }
    localStorage.removeItem('fury_token');
    localStorage.removeItem('fury_user');
    setUser(null);
    setAccessToken(null);
    setHistory([]);
    setOrbState('idle');
    setView('chat');
    setCurrentSessionId(crypto.randomUUID());
  };

  const startRecording = useCallback(async () => {
    setError('');
    initAudio();
    if (audioCtxRef.current.state === 'suspended') {
      await audioCtxRef.current.resume();
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Connect mic to visualizer (WITHOUT connecting to destination/speakers)
      if (micSourceRef.current) micSourceRef.current.disconnect();
      const source = audioCtxRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      micSourceRef.current = source;

      const options = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? { mimeType: 'audio/webm;codecs=opus' } : {};
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];
      mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      mediaRecorderRef.current.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (micSourceRef.current) {
          micSourceRef.current.disconnect();
          micSourceRef.current = null;
        }
        await processVoice(new Blob(audioChunksRef.current, { type: 'audio/webm' }));
      };
      mediaRecorderRef.current.start(200);
      setOrbState('recording');
      setStatusText('Listening… tap again to send');
    } catch {
      setError('Microphone access denied. Please allow microphone permissions and refresh.');
      setOrbState('idle');
    }
  }, [accessToken]);

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
      const res = await fetch('/api/voice/process', {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${accessToken}`,
          'X-Session-ID': currentSessionId
        },
        body: formData,
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      setHistory((prev) => [...prev, { role: 'user', text: data.transcript }, { role: 'ai', text: data.ai_text }]);
      if (data.audio_base64) {
        setOrbState('speaking');
        setStatusText('Fury AI is speaking…');
        
        // Update reused audio element instead of creating new one
        if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
          await audioCtxRef.current.resume();
        }
        
        audioRef.current.src = `data:audio/mp3;base64,${data.audio_base64}`;
        audioRef.current.onended = () => { setOrbState('idle'); setStatusText('Tap the microphone to begin'); };
        audioRef.current.onerror = () => { setOrbState('idle'); setStatusText('Tap the microphone to begin'); };
        audioRef.current.play().catch(() => { });
      } else {
        setOrbState('idle');
        setStatusText('Tap the microphone to begin');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
      setOrbState('idle');
      setStatusText('Tap the microphone to begin');
    }
  };

  const handleMicClick = () => { if (orbState === 'recording') stopRecording(); else if (orbState === 'idle') startRecording(); };
  const stopSpeaking = () => { if (audioRef.current) { audioRef.current.pause(); audioRef.current.currentTime = 0; } setOrbState('idle'); setStatusText('Tap the microphone to begin'); };
  const clearHistory = () => setHistory([{ role: 'ai', text: 'Conversation cleared. How can I help you?' }]);



  // ── Auth Screen ──────────────────────────────────────────────────────────
  if (!user) return <AuthScreen onAuthSuccess={handleAuthSuccess} />;

  // ── History View ─────────────────────────────────────────────────────────
  if (view === 'history') {
    return (
      <div className="app">
        <header className="app-header">
          <div className="logo">
            <img src="/logo.png" alt="FuryAI Logo" className="logo-img" />
            <span className="logo-text">Fury <span className="logo-sub">AI</span></span>
          </div>
          <nav className="header-nav">
            <div className="user-badge">
              <div className="user-avatar">{user.email[0].toUpperCase()}</div>
              <span className="user-email">{user.email}</span>
            </div>
            <button className="nav-btn nav-btn-logout" onClick={handleLogout}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" />
              </svg>
              Logout
            </button>
          </nav>
        </header>
        <HistoryView 
          accessToken={accessToken} 
          onSessionSelect={handleSessionSelect}
          onBack={() => setView('chat')} 
          onUnauthorized={handleLogout}
        />
        <footer className="app-footer">
          <p>© 2026 Fayaz Ahmed Shaik. All rights reserved.</p>
        </footer>
      </div>
    );
  }

  // ── Main Chat View ───────────────────────────────────────────────────────
  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <img src="/logo.png" alt="FuryAI Logo" className="logo-img" />
          <span className="logo-text">Fury <span className="logo-sub">AI</span></span>
        </div>
        <nav className="header-nav">
          <div className="user-badge">
            <div className="user-avatar">{user.email[0].toUpperCase()}</div>
            <span className="user-email">{user.email}</span>
          </div>
          <button className="nav-btn nav-btn-new" onClick={startNewChat} title="Start fresh conversation">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
            </svg>
            New Chat
          </button>
          <button className="nav-btn" id="history-tab-btn" onClick={() => setView('history')} title="View past chats">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" />
            </svg>
            History
          </button>
          <button className="nav-btn" id="clear-chat-btn" onClick={clearHistory} title="Clear chat">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
            </svg>
            Clear
          </button>
          <button className="nav-btn nav-btn-logout" id="logout-btn" onClick={handleLogout} title="Logout">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" />
            </svg>
            Logout
          </button>
        </nav>
      </header>

      <main className="app-main">
        <section className="chat-section">
          <div className="chat-messages">
            {history.map((msg, i) => <MessageBubble key={i} msg={msg} index={i} />)}
            <div ref={chatEndRef} />
          </div>
        </section>
        <section className="voice-stage">
          <div className={`waveform-area waveform-top ${orbState === 'recording' ? 'wf-visible' : ''}`}>
            <VoiceWaveform active={orbState === 'recording'} color="#ea4335" analyser={analyserRef.current} />
          </div>
          <button
            className={`orb-btn ${orbState === 'processing' ? 'orb-btn-inactive' : ''}`}
            onClick={orbState === 'speaking' ? stopSpeaking : handleMicClick}
            disabled={orbState === 'processing'}
            aria-label={orbState === 'recording' ? 'Stop recording' : 'Start recording'}
          >
            <GeminiOrb state={orbState} />
          </button>
          <div className={`waveform-area waveform-bottom ${orbState === 'speaking' ? 'wf-visible' : ''}`}>
            <VoiceWaveform active={orbState === 'speaking'} color="#8ab4f8" analyser={analyserRef.current} />
          </div>
          <p className="status-text">{statusText}</p>
          {error && (
            <div className="error-banner">
              <span>⚠️ {error}</span>
              <button onClick={() => setError('')}>✕</button>
            </div>
          )}
        </section>
      </main>

      <footer className="app-footer">
        <p>© 2026 Fayaz Ahmed Shaik. All rights reserved.</p>
      </footer>
    </div>
  );
}
