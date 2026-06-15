import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import Sidebar from '../components/Sidebar';
import { SUGGESTION_CHIPS } from '../constants/insights';
import { formatTime, formatRelative, getAudioMimeType, formatDuration } from '../utils/insightsHelpers';

// Renders **bold** and *italic* markdown emphasis while leaving newlines
// and other punctuation alone. The double-asterisk split runs first so that
// **bold** never gets eaten by the single-asterisk italic pattern.
const renderRichText = (text) => {
  if (!text) return null;
  const boldParts = text.split(/(\*\*[^*\n]+\*\*)/g);
  return boldParts.flatMap((boldPart, boldIdx) => {
    if (boldPart.startsWith('**') && boldPart.endsWith('**')) {
      return <strong key={`b-${boldIdx}`}>{boldPart.slice(2, -2)}</strong>;
    }
    // For non-bold segments, split out single-asterisk italics.
    const italicParts = boldPart.split(/(\*[^*\n]+\*)/g);
    return italicParts.map((italicPart, italicIdx) => {
      if (
        italicPart.startsWith('*') &&
        italicPart.endsWith('*') &&
        italicPart.length > 2
      ) {
        return <em key={`b-${boldIdx}-i-${italicIdx}`}>{italicPart.slice(1, -1)}</em>;
      }
      return (
        <React.Fragment key={`b-${boldIdx}-t-${italicIdx}`}>{italicPart}</React.Fragment>
      );
    });
  });
};

