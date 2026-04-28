import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

const sidebarItems = [
  { key: 'dashboard', label: 'Dashboard', icon: 'dashboard', path: '/dashboard' },
  { key: 'diary', label: 'Diary', icon: 'book_5', path: '/diary' },
  { key: 'insights', label: 'Insights', icon: 'insights', path: '/insights' },
  { key: 'chatbot', label: 'AI Chat', icon: 'chat_bubble', path: '/chatbot', active: true },
  { key: 'settings', label: 'Settings', icon: 'settings', path: '/settings' },
];

const MODES = [
  { key: 'daily', label: 'Today', icon: 'today' },
  { key: 'weekly', label: 'This Week', icon: 'date_range' },
  { key: 'general', label: 'Last 30 Days', icon: 'calendar_month' },
];

const QUICK_PROMPTS = [
  { label: 'Weekly summary', message: "Give me a summary of this week's entries.", mode: 'weekly' },
  { label: "Today's mood", message: 'How was my mood today based on my entries?', mode: 'daily' },
  { label: 'Recurring themes', message: 'What topics or themes keep coming up in my diary?', mode: 'general' },
  { label: 'Suggestions', message: 'Based on my recent entries, what lifestyle suggestions do you have?', mode: 'general' },
  { label: 'Emotional pattern', message: 'What emotional patterns do you notice in my writing this week?', mode: 'weekly' },
  { label: 'Positive moments', message: 'What positive moments or progress did I write about recently?', mode: 'general' },
];

const formatTime = () =>
  new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

const getAudioMimeType = () => {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg', 'audio/mp4'];
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || '';
};

