import React, { useEffect, useRef, useState } from 'react';
import api from '../api/axios';

const MOOD_OPTIONS = [
  { value: 'Joyful', icon: 'sentiment_satisfied' },
  { value: 'Calm', icon: 'self_improvement' },
  { value: 'Grounded', icon: 'eco' },
  { value: 'Inspired', icon: 'auto_awesome' },
  { value: 'Tired', icon: 'bedtime' },
  { value: 'Anxious', icon: 'psychology_alt' },
  { value: 'Sad', icon: 'sentiment_dissatisfied' },
];

const todayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const getAudioMimeType = () => {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg', 'audio/mp4'];
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || '';
};

const formatDuration = (s) =>
  `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

const NewDiaryEntry = ({ open, onClose, onCreated, defaultDate }) => {
  const [form, setForm] = useState(() => ({
    title: '',
    content: '',
    mood: '',
    tags: '',
    entry_date: defaultDate || todayISO(),
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState('');
  const [recordSeconds, setRecordSeconds] = useState(0);

  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioMimeTypeRef = useRef('');
  const timerRef = useRef(null);

  const speechSupported =
    typeof window !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);

  // Reset form whenever the modal is opened.
  useEffect(() => {
    if (open) {
      setForm({ title: '', content: '', mood: '', tags: '', entry_date: defaultDate || todayISO() });
      setError('');
      setVoiceError('');
      setRecordSeconds(0);
    }
  }, [open, defaultDate]);

  // Cleanup recording resources on unmount.
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
        setForm((f) => ({ ...f, content: f.content ? `${f.content} ${transcript}` : transcript }));
      }
    } catch {
      setVoiceError('Transcription failed. Please try again.');
    } finally {
      setIsTranscribing(false);
      setRecordSeconds(0);
    }
  };

  const handleSubmit = async () => {
    setError('');
    if (!form.content.trim()) {
      setError('Please write something before saving.');
      return;
    }

    setSaving(true);
    try {
      const tagsArray = (form.tags || '')
        .split(',')
        .map((t) => t.trim().replace(/^#/, ''))
        .filter(Boolean);

      const payload = {
        entry_date: form.entry_date,
        title: form.title.trim() || 'Untitled',
        content: form.content,
        mood: form.mood || null,
        tags: tagsArray,
      };

      const res = await api.post('/diary/entries', payload);
      onCreated?.(res.data);
      onClose?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to save entry. Try again in a moment.');
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="fixed inset-0 cursor-default"
      />
      <div className="relative z-10 flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200/40 bg-white shadow-2xl dark:border-slate-700/40 dark:bg-slate-900">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-100 px-6 py-4 dark:border-slate-700">
          <h3 className="font-display text-lg font-bold text-slate-800 dark:text-slate-100">New diary entry</h3>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          {error && (
            <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800/60 dark:bg-rose-900/20 dark:text-rose-200">
              {error}
            </p>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Date
              </label>
              <input
                type="date"
                value={form.entry_date}
                onChange={(e) => setForm((f) => ({ ...f, entry_date: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Title
              </label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Optional title"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Mood
            </label>
            <div className="flex flex-wrap gap-2">
              {MOOD_OPTIONS.map((m) => {
                const active = form.mood === m.value;
                return (
                  <button
                    key={m.value}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, mood: active ? '' : m.value }))}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                      active
                        ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-blue-900/30'
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">{m.icon}</span>
                    {m.value}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Reflection
              </label>
              {speechSupported && (
                <button
                  type="button"
                  onClick={isRecording ? stopAndTranscribe : startRecording}
                  disabled={isTranscribing || saving}
                  title={isRecording ? 'Stop recording' : 'Voice input (auto language)'}
                  className={`flex h-8 items-center gap-1.5 rounded-full px-3 text-xs font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
                    isRecording
                      ? 'animate-pulse bg-red-500 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-blue-50 hover:text-blue-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-blue-900/30'
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">{isRecording ? 'stop' : 'mic'}</span>
                  {isRecording ? `Stop ${formatDuration(recordSeconds)}` : isTranscribing ? 'Transcribing…' : 'Voice'}
                </button>
              )}
            </div>
            {voiceError && (
              <p className="mb-2 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-600 dark:bg-rose-900/20 dark:text-rose-300">
                {voiceError}
              </p>
            )}
            <textarea
              rows={6}
              value={form.content}
              onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
              disabled={isTranscribing}
              placeholder="What's on your mind today?"
              className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Tags
            </label>
            <input
              type="text"
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
              placeholder="study, sleep, gratitude (comma-separated)"
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>
        </div>

        <div className="flex shrink-0 items-center justify-end gap-2 border-t border-slate-100 bg-slate-50/50 px-6 py-4 dark:border-slate-700 dark:bg-slate-800/30">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-xl px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving || isTranscribing}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="material-symbols-outlined text-base">{saving ? 'hourglass_top' : 'save'}</span>
            {saving ? 'Saving…' : 'Save entry'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewDiaryEntry;