const Insights = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionError, setSessionError] = useState('');
  const [currentSession, setCurrentSession] = useState(null);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState('');
  const [recordSeconds, setRecordSeconds] = useState(0);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioMimeTypeRef = useRef('');
  const timerRef = useRef(null);

  const speechSupported =
    typeof window !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) navigate('/auth');
  }, [navigate]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    setSessionsLoading(true);
    api.get('/chatbot/sessions')
      .then((res) => setSessions(res.data?.sessions || []))
      .catch((err) => {
        const detail = err?.response?.data?.detail;
        setSessionError(typeof detail === 'string' ? detail : 'Failed to load chat sessions.');
      })
      .finally(() => setSessionsLoading(false));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      clearInterval(timerRef.current);
    };
  }, []);

  const stopMediaStream = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
  };

  const stopRecorder = () =>
    new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      const mimeType = audioMimeTypeRef.current || recorder?.mimeType || 'audio/webm';
      if (!recorder || recorder.state === 'inactive') {
        stopMediaStream();
        resolve(new Blob(audioChunksRef.current, { type: mimeType }));
        return;
      }
      recorder.onstop = () => {
        stopMediaStream();
        mediaRecorderRef.current = null;
        resolve(new Blob(audioChunksRef.current, { type: mimeType }));
      };
      recorder.stop();
    });

  const startRecording = async () => {
    if (!speechSupported || isRecording || isTranscribing) return;
    setVoiceError('');
    setRecordSeconds(0);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getAudioMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      audioMimeTypeRef.current = mimeType || recorder.mimeType || 'audio/webm';
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => { if (e.data?.size) audioChunksRef.current.push(e.data); };
      recorder.onerror = () => {
        setVoiceError('Recording failed. Please try again.');
        clearInterval(timerRef.current);
        stopMediaStream();
        setIsRecording(false);
      };

      recorder.start(1000);
      setIsRecording(true);
      timerRef.current = setInterval(() => setRecordSeconds((s) => s + 1), 1000);
    } catch {
      setVoiceError('Microphone access was blocked or unavailable.');
    }
  };

  const stopAndTranscribe = async () => {
    if (!mediaRecorderRef.current) return;
    clearInterval(timerRef.current);
    setIsRecording(false);
    setIsTranscribing(true);

    try {
      const audioBlob = await stopRecorder();
      if (!audioBlob.size) { setIsTranscribing(false); return; }

      const ext = audioBlob.type.includes('ogg') ? 'ogg' : audioBlob.type.includes('mp4') ? 'mp4' : 'webm';
      const formData = new FormData();
      formData.append('audio_file', audioBlob, `voice.${ext}`);
      formData.append('language_code', 'auto');

      const res = await api.post('/diary/speech-to-text', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const transcript = (res.data?.transcript || '').trim();
      if (transcript) {
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
        setTimeout(() => inputRef.current?.focus(), 50);
      }
    } catch {
      setVoiceError('Transcription failed. Please try again.');
    } finally {
      setIsTranscribing(false);
      setRecordSeconds(0);
    }
  };

  const ensureSession = async () => {
    if (currentSession?.id) return currentSession;
    const res = await api.post('/chatbot/sessions', { title: 'New Chat' });
    const created = res.data;
    if (!created?.id) throw new Error('Invalid session response');
    setSessions((prev) => [created, ...prev]);
    setCurrentSession(created);
    setMessages([]);
    return created;
  };

  const sendMessage = async (messageText, mode = 'general') => {
    const text = (messageText || input).trim();
    if (!text || loading) return;

    let session;
    try {
      session = await ensureSession();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setSessionError(typeof detail === 'string' ? detail : 'Could not start a new chat.');
      return;
    }

    const userTime = new Date().toISOString();
    setMessages((prev) => [...prev, { role: 'user', text, time: userTime }]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.post('/chatbot/chat', {
        session_id: session.id,
        message: text,
        mode,
      });
      const assistantTime = new Date().toISOString();
      setMessages((prev) => [...prev, { role: 'assistant', text: response.data.response, time: assistantTime }]);
      setSessions((prev) =>
        prev.map((s) =>
          s.id === session.id
            ? { ...s, last_activity: assistantTime, title: s.title === 'New Chat' ? text.slice(0, 60) : s.title }
            : s,
        ),
      );
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'AI service is currently unavailable. Please try again in a moment.', time: new Date().toISOString() },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewChat = async () => {
    if (loading) return;
    setSessionError('');
    try {
      const res = await api.post('/chatbot/sessions', { title: 'New Chat' });
      const created = res.data;
      if (!created?.id) {
        setSessionError('Session was created with an invalid response.');
        return;
      }
      setSessions((prev) => [created, ...prev]);
      setCurrentSession(created);
      setMessages([]);
      setHistoryOpen(false);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setSessionError(typeof detail === 'string' ? detail : 'Could not create a new chat session.');
    }
  };

  const openSession = async (sessionId) => {
    if (!sessionId) return;
    setSessionError('');
    try {
      const res = await api.get(`/chatbot/sessions/${sessionId}`);
      setCurrentSession({ id: res.data.id, title: res.data.title, updated_at: res.data.updated_at });
      setMessages((res.data.messages || []).map((m) => ({ role: m.role, text: m.text })));
      setHistoryOpen(false);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setSessionError(typeof detail === 'string' ? detail : 'Could not open this chat session.');
    }
  };

  const deleteSession = async (sessionId) => {
    setSessionError('');
    try {
      await api.delete(`/chatbot/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setSessionError(typeof detail === 'string' ? detail : 'Could not delete this session.');
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background-light text-text-primary-light dark:bg-background-dark dark:text-text-primary-dark">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        footerSlot={
          <div className="rounded-2xl bg-white/10 px-4 py-3">
            <p className="text-[11px] text-blue-200">
              Aura analyzes your diary entries to suggest lifestyle patterns and activities.
            </p>
          </div>
        }
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between gap-3 border-b border-slate-200/60 bg-white/80 backdrop-blur-md px-4 py-4 dark:border-slate-800 dark:bg-slate-900/80 md:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200 lg:hidden"
            >
              <span className="material-symbols-outlined">menu</span>
            </button>
            <h1 className="font-display text-lg font-black text-slate-800 dark:text-white">Aura</h1>
          </div>
          <button
            type="button"
            onClick={() => setHistoryOpen(true)}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 md:hidden"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>history</span>
            History
          </button>
        </header>

        <main className="relative flex flex-1 overflow-hidden">
          {/* Chat history sidebar (desktop) + drawer (mobile) */}
          {historyOpen && (
            <button
              type="button"
              aria-label="Close history"
              onClick={() => setHistoryOpen(false)}
              className="fixed inset-0 z-40 bg-slate-900/40 md:hidden"
            />
          )}
          <section
            className={`fixed inset-y-0 left-0 z-50 flex w-80 shrink-0 flex-col border-r border-slate-200/60 bg-slate-50 transition-transform duration-200 dark:border-slate-700/60 dark:bg-slate-900 md:static md:translate-x-0 ${
              historyOpen ? 'translate-x-0' : '-translate-x-full'
            } md:flex`}
          >
            <div className="flex items-center justify-between p-6 pb-3 md:pb-6">
              <button
                type="button"
                onClick={startNewChat}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 py-3 font-semibold text-white shadow-md transition-all hover:bg-blue-700 hover:shadow-lg active:scale-[0.98] disabled:opacity-50"
              >
                <span className="material-symbols-outlined">add</span>
                New Chat
              </button>
              <button
                type="button"
                onClick={() => setHistoryOpen(false)}
                className="ml-2 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 md:hidden"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="px-6 pb-2">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">Previous Discussions</p>
            </div>
            <div className="custom-scrollbar flex-1 space-y-2 overflow-y-auto px-4 pb-4">
              {sessionError && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700 dark:border-rose-800/60 dark:bg-rose-900/20 dark:text-rose-200">
                  {sessionError}
                </div>
              )}
              {sessionsLoading && (
                <div className="rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                  Loading…
                </div>
              )}
              {!sessionsLoading && !sessionError && sessions.length === 0 && (
                <p className="px-2 py-4 text-xs text-slate-500 dark:text-slate-400">
                  No chats yet. Click <span className="font-semibold">+ New Chat</span> to start one.
                </p>
              )}
              {sessions.map((s) => {
                const active = currentSession?.id === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => openSession(s.id)}
                    className={`group cursor-pointer rounded-2xl p-4 transition-all ${
                      active
                        ? 'border border-blue-600/15 bg-white shadow-sm dark:border-blue-500/20 dark:bg-slate-800'
                        : 'hover:bg-white dark:hover:bg-slate-800'
                    }`}
                  >
                    <div className="mb-1 flex items-start justify-between gap-2">
                      <h4
                        className={`flex-1 truncate text-sm ${
                          active
                            ? 'font-bold text-slate-800 dark:text-slate-100'
                            : 'font-semibold text-slate-700 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-blue-400'
                        }`}
                      >
                        {s.title || 'New Chat'}
                      </h4>
                      <span className="shrink-0 whitespace-nowrap text-[10px] text-slate-500 dark:text-slate-400">
                        {formatRelative(s.last_activity || s.updated_at)}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                      className="text-[10px] text-slate-400 opacity-0 transition-opacity hover:text-rose-500 group-hover:opacity-100"
                      title="Delete session"
                    >
                      Delete
                    </button>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Active chat window */}
          <section className="relative flex flex-1 flex-col overflow-hidden bg-white dark:bg-slate-950">
            {/* Messages */}
            <div className="custom-scrollbar relative z-10 flex-1 space-y-6 overflow-y-auto p-6 md:p-8">
              {messages.length === 0 && !loading && (
                <div className="flex h-full items-center justify-center">
                  <div className="max-w-md text-center">
                    <div className="mx-auto mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-100 dark:bg-blue-900/40">
                      <span className="material-symbols-outlined text-3xl text-blue-600 dark:text-blue-300">forum</span>
                    </div>
                    <h2 className="font-display text-2xl font-bold text-slate-800 dark:text-white">
                      {currentSession ? 'Start typing or pick a suggestion' : 'Start a conversation'}
                    </h2>
                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                      I'll look through your diary — themes, mood patterns, and activity ideas. Ask me anything.
                    </p>
                  </div>
                </div>
              )}

              {messages.map((msg, i) =>
                msg.role === 'assistant' ? (
                  <div key={i} className="flex max-w-[85%] items-end gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/40">
                      <span className="material-symbols-outlined text-sm text-blue-600 dark:text-blue-300">smart_toy</span>
                    </div>
                    <div className="space-y-1">
                      <div className="rounded-2xl rounded-bl-none border border-slate-200/40 bg-slate-50 p-4 shadow-sm dark:border-slate-700/40 dark:bg-slate-800">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800 dark:text-slate-100">{renderRichText(msg.text)}</p>
                      </div>
                      <span className="ml-1 text-[10px] font-medium uppercase text-slate-500 dark:text-slate-400">
                        Aura{msg.time ? ` • ${formatTime(msg.time)}` : ''}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div key={i} className="ml-auto flex max-w-[85%] flex-row-reverse items-end gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/20">
                      <span className="material-symbols-outlined text-sm text-blue-600 dark:text-blue-300">person</span>
                    </div>
                    <div className="space-y-1 text-right">
                      <div className="rounded-2xl rounded-br-none bg-blue-600 p-4 text-white shadow-md">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed">{renderRichText(msg.text)}</p>
                      </div>
                      <span className="mr-1 text-[10px] font-medium uppercase text-slate-500 dark:text-slate-400">
                        You{msg.time ? ` • ${formatTime(msg.time)}` : ''}
                      </span>
                    </div>
                  </div>
                ),
              )}

              {loading && (
                <div className="flex max-w-[85%] items-end gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/40">
                    <span className="material-symbols-outlined text-sm text-blue-600 dark:text-blue-300">smart_toy</span>
                  </div>
                  <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-none border border-slate-200/40 bg-slate-50 p-4 shadow-sm dark:border-slate-700/40 dark:bg-slate-800">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 dark:bg-slate-500" style={{ animationDelay: '0ms' }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 dark:bg-slate-500" style={{ animationDelay: '150ms' }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 dark:bg-slate-500" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="relative z-10 border-t border-slate-200/60 bg-white p-4 dark:border-slate-800 dark:bg-slate-950 md:p-6">
              {voiceError && (
                <p className="mb-3 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-600 dark:bg-rose-900/20 dark:text-rose-300">
                  {voiceError}
                </p>
              )}

              {(isRecording || isTranscribing) && (
                <div className="mb-3 flex items-center gap-2 rounded-xl bg-red-50 px-3 py-2 dark:bg-red-900/20">
                  {isRecording && <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />}
                  <span className="text-xs font-semibold text-red-600 dark:text-red-300">
                    {isTranscribing ? 'Whisper is transcribing…' : `Recording ${formatDuration(recordSeconds)}`}
                  </span>
                  {isRecording && (
                    <button
                      type="button"
                      onClick={stopAndTranscribe}
                      className="ml-auto text-xs font-bold text-red-600 underline dark:text-red-300"
                    >
                      Stop
                    </button>
                  )}
                </div>
              )}

              <div className="mb-4 flex flex-wrap gap-2">
                {SUGGESTION_CHIPS.map((chip) => (
                  <button
                    key={chip.label}
                    type="button"
                    onClick={() => sendMessage(chip.message, chip.mode)}
                    disabled={loading || isTranscribing}
                    className="flex items-center gap-2 rounded-full border border-blue-600/20 bg-blue-50 px-4 py-2 text-xs font-semibold text-blue-600 transition-all hover:bg-blue-600 hover:text-white disabled:cursor-not-allowed disabled:opacity-40 dark:border-blue-500/30 dark:bg-blue-900/20 dark:text-blue-300 dark:hover:bg-blue-600 dark:hover:text-white"
                  >
                    <span className="material-symbols-outlined text-sm">{chip.icon}</span>
                    {chip.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2 rounded-3xl border border-slate-200 bg-white p-2 shadow-lg transition-all focus-within:ring-2 focus-within:ring-blue-600/20 dark:border-slate-700 dark:bg-slate-900">
                {speechSupported && (
                  <button
                    type="button"
                    onClick={isRecording ? stopAndTranscribe : startRecording}
                    disabled={isTranscribing || loading}
                    title={isRecording ? 'Stop recording' : 'Voice input'}
                    className={`p-3 transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                      isRecording
                        ? 'text-red-500'
                        : 'text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400'
                    }`}
                  >
                    <span className="material-symbols-outlined">{isRecording ? 'stop' : 'mic'}</span>
                  </button>
                )}
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isTranscribing ? 'Transcribing…' : 'Share your thoughts or ask for advice…'}
                  disabled={isTranscribing || loading}
                  className="flex-1 border-none bg-transparent py-4 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-0 disabled:opacity-60 dark:text-slate-100"
                />
                <button
                  type="button"
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || loading}
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-sm transition-all hover:bg-blue-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <span className="material-symbols-outlined" style={{ fontVariationSettings: '"FILL" 1' }}>send</span>
                </button>
              </div>

            </div>
          </section>
        </main>
      </div>
    </div>
  );
};

export default Insights;