const Chatbot = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mode, setMode] = useState('weekly');
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      text: "Hi! I'm your MindTrackAI companion. I've been reading your diary entries and I'm ready to reflect on them with you. Ask me for a weekly summary, mood patterns, recurring themes, or anything else. What would you like to explore?",
      time: formatTime(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Voice state
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
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cleanup on unmount
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

      recorder.ondataavailable = (e) => {
        if (e.data?.size) audioChunksRef.current.push(e.data);
      };
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
      if (!audioBlob.size) {
        setIsTranscribing(false);
        return;
      }

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

  const sendMessage = useCallback(
    async (text, overrideMode) => {
      const trimmed = (text || input).trim();
      if (!trimmed || isLoading) return;

      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: 'user', text: trimmed, time: formatTime() },
      ]);
      setInput('');
      setIsLoading(true);

      try {
        const res = await api.post('/chatbot/chat', {
          message: trimmed,
          mode: overrideMode || mode,
          date: new Date().toISOString().split('T')[0],
        });

        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            text: res.data.response,
            usedMemory: res.data.used_analysis_memory,
            time: formatTime(),
          },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            text: 'Sorry, I could not reach the AI service right now. Please try again in a moment.',
            isError: true,
            time: formatTime(),
          },
        ]);
      } finally {
        setIsLoading(false);
        setTimeout(() => inputRef.current?.focus(), 50);
      }
    },
    [input, mode, isLoading]
  );

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleQuickPrompt = (prompt) => {
    setMode(prompt.mode);
    sendMessage(prompt.message, prompt.mode);
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        text: 'Chat cleared. What would you like to explore about your diary?',
        time: formatTime(),
      },
    ]);
  };

  const formatDuration = (s) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  return (
    <div className="h-screen overflow-hidden bg-background-light text-text-primary-light dark:bg-background-dark dark:text-text-primary-dark lg:flex">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col justify-between bg-blue-900 px-6 py-6 text-white shadow-2xl transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } overflow-y-auto`}
      >
        <div className="flex flex-col gap-8">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-3xl">self_improvement</span>
            <span className="font-display text-xl font-bold tracking-wide">MindTrackAi</span>
          </div>

          <nav className="flex flex-col gap-2">
            {sidebarItems.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => {
                  if (item.path) { navigate(item.path); setSidebarOpen(false); }
                }}
                className={`flex items-center gap-3 rounded-xl px-4 py-3 text-left font-medium transition-all ${
                  item.active
                    ? 'bg-blue-500/30 text-white'
                    : item.path
                    ? 'text-blue-100 hover:bg-white/10'
                    : 'cursor-not-allowed text-blue-200/60'
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="rounded-2xl bg-white/10 p-4">
          <p className="mb-1 text-xs font-bold uppercase tracking-widest text-blue-200">AI Memory</p>
          <p className="text-xs text-blue-100/80">
            Diary entries are analyzed in the background. The chat uses pre-computed summaries for fast responses.
          </p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex h-full flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex shrink-0 items-center justify-between border-b border-slate-100 bg-white px-4 py-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200 lg:hidden"
            >
              <span className="material-symbols-outlined text-lg">menu</span>
            </button>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-900/40">
              <span className="material-symbols-outlined text-lg text-blue-600 dark:text-blue-300">chat_bubble</span>
            </div>
            <div>
              <h1 className="font-display text-base font-bold text-slate-800 dark:text-white">AI Companion</h1>
              <p className="text-xs text-slate-400">Reflects on your diary with you</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800 sm:flex">
              {MODES.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => setMode(m.key)}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                    mode === m.key
                      ? 'bg-white text-blue-700 shadow-sm dark:bg-slate-700 dark:text-blue-300'
                      : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  <span className="material-symbols-outlined text-[14px]">{m.icon}</span>
                  {m.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={clearChat}
              title="Clear chat"
              className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <span className="material-symbols-outlined text-lg">restart_alt</span>
            </button>
          </div>
        </header>

        {/* Mode tabs mobile */}
        <div className="flex shrink-0 items-center gap-1 border-b border-slate-100 bg-white px-4 py-2 dark:border-slate-800 dark:bg-slate-900 sm:hidden">
          {MODES.map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => setMode(m.key)}
              className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition-all ${
                mode === m.key
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                  : 'text-slate-500'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Messages */}
        <div className="custom-scrollbar flex-1 overflow-y-auto px-4 py-6 md:px-6">
          <div className="mx-auto max-w-2xl space-y-4">
            {messages.length === 1 && (
              <div className="mb-6">
                <p className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400">Quick questions</p>
                <div className="flex flex-wrap gap-2">
                  {QUICK_PROMPTS.map((prompt) => (
                    <button
                      key={prompt.label}
                      type="button"
                      onClick={() => handleQuickPrompt(prompt)}
                      disabled={isLoading}
                      className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition-all hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-blue-900/20 dark:hover:text-blue-300"
                    >
                      {prompt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                {msg.role === 'assistant' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/50">
                    <span className="material-symbols-outlined text-sm text-blue-600 dark:text-blue-300">self_improvement</span>
                  </div>
                )}
                <div className={`flex max-w-[80%] flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : msg.isError
                        ? 'border border-rose-100 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300'
                        : 'border border-slate-100 bg-white text-slate-700 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                    }`}
                  >
                    {msg.text}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400">{msg.time}</span>
                    {msg.usedMemory && (
                      <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400">
                        <span className="material-symbols-outlined text-[10px]">memory</span>
                        from memory
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/50">
                  <span className="material-symbols-outlined text-sm text-blue-600 dark:text-blue-300">self_improvement</span>
                </div>
                <div className="flex items-center gap-1.5 rounded-2xl border border-slate-100 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 dark:bg-slate-500" style={{ animationDelay: '0ms' }} />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 dark:bg-slate-500" style={{ animationDelay: '150ms' }} />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 dark:bg-slate-500" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="shrink-0 border-t border-slate-100 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900 md:px-6">
          <div className="mx-auto max-w-2xl space-y-2">
            {/* Voice error */}
            {voiceError && (
              <p className="rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-600 dark:bg-rose-900/20 dark:text-rose-300">
                {voiceError}
              </p>
            )}

            {/* Recording indicator */}
            {(isRecording || isTranscribing) && (
              <div className="flex items-center gap-2 rounded-xl bg-red-50 px-3 py-2 dark:bg-red-900/20">
                {isRecording && (
                  <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
                )}
                <span className="text-xs font-semibold text-red-600 dark:text-red-300">
                  {isTranscribing ? 'Whisper is transcribing...' : `Recording ${formatDuration(recordSeconds)}`}
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

            <div className="flex items-end gap-2">
              {/* Text input */}
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isTranscribing ? 'Transcribing...' : 'Ask about your diary entries...'}
                disabled={isLoading || isTranscribing}
                className="flex-1 resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:focus:border-blue-600 dark:focus:ring-blue-900/30"
                style={{ maxHeight: '120px' }}
                onInput={(e) => {
                  e.target.style.height = 'auto';
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                }}
              />

              {/* Mic button */}
              {speechSupported && (
                <button
                  type="button"
                  onClick={isRecording ? stopAndTranscribe : startRecording}
                  disabled={isTranscribing || isLoading}
                  title={isRecording ? 'Stop recording' : 'Start voice input'}
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
                    isRecording
                      ? 'bg-red-500 text-white shadow-md shadow-red-500/30 animate-pulse'
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700'
                  }`}
                >
                  <span className="material-symbols-outlined text-lg">
                    {isRecording ? 'stop' : 'mic'}
                  </span>
                </button>
              )}

              {/* Send button */}
              <button
                type="button"
                onClick={() => sendMessage()}
                disabled={!input.trim() || isLoading}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-md shadow-blue-600/20 transition-all hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-lg">send</span>
              </button>
            </div>

            <p className="text-center text-[10px] text-slate-400">
              Enter to send · Shift+Enter for new line · Mode:{' '}
              <strong>{MODES.find((m) => m.key === mode)?.label}</strong>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Chatbot;
