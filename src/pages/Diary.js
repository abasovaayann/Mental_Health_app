import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api/axios';

const sidebarItems = [
  { key: 'dashboard', label: 'Dashboard', icon: 'dashboard', path: '/dashboard' },
  { key: 'diary', label: 'Diary', icon: 'book_5', path: '/diary', active: true },
  { key: 'insights', label: 'Insights', icon: 'insights' },
  { key: 'exercises', label: 'Exercises', icon: 'fitness_center' },
  { key: 'settings', label: 'Settings', icon: 'settings', path: '/settings' },
];

const DAILY_PROMPTS = [
  'What happened today that affected your mood the most, and why do you think it stayed with you?',
  'Which moment today gave you even a small sense of relief or calm?',
  'What thought kept repeating in your mind, and what might it be asking for?',
  'If you could offer yourself one kind sentence today, what would it be?',
  'What felt heavy today, and what helped you carry it?'
];

const TAG_SUGGESTIONS = ['study', 'sleep', 'exam', 'family', 'anxiety', 'focus', 'gratitude', 'stress'];

const CALENDAR_VISIBLE_ENTRIES_LIMIT = 6;

const VOICE_LANGUAGES = [
  { value: 'en-US', label: 'English' },
  { value: 'ru-RU', label: 'Russian' },
  { value: 'tr-TR', label: 'Turkish' },
];

const formatDateInput = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const formatMonthLabel = (value) => {
  const parsed = new Date(`${value}T00:00:00`);
  return parsed.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

const formatDateShort = (value) => {
  const parsed = new Date(`${value}T00:00:00`);
  return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const formatDuration = (seconds) => {
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');
  return `${mm}:${ss}`;
};

const moodMeta = {
  positive: {
    label: 'Positive',
    card: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    dot: 'bg-emerald-500',
    calendar: 'bg-emerald-500 text-white hover:bg-emerald-600',
    calendarToday: 'bg-emerald-600 text-white ring-2 ring-primary/60',
    soft: 'ring-emerald-200 dark:ring-emerald-500/50',
  },
  neutral: {
    label: 'Neutral',
    card: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    dot: 'bg-amber-500',
    calendar: 'bg-amber-500 text-white hover:bg-amber-600',
    calendarToday: 'bg-amber-600 text-white ring-2 ring-primary/60',
    soft: 'ring-amber-200 dark:ring-amber-500/50',
  },
  negative: {
    label: 'Negative',
    card: 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
    dot: 'bg-rose-500',
    calendar: 'bg-rose-500 text-white hover:bg-rose-600',
    calendarToday: 'bg-rose-600 text-white ring-2 ring-primary/60',
    soft: 'ring-rose-200 dark:ring-rose-500/50',
  },
};

const moodRank = { negative: 3, neutral: 2, positive: 1 };

const formatReadableDate = (value) => {
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return 'Today';
  }

  return parsed.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
};

const getCalendarGrid = (year, month) => {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startOffset = (firstDay.getDay() + 6) % 7;
  const days = [];

  const prevMonthLastDate = new Date(year, month, 0).getDate();
  for (let i = startOffset - 1; i >= 0; i -= 1) {
    days.push({ day: prevMonthLastDate - i, currentMonth: false });
  }

  for (let day = 1; day <= lastDay.getDate(); day += 1) {
    days.push({ day, currentMonth: true });
  }

  let nextMonthDay = 1;
  while (days.length < 42) {
    days.push({ day: nextMonthDay, currentMonth: false });
    nextMonthDay += 1;
  }

  return days;
};

const isFutureDate = (dateValue, todayValue) => dateValue > todayValue;

const mapApiEntryToUi = (entry) => {
  const parsedDate = entry.created_at ? new Date(entry.created_at) : new Date();
  const safeTags = Array.isArray(entry.tags) ? entry.tags : [];

  return {
    id: String(entry.id),
    date: entry.entry_date,
    time: parsedDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    title: entry.title,
    content: entry.content,
    preview: entry.content.slice(0, 120) + (entry.content.length > 120 ? '...' : ''),
    mood: entry.mood,
    tags: safeTags,
  };
};

const Diary = () => {
  const navigate = useNavigate();
  const { date: selectedDateParam } = useParams();
  const isEditorPage = Boolean(selectedDateParam);
  const todayDate = useMemo(() => formatDateInput(new Date()), []);
  const selectedDate = selectedDateParam || todayDate;
  const [calendarDate, setCalendarDate] = useState(() => new Date(`${selectedDate}T00:00:00`));
  const calendarDays = useMemo(
    () => getCalendarGrid(calendarDate.getFullYear(), calendarDate.getMonth()),
    [calendarDate]
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [entries, setEntries] = useState([]);
  const [openedEntry, setOpenedEntry] = useState(null);
  const [editingEntryId, setEditingEntryId] = useState(null);
  const [dailyPrompt, setDailyPrompt] = useState(DAILY_PROMPTS[0]);

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [selectedMood, setSelectedMood] = useState('neutral');
  const [tags, setTags] = useState(['#reflection']);
  const [tagInput, setTagInput] = useState('');
  const [draftState, setDraftState] = useState('idle');
  const [saveState, setSaveState] = useState('idle');
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [voiceLanguage, setVoiceLanguage] = useState('en-US');
  const [recordingError, setRecordingError] = useState('');
  const [recordingStatus, setRecordingStatus] = useState('Ready');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [sameDayModalOpen, setSameDayModalOpen] = useState(false);
  const [recentEntriesModalOpen, setRecentEntriesModalOpen] = useState(false);
  const recognitionRef = useRef(null);
  const isRecordingRef = useRef(false);
  const timerRef = useRef(null);

  const speechSupported = useMemo(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    return Boolean(SpeechRecognition);
  }, []);

  useEffect(() => {
    // Cleanup legacy local-storage entry cache now that diary uses database-backed APIs.
    localStorage.removeItem('diary_entries');
  }, []);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) {
      navigate('/auth');
    }
  }, [navigate]);

  useEffect(() => {
    const parsed = new Date(`${selectedDate}T00:00:00`);
    if (!Number.isNaN(parsed.getTime())) {
      setCalendarDate(parsed);
    }
  }, [selectedDate]);

  useEffect(() => {
    if (!selectedDateParam) {
      return;
    }

    if (isFutureDate(selectedDateParam, todayDate)) {
      navigate(`/diary/entry/${todayDate}`, { replace: true });
    }
  }, [selectedDateParam, todayDate, navigate]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setEntries([]);
      return;
    }

    const loadEntries = async () => {
      try {
        const response = await api.get('/diary/entries');
        setEntries(Array.isArray(response.data) ? response.data.map(mapApiEntryToUi) : []);
      } catch (error) {
        console.error('Failed to load diary entries', error);
        setEntries([]);
      }
    };

    loadEntries();
  }, []);

  useEffect(() => {
    if (!isEditorPage) {
      return;
    }

    const queuedEditId = sessionStorage.getItem('diary_edit_entry_id');
    const activeEditId = queuedEditId || editingEntryId;
    if (queuedEditId) {
      setEditingEntryId(queuedEditId);
      sessionStorage.removeItem('diary_edit_entry_id');
    }

    const selectedEntryForEdit = entries.find(
      (entry) => entry.id === activeEditId && entry.date === selectedDate
    );
    if (selectedEntryForEdit) {
      setTitle(selectedEntryForEdit.title);
      setContent(selectedEntryForEdit.content);
      setSelectedMood(selectedEntryForEdit.mood);
      setTags(selectedEntryForEdit.tags.map((tag) => (tag.startsWith('#') ? tag : `#${tag}`)));
      setSaveState('idle');
      return;
    }

    if (activeEditId && editingEntryId && !selectedEntryForEdit) {
      setEditingEntryId(null);
    }

    const draftKey = `diary_draft_${selectedDate}`;
    const saved = JSON.parse(localStorage.getItem(draftKey) || 'null');
    if (saved) {
      setTitle(saved.title || '');
      setContent(saved.content || '');
      setSelectedMood(saved.selectedMood || 'neutral');
      setTags(Array.isArray(saved.tags) && saved.tags.length ? saved.tags : ['#reflection']);
      return;
    }

    const existing = entries.find((entry) => entry.date === selectedDate);
    if (existing) {
      setTitle(existing.title);
      setContent(existing.content);
      setSelectedMood(existing.mood);
      setTags(existing.tags.map((tag) => (tag.startsWith('#') ? tag : `#${tag}`)));
    } else {
      setTitle('');
      setContent('');
      setSelectedMood('neutral');
      setTags(['#reflection']);
    }

    setSaveState('idle');
  }, [isEditorPage, selectedDate, entries]);

  useEffect(() => {
    if (!isEditorPage) {
      return;
    }

    const draftKey = `diary_draft_${selectedDate}`;
    setDraftState('saving');
    const timeout = setTimeout(() => {
      localStorage.setItem(
        draftKey,
        JSON.stringify({
          title,
          content,
          selectedMood,
          tags,
          updatedAt: Date.now(),
        })
      );
      setDraftState('saved');
    }, 700);

    return () => clearTimeout(timeout);
  }, [isEditorPage, selectedDate, title, content, selectedMood, tags]);

  // Cleanup recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.onend = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onresult = null;
        recognitionRef.current.abort();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (saveState !== 'success') {
      return undefined;
    }

    const timeout = setTimeout(() => setSaveState('idle'), 2200);
    return () => clearTimeout(timeout);
  }, [saveState]);

  const entriesByDate = useMemo(() => {
    return entries.reduce((acc, entry) => {
      if (!acc[entry.date]) {
        acc[entry.date] = [];
      }
      acc[entry.date].push(entry);
      return acc;
    }, {});
  }, [entries]);

  const wordsCount = useMemo(() => {
    return content.trim() ? content.trim().split(/\s+/).length : 0;
  }, [content]);

  const aiMoodData = useMemo(() => {
    const byMood = {
      positive: {
        mood: '😊 Calm',
        insight:
          'You are showing healthy recovery patterns today. Moments of gratitude and task completion are helping your stress stay manageable.',
        suggestions: [
          'Keep your evening wind-down routine simple and consistent.',
          'Write 3 small goals for tomorrow to protect this momentum.',
          'Take one short walk to maintain emotional balance.',
        ],
      },
      neutral: {
        mood: '🙂 Steady',
        insight:
          'Your mood appears balanced with mild mental load. Small moments of structure are preventing stress from building too quickly.',
        suggestions: [
          'Take short breaks between focused tasks.',
          'Name one priority and let the rest wait for tomorrow.',
          'Try 5 minutes of slow breathing before sleep.',
        ],
      },
      negative: {
        mood: '😔 Stressed',
        insight:
          'Your reflection suggests cognitive fatigue and pressure. You are still processing clearly, but your nervous system could benefit from slower pacing.',
        suggestions: [
          'Split big tasks into 15-minute blocks with pauses.',
          'Write one supportive sentence to yourself before bed.',
          'Reduce screen stimulation for 30 minutes tonight.',
        ],
      },
    };

    return byMood[selectedMood] || byMood.neutral;
  }, [selectedMood]);

  const aiConfidence = useMemo(() => {
    const base = selectedMood === 'negative' ? 76 : selectedMood === 'positive' ? 81 : 78;
    const wordBoost = Math.min(8, Math.floor(wordsCount / 45));
    const voiceBoost = transcript.trim() ? 3 : 0;
    return Math.min(94, base + wordBoost + voiceBoost);
  }, [selectedMood, wordsCount, transcript]);

  const energyLevel = useMemo(() => {
    if (wordsCount < 90) {
      return 'Low';
    }
    if (wordsCount < 220) {
      return 'Medium';
    }
    return 'High';
  }, [wordsCount]);

  const mainTheme = useMemo(() => {
    const cleaned = tags
      .map((tag) => tag.replace('#', '').trim())
      .find((tag) => tag && tag !== 'reflection');

    if (!cleaned) {
      return 'General reflection';
    }

    return `${cleaned.charAt(0).toUpperCase()}${cleaned.slice(1)} focus`;
  }, [tags]);

  const readMinutes = Math.max(1, Math.ceil(wordsCount / 180));
  const isSaveDisabled = !title.trim() || !content.trim();

  const tagSuggestions = useMemo(() => {
    const cleanInput = tagInput.trim().toLowerCase();
    if (!cleanInput) {
      return TAG_SUGGESTIONS.slice(0, 5);
    }

    return TAG_SUGGESTIONS.filter((tag) => tag.includes(cleanInput)).slice(0, 5);
  }, [tagInput]);

  const activeMoodByDate = useMemo(() => {
    return Object.keys(entriesByDate).reduce((acc, dateKey) => {
      const strongest = entriesByDate[dateKey].reduce((current, item) => {
        return moodRank[item.mood] > moodRank[current] ? item.mood : current;
      }, 'positive');
      acc[dateKey] = strongest;
      return acc;
    }, {});
  }, [entriesByDate]);

  const selectedDayEntries = useMemo(() => {
    if (!isEditorPage) {
      return [];
    }

    return entries.filter((entry) => entry.date === selectedDate);
  }, [entries, isEditorPage, selectedDate]);

  const saveEntry = async () => {
    if (isSaveDisabled) {
      return;
    }

    const preparedEntry = {
      entry_date: selectedDate,
      title: title.trim(),
      content: content.trim(),
      mood: selectedMood,
      tags: tags.map((tag) => tag.replace('#', '')),
    };

    try {
      if (editingEntryId) {
        const response = await api.put(`/diary/entries/${editingEntryId}`, preparedEntry);
        const updatedEntry = mapApiEntryToUi(response.data);
        setEntries((prev) => prev.map((entry) => (entry.id === editingEntryId ? updatedEntry : entry)));
      } else {
        const response = await api.post('/diary/entries', preparedEntry);
        const createdEntry = mapApiEntryToUi(response.data);
        setEntries((prev) => [createdEntry, ...prev]);
      }

      localStorage.removeItem(`diary_draft_${selectedDate}`);
      setDraftState('saved');
      setSaveState('success');
    } catch (error) {
      console.error('Failed to save diary entry', error);
      setSaveState('idle');
    }
  };

  const addTag = (value) => {
    const clean = value.trim().replace('#', '');
    if (!clean) {
      return;
    }
    const formatted = `#${clean.toLowerCase()}`;
    if (!tags.includes(formatted)) {
      setTags((prev) => [...prev, formatted]);
    }
    setTagInput('');
  };

  const removeTag = (value) => {
    setTags((prev) => prev.filter((tag) => tag !== value));
  };

  /* ---------- Helper: start the mm:ss timer ---------- */
  const startTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    timerRef.current = setInterval(() => {
      setRecordSeconds((prev) => prev + 1);
    }, 1000);
  };

  /* ---------- Helper: stop the mm:ss timer ---------- */
  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  /* ---------- Helper: create and wire up a SpeechRecognition instance ---------- */
  const initRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = voiceLanguage;

    recognition.onstart = () => {};

    recognition.onresult = (event) => {
      let interim = '';
      let finalText = '';

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const text = event.results[i][0].transcript;
        const isFinal = event.results[i].isFinal;
        if (isFinal) {
          finalText += text + ' ';
        } else {
          interim += text;
        }
      }

      if (finalText) {
        setTranscript((prev) => prev + finalText);
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event) => {
      // 'aborted' fires naturally when recognition.abort() is called (e.g. on discard) — not a real error
      if (event.error === 'aborted') {
        return;
      }
      setRecordingError(`Speech error: ${event.error}`);
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        stopTimer();
        isRecordingRef.current = false;
        setIsRecording(false);
        setIsPaused(false);
        setRecordingStatus('Ready');
      }
    };

    // Auto-restart only when still actively recording (not paused/stopped/discarded)
    recognition.onend = () => {
      if (isRecordingRef.current) {
        recognition.start();
      }
    };

    recognitionRef.current = recognition;
  };

  /* ---------- Start recording (Web Speech API) ---------- */
  const startRecording = () => {
    if (!speechSupported || isRecordingRef.current) {
      return;
    }

    setRecordingError('');
    setRecordingStatus('Listening...');

    // Brand new session (not resuming from pause): clear old transcript
    if (!isPaused) {
      setTranscript('');
      setInterimTranscript('');
      setRecordSeconds(0);
      initRecognition();
    }

    isRecordingRef.current = true;
    setIsRecording(true);
    setIsPaused(false);

    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (error) {
        // If restarting the same instance fails, create a new one
        initRecognition();
        recognitionRef.current.start();
      }
    }

    startTimer();
  };

  /* ---------- Pause recording ---------- */
  const pauseRecording = () => {
    if (!recognitionRef.current || !isRecordingRef.current) {
      return;
    }

    isRecordingRef.current = false;
    setIsPaused(true);
    setRecordingStatus('Paused');
    setInterimTranscript('');

    recognitionRef.current.stop();
    stopTimer();
  };

  /* ---------- Resume recording (delegates to startRecording) ---------- */
  const resumeRecording = () => {
    startRecording();
  };

  /* ---------- Stop and save (append to diary content) ---------- */
  const stopAndSaveRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.stop();
    }

    isRecordingRef.current = false;
    setIsRecording(false);
    setIsPaused(false);
    setInterimTranscript('');
    setRecordingStatus('Saved');
    stopTimer();

    // Append final transcript to diary content
    setTranscript((currentTranscript) => {
      const finalVoiceNote = currentTranscript.trim();
      if (finalVoiceNote) {
        setContent((prev) =>
          prev.trim()
            ? `${prev.trim()}\n\nVoice note: ${finalVoiceNote}`
            : `Voice note: ${finalVoiceNote}`
        );
      }
      return currentTranscript;
    });
  };

  /* ---------- Discard recording ---------- */
  const discardRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.abort();
    }

    isRecordingRef.current = false;
    setIsRecording(false);
    setIsPaused(false);
    setTranscript('');
    setInterimTranscript('');
    setRecordingStatus('Ready');
    setRecordingError('');
    setRecordSeconds(0);
    stopTimer();
  };

  const shiftMonth = (value) => {
    setCalendarDate((prev) => {
      const next = new Date(prev.getFullYear(), prev.getMonth() + value, 1);
      const currentMonthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
      if (next > currentMonthStart) {
        return prev;
      }
      return next;
    });
  };

  const startEditEntry = (entry) => {
    sessionStorage.setItem('diary_edit_entry_id', entry.id);
    navigate(`/diary/entry/${entry.date}`);
    setSidebarOpen(false);
  };

  const deleteEntry = async (entryId) => {
    try {
      await api.delete(`/diary/entries/${entryId}`);
      setEntries((prev) => prev.filter((entry) => entry.id !== entryId));

      if (openedEntry?.id === entryId) {
        setOpenedEntry(null);
      }

      if (editingEntryId === entryId) {
        setEditingEntryId(null);
        setTitle('');
        setContent('');
        setSelectedMood('neutral');
        setTags(['#reflection']);
        setSaveState('idle');
      }
    } catch (error) {
      console.error('Failed to delete diary entry', error);
    }
  };

  const removeCurrentEditingEntry = () => {
    if (!editingEntryId) {
      return;
    }
    deleteEntry(editingEntryId);
  };

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

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col justify-between bg-blue-900 px-6 py-6 text-white shadow-2xl transition-transform duration-200 lg:static lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'
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
                  if (item.path) {
                    navigate(item.path);
                    setSidebarOpen(false);
                  }
                }}
                className={`flex items-center gap-3 rounded-xl px-4 py-3 text-left font-medium transition-all ${item.active
                    ? 'bg-blue-500/30 text-white'
                    : item.path
                      ? 'text-blue-100 hover:bg-white/10'
                      : 'cursor-not-allowed text-blue-200/60'
                  }`}
              >
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                <span className="text-sm font-medium">{item.label}</span>
                {!item.path && <span className="ml-auto text-[10px] uppercase tracking-wide">Soon</span>}
              </button>
            ))}
          </nav>
        </div>

        <button
          type="button"
          className="flex items-center justify-center gap-2 rounded-2xl bg-white/10 py-3.5 font-semibold text-white transition-all hover:bg-white/15"
        >
          <span className="material-symbols-outlined text-sm font-bold">add</span>
          <span className="text-sm">New Entry</span>
        </button>
      </aside>

      <main className="custom-scrollbar h-full flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
        <div className="w-full space-y-6">
          <header className="flex items-start gap-3 lg:hidden">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="mt-1 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-slate-600 shadow-sm dark:bg-slate-800 dark:text-slate-200"
            >
              <span className="material-symbols-outlined">menu</span>
            </button>
            <div>
              <h1 className="font-display text-2xl font-bold text-text-heading">Diary</h1>
              <p className="mt-1 text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark">Write and review your reflections.</p>
            </div>
          </header>

          {!isEditorPage && (
            <div className="grid grid-cols-1 gap-6 xl:min-h-[calc(100vh-10rem)] xl:grid-cols-12 xl:items-stretch">
              <section className="xl:col-span-7 flex h-full flex-col gap-6">
                <div className="h-full rounded-3xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark">
                  <div className="mb-5 flex items-center justify-between">
                    <div>
                      <h3 className="font-display text-lg font-bold text-slate-800 dark:text-white">Calendar</h3>
                      <p className="mt-1 text-xs text-slate-400">Only today and past dates are available</p>
                    </div>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => shiftMonth(-1)} className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-500 dark:bg-slate-800">
                        <span className="material-symbols-outlined text-[18px]">chevron_left</span>
                      </button>
                      <button type="button" onClick={() => shiftMonth(1)} className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-500 dark:bg-slate-800">
                        <span className="material-symbols-outlined text-[18px]">chevron_right</span>
                      </button>
                    </div>
                  </div>

                  <div className="mb-4 flex items-center justify-between">
                    <h4 className="font-semibold text-slate-800 dark:text-white">{formatMonthLabel(formatDateInput(calendarDate))}</h4>
                    <span className="text-xs font-semibold text-primary">Choose a day</span>
                  </div>

                  <div className="mb-3 grid grid-cols-7 gap-2 text-center text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    {['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'].map((day) => (
                      <span key={day}>{day}</span>
                    ))}
                  </div>

                  <div className="grid grid-cols-7 gap-2 text-sm">
                    {calendarDays.map((item, index) => {
                      const cellDate = formatDateInput(new Date(calendarDate.getFullYear(), calendarDate.getMonth(), item.day));
                      const isToday = item.currentMonth && cellDate === todayDate;
                      const mood = activeMoodByDate[cellDate];
                      const isFuture = item.currentMonth && isFutureDate(cellDate, todayDate);
                      const moodClass = mood
                        ? isToday
                          ? moodMeta[mood].calendarToday
                          : moodMeta[mood].calendar
                        : '';

                      return (
                        <button
                          key={`${item.day}-${index}`}
                          type="button"
                          disabled={!item.currentMonth || isFuture}
                          onClick={() => {
                            if (isFuture) {
                              return;
                            }
                            navigate(`/diary/entry/${cellDate}`);
                          }}
                          className={`relative aspect-square rounded-2xl transition-colors ${item.currentMonth
                              ? isFuture
                                ? 'cursor-not-allowed bg-slate-100 text-slate-400 dark:bg-slate-900 dark:text-slate-600'
                                : mood
                                  ? `${moodClass} font-bold shadow-md`
                                  : isToday
                                    ? 'bg-primary font-bold text-white shadow-lg shadow-primary/20'
                                    : 'bg-slate-50 text-slate-700 hover:bg-primary/10 dark:bg-slate-800 dark:text-slate-200'
                              : 'cursor-not-allowed text-slate-400 dark:text-slate-600'
                            }`}
                        >
                          {item.day}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </section>

              <aside className="xl:col-span-5 flex h-full flex-col gap-6">
                <div className="flex h-full flex-col rounded-3xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark">
                  <div className="mb-5 flex items-center justify-between">
                    <div>
                      <h3 className="font-display text-lg font-bold text-slate-800 dark:text-white">Recent Entries</h3>
                      <p className="mt-1 text-xs text-slate-400">Open any existing entry or choose a date first.</p>
                    </div>
                  </div>

                  {entries.length ? (
                    <>
                      <div className="min-h-0 flex-1 space-y-3 overflow-hidden pr-1">
                        {entries.slice(0, CALENDAR_VISIBLE_ENTRIES_LIMIT).map((entry) => (
                          <div
                            key={entry.id}
                            className="rounded-2xl border border-slate-200 bg-white p-4 transition-colors hover:border-primary/30 dark:border-slate-700 dark:bg-slate-900"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="font-display text-sm font-bold text-slate-800 dark:text-white">{entry.title}</p>
                                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatDateShort(entry.date)} · {entry.time}</p>
                              </div>
                              <span className={`rounded-lg px-2 py-1 text-[10px] font-bold uppercase ${moodMeta[entry.mood].card}`}>
                                {moodMeta[entry.mood].label}
                              </span>
                            </div>
                            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">{entry.preview}</p>
                            <div className="mt-3 flex flex-wrap gap-2">
                              {entry.tags.map((tag) => (
                                <span
                                  key={`recent-${entry.id}-${tag}`}
                                  className="rounded-lg bg-slate-100 px-2 py-1 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                                >
                                  #{tag.replace('#', '')}
                                </span>
                              ))}
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs font-semibold">
                              <button
                                type="button"
                                onClick={() => startEditEntry(entry)}
                                className="text-blue-600 hover:underline dark:text-blue-300"
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                onClick={() => deleteEntry(entry.id)}
                                className="text-rose-600 hover:underline dark:text-rose-300"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>

                      <button
                        type="button"
                        onClick={() => setRecentEntriesModalOpen(true)}
                        className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-semibold text-slate-700 transition-colors hover:border-primary/40 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                      >
                        Open full window for seeing all your records
                      </button>
                    </>
                  ) : (
                    <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
                      No diary entries yet. Create your first one from any date.
                    </p>
                  )}
                </div>
              </aside>
            </div>
          )}

          {isEditorPage && (
            <div className="grid grid-cols-1 gap-6 xl:min-h-[calc(100vh-10rem)] xl:grid-cols-12 xl:items-stretch">
              <section className="xl:col-span-8 flex flex-col gap-6 xl:h-full">
                <div className="flex items-center gap-4 rounded-3xl border border-slate-100 bg-surface-light p-5 shadow-sm dark:border-border-dark dark:bg-surface-dark">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50 dark:bg-amber-900/20">
                    <span className="material-symbols-outlined text-amber-500">lightbulb</span>
                  </div>
                  <div className="flex-1">
                    <p className="mb-1 text-[11px] font-bold uppercase tracking-widest text-amber-600 dark:text-amber-500">Daily Prompt</p>
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{dailyPrompt}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const currentIndex = DAILY_PROMPTS.indexOf(dailyPrompt);
                      const nextIndex = (currentIndex + 1) % DAILY_PROMPTS.length;
                      setDailyPrompt(DAILY_PROMPTS[nextIndex]);
                    }}
                    className="text-slate-400 transition-colors hover:text-slate-600"
                  >
                    <span className="material-symbols-outlined text-lg">refresh</span>
                  </button>
                </div>

                <div className="flex flex-col gap-6 rounded-3xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark sm:p-8 xl:flex-1">
                  <div className="flex flex-col gap-4 md:flex-row md:items-start">
                    <div className="flex-1">
                      <input
                        className="w-full rounded-2xl border-none bg-slate-50 px-5 py-4 text-xl font-bold text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-primary/50 dark:bg-slate-800/50 dark:text-white"
                        placeholder="Title your reflection..."
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                      />
                    </div>
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
                      <span className="rounded-xl bg-blue-50 px-3 py-2 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
                        {editingEntryId
                          ? 'Editing entry'
                          : draftState === 'saving'
                            ? 'Saving draft...'
                            : draftState === 'saved'
                              ? 'Draft saved'
                              : 'Draft idle'}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    {['positive', 'neutral', 'negative'].map((mood) => (
                      <button
                        key={mood}
                        type="button"
                        onClick={() => setSelectedMood(mood)}
                        className={`rounded-2xl border px-4 py-4 text-left transition-colors dark:border-slate-700 dark:bg-slate-800/50 ${selectedMood === mood
                            ? `ring-2 ${moodMeta[mood].soft} border-transparent bg-white`
                            : 'border-slate-200 bg-slate-50 hover:border-primary/40'
                          }`}
                      >
                        <p className="mb-1 text-[11px] font-bold uppercase tracking-widest text-slate-400">Mood</p>
                        <p className="text-sm font-semibold text-slate-800 dark:text-white">{moodMeta[mood].label}</p>
                      </button>
                    ))}
                    <button type="button" className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-left transition-colors hover:border-primary/40 dark:border-slate-700 dark:bg-slate-800/50">
                      <p className="mb-1 text-[11px] font-bold uppercase tracking-widest text-slate-400">Weather of mind</p>
                      <p className="text-sm font-semibold text-slate-800 dark:text-white">Mostly clear</p>
                    </button>
                  </div>

                  <textarea
                    id="diaryContent"
                    className="min-h-[420px] w-full resize-none rounded-2xl border-none bg-slate-50 px-6 py-6 text-base leading-relaxed text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-primary/50 dark:bg-slate-800/50 dark:text-white"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Write your reflection here..."
                  />

                  <div className="flex flex-col gap-3">
                    <div className="flex flex-wrap gap-2">
                      {tags.map((tag) => (
                        <span
                          key={tag}
                          className="flex items-center gap-1 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        >
                          {tag}
                          <button type="button" onClick={() => removeTag(tag)} className="material-symbols-outlined text-xs">close</button>
                        </span>
                      ))}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="text"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            addTag(tagInput);
                          }
                        }}
                        placeholder="+ Add tag"
                        className="w-40 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 focus:border-primary focus:ring-0 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                      />
                      <button type="button" onClick={() => addTag(tagInput)} className="rounded-xl bg-primary/10 px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/20">
                        Add
                      </button>
                      <div className="flex flex-wrap gap-2">
                        {tagSuggestions.map((suggestion) => (
                          <button
                            key={suggestion}
                            type="button"
                            onClick={() => addTag(suggestion)}
                            className="rounded-lg border border-slate-200 px-2 py-1 text-[11px] text-slate-500 transition-colors hover:border-primary/40 dark:border-slate-700 dark:text-slate-400"
                          >
                            {`#${suggestion}`}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-4 border-t border-slate-100 pt-6 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-wrap items-center gap-5 text-xs text-slate-400">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-base">format_align_left</span>
                        <span className="font-medium">{wordsCount} words</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-base">schedule</span>
                        <span className="font-medium">~{readMinutes} min read</span>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      {editingEntryId && (
                        <button
                          type="button"
                          onClick={removeCurrentEditingEntry}
                          className="rounded-xl border border-rose-200 px-6 py-2.5 text-sm font-semibold text-rose-600 transition-colors hover:bg-rose-50 dark:border-rose-900/60 dark:text-rose-300 dark:hover:bg-rose-900/20"
                        >
                          Delete Entry
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          setEditingEntryId(null);
                          setTitle('');
                          setContent('');
                          setTags(['#reflection']);
                          discardRecording();
                        }}
                        className="rounded-xl border border-slate-200 px-6 py-2.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                      >
                        Clear
                      </button>
                      <button
                        type="button"
                        disabled={isSaveDisabled}
                        onClick={saveEntry}
                        className="rounded-xl bg-primary px-8 py-2.5 text-sm font-semibold text-white shadow-md shadow-primary/20 transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {saveState === 'success' ? 'Saved ✓' : editingEntryId ? 'Update Entry' : 'Save Entry'}
                      </button>
                    </div>
                  </div>
                </div>
              </section>

              <aside className="xl:col-span-4 flex flex-col gap-6 xl:h-full xl:justify-between">
                <div className="rounded-3xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark">
                  <div className="mb-6 flex items-center justify-between">
                    <p className="font-display text-lg font-bold text-slate-800 dark:text-white">Voice Diary</p>
                    <div className="flex items-center gap-2">
                      {isRecording && !isPaused && <span className="h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse" />}
                      {isPaused && <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />}
                      <span
                        id="recordingStatus"
                        className={`text-xs font-bold uppercase tracking-wide ${isPaused ? 'text-amber-500' : isRecording ? 'text-red-500' : 'text-slate-400 dark:text-slate-500'}`}
                      >
                        {recordingStatus}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col items-center gap-6 py-2">
                    <button
                      type="button"
                      onClick={isRecording ? (isPaused ? resumeRecording : stopAndSaveRecording) : startRecording}
                      disabled={!speechSupported}
                      className="relative disabled:opacity-50"
                    >
                      {isRecording && !isPaused && <span className="absolute -inset-4 rounded-full bg-primary/10 animate-ping opacity-25" />}
                      <span className={`relative flex h-20 w-20 items-center justify-center rounded-full text-white shadow-xl ${isPaused ? 'bg-amber-500 shadow-amber-500/30' : 'bg-primary shadow-primary/30'}`}>
                        <span className="material-symbols-outlined text-4xl">{isPaused ? 'play_arrow' : 'mic'}</span>
                      </span>
                    </button>

                    <div className="text-center">
                      <p id="recordingTimer" className="text-3xl font-mono font-bold text-slate-800 dark:text-white">{formatDuration(recordSeconds)}</p>
                      <p className="mt-1 text-sm text-slate-400">
                        {isPaused ? 'Paused — tap to resume' : isRecording ? 'Tap to stop' : 'Tap to start recording'}
                      </p>
                    </div>

                    <div className="w-full">
                      <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">Recognition language</p>
                      <div className="grid grid-cols-2 gap-2">
                        {VOICE_LANGUAGES.map((lang) => (
                          <button
                            key={lang.value}
                            type="button"
                            disabled={isRecording}
                            onClick={() => setVoiceLanguage(lang.value)}
                            className={`rounded-xl border px-3 py-2 text-xs font-semibold transition-colors ${voiceLanguage === lang.value
                                ? 'border-primary bg-primary/10 text-primary'
                                : 'border-slate-200 bg-white text-slate-600 hover:border-primary/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'
                              } disabled:cursor-not-allowed disabled:opacity-60`}
                          >
                            {lang.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {!speechSupported && (
                      <p className="w-full rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
                        Speech recognition not supported in this browser
                      </p>
                    )}

                    {recordingError && (
                      <p
                        id="recordingError"
                        className="w-full rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-900/20 dark:text-rose-300"
                      >
                        {recordingError}
                      </p>
                    )}

                    <div className="flex w-full gap-2">
                      <button id="startRecording" type="button" onClick={isPaused ? resumeRecording : startRecording} disabled={(isRecording && !isPaused) || !speechSupported} className="flex-1 rounded-full bg-primary px-3 py-3 text-sm font-bold text-white disabled:opacity-50">
                        {isPaused ? 'Resume' : 'Start'}
                      </button>
                      <button id="pauseRecording" type="button" onClick={isPaused ? resumeRecording : pauseRecording} disabled={!isRecording} className={`flex-1 rounded-full px-3 py-3 text-sm font-bold disabled:opacity-50 ${isPaused ? 'bg-amber-500 text-white' : 'bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300'}`}>
                        {isPaused ? 'Resume' : 'Pause'}
                      </button>
                      <button id="stopRecording" type="button" onClick={stopAndSaveRecording} disabled={!isRecording} className="flex-1 rounded-full bg-primary px-3 py-3 text-sm font-bold text-white disabled:opacity-50">
                        Save
                      </button>
                      <button id="discardRecording" type="button" onClick={discardRecording} disabled={!isRecording && !transcript} className="flex-1 rounded-full bg-slate-100 px-3 py-3 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
                        Discard
                      </button>
                    </div>

                    <div id="liveTranscript" className="w-full rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                      <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">Live Transcription</p>
                      <p className="text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                        {transcript || interimTranscript ? (
                          <>
                            <span>{transcript}</span>
                            {interimTranscript && (
                              <span className="italic text-slate-400 dark:text-slate-500">{interimTranscript}</span>
                            )}
                          </>
                        ) : (
                          <span className="italic">Tap Start, allow microphone access, and begin speaking.</span>
                        )}
                      </p>
                    </div>
                  </div>
                </div>

                <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <article className="rounded-3xl border border-blue-100 bg-blue-50/70 p-5 shadow-sm transition-all hover:shadow-md dark:border-blue-900/50 dark:bg-blue-950/20">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div>
                        <p className="font-display text-base font-bold text-slate-800 dark:text-white">AI Analysis</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Emotion detection from your writing + voice</p>
                      </div>
                      <span className="material-symbols-outlined text-blue-500">neurology</span>
                    </div>

                    <div className="mb-3 flex items-center justify-between rounded-2xl bg-white/70 px-3 py-2 text-sm dark:bg-slate-900/50">
                      <span className="font-semibold text-slate-600 dark:text-slate-300">Detected mood</span>
                      <span className="font-bold text-slate-800 dark:text-white">{aiMoodData.mood}</span>
                    </div>

                    <div className="mb-3 flex items-center justify-between rounded-2xl bg-white/70 px-3 py-2 text-sm dark:bg-slate-900/50">
                      <span className="font-semibold text-slate-600 dark:text-slate-300">Confidence</span>
                      <span className="font-bold text-blue-700 dark:text-blue-300">{aiConfidence}%</span>
                    </div>

                    <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{aiMoodData.insight}</p>
                  </article>

                  <article className="rounded-3xl border border-slate-100 bg-surface-light p-5 shadow-sm transition-all hover:shadow-md dark:border-border-dark dark:bg-surface-dark">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div>
                        <p className="font-display text-base font-bold text-slate-800 dark:text-white">Daily Summary</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Quick snapshot for today</p>
                      </div>
                      <span className="material-symbols-outlined text-slate-400">monitoring</span>
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                        <span className="text-slate-500 dark:text-slate-400">Mood</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-200">{moodMeta[selectedMood].label}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                        <span className="text-slate-500 dark:text-slate-400">Energy level</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-200">{energyLevel}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                        <span className="text-slate-500 dark:text-slate-400">Main theme</span>
                        <span className="font-semibold text-right text-slate-700 dark:text-slate-200">{mainTheme}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                        <span className="text-slate-500 dark:text-slate-400">Word count</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-200">{wordsCount}</span>
                      </div>
                    </div>
                  </article>

                  <article className="md:col-span-2 rounded-3xl border border-slate-100 bg-surface-light p-5 shadow-sm transition-all hover:shadow-md dark:border-border-dark dark:bg-surface-dark">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div>
                        <p className="font-display text-base font-bold text-slate-800 dark:text-white">Suggestions</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Gentle actions based on today&apos;s emotional pattern</p>
                      </div>
                      <span className="material-symbols-outlined text-amber-500">tips_and_updates</span>
                    </div>

                    <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
                      {aiMoodData.suggestions.slice(0, 3).map((item) => (
                        <li key={item} className="flex items-start gap-2 rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                          <span className="mt-[2px] h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </article>

                  <article className="md:col-span-2 rounded-3xl border border-slate-100 bg-surface-light p-5 shadow-sm transition-all hover:shadow-md dark:border-border-dark dark:bg-surface-dark">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div>
                        <p className="font-display text-base font-bold text-slate-800 dark:text-white">Same Day Entries</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Entries saved for {formatReadableDate(selectedDate)}</p>
                      </div>
                      <span className="material-symbols-outlined text-slate-400">history_edu</span>
                    </div>

                    <button
                      type="button"
                      onClick={() => setSameDayModalOpen(true)}
                      className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-4 text-left transition-colors hover:border-primary/40 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-800 dark:text-white">View saved entries for this day</p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            {selectedDayEntries.length
                              ? `${selectedDayEntries.length} entr${selectedDayEntries.length === 1 ? 'y' : 'ies'} saved`
                              : 'No entries saved yet'}
                          </p>
                        </div>
                        <span className="material-symbols-outlined text-slate-400">open_in_new</span>
                      </div>
                    </button>
                  </article>
                </section>
              </aside>
            </div>
          )}
        </div>
      </main>

      {recentEntriesModalOpen && !isEditorPage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Recent Entries</p>
                <h3 className="mt-1 font-display text-xl font-bold text-slate-800 dark:text-white">All Diary Entries</h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Total entries: {entries.length}</p>
              </div>
              <button
                type="button"
                onClick={() => setRecentEntriesModalOpen(false)}
                className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {entries.length ? (
              <div className="custom-scrollbar max-h-[60vh] space-y-3 overflow-y-auto pr-1">
                {entries.map((entry) => (
                  <div key={`modal-recent-${entry.id}`} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-800 dark:text-white">{entry.title}</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatDateShort(entry.date)} · {entry.time}</p>
                      </div>
                      <span className={`rounded-lg px-2 py-1 text-[10px] font-bold uppercase ${moodMeta[entry.mood].card}`}>
                        {moodMeta[entry.mood].label}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">{entry.preview}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {entry.tags.map((tag) => (
                        <span
                          key={`modal-recent-tag-${entry.id}-${tag}`}
                          className="rounded-lg bg-slate-100 px-2 py-1 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        >
                          #{tag.replace('#', '')}
                        </span>
                      ))}
                    </div>
                    <div className="mt-3 flex items-center gap-3 text-xs font-semibold">
                      <button
                        type="button"
                        onClick={() => {
                          startEditEntry(entry);
                          setRecentEntriesModalOpen(false);
                        }}
                        className="text-blue-600 hover:underline dark:text-blue-300"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteEntry(entry.id)}
                        className="text-rose-600 hover:underline dark:text-rose-300"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
                No diary entries yet. Create your first one from any date.
              </p>
            )}
          </div>
        </div>
      )}

      {sameDayModalOpen && isEditorPage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Same Day Entries</p>
                <h3 className="mt-1 font-display text-xl font-bold text-slate-800 dark:text-white">
                  {formatReadableDate(selectedDate)}
                </h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Total entries: {selectedDayEntries.length}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSameDayModalOpen(false)}
                className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {selectedDayEntries.length ? (
              <div className="custom-scrollbar max-h-[60vh] space-y-3 overflow-y-auto pr-1">
                {selectedDayEntries.map((entry) => (
                  <div key={`modal-same-day-${entry.id}`} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-800 dark:text-white">{entry.title}</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{entry.time}</p>
                      </div>
                      <span className={`rounded-lg px-2 py-1 text-[10px] font-bold uppercase ${moodMeta[entry.mood].card}`}>
                        {moodMeta[entry.mood].label}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">{entry.preview}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {entry.tags.map((tag) => (
                        <span
                          key={`same-day-tag-${entry.id}-${tag}`}
                          className="rounded-lg bg-slate-100 px-2 py-1 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        >
                          #{tag.replace('#', '')}
                        </span>
                      ))}
                    </div>
                    <div className="mt-3 flex items-center gap-3 text-xs font-semibold">
                      <button
                        type="button"
                        onClick={() => {
                          startEditEntry(entry);
                          setSameDayModalOpen(false);
                        }}
                        className="text-blue-600 hover:underline dark:text-blue-300"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteEntry(entry.id)}
                        className="text-rose-600 hover:underline dark:text-rose-300"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
                No saved entries for this date yet. Write and save one to see it here.
              </p>
            )}
          </div>
        </div>
      )}

      {openedEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">{formatDateShort(openedEntry.date)} · {openedEntry.time}</p>
                <h3 className="mt-1 text-xl font-bold text-slate-800 dark:text-white">{openedEntry.title}</h3>
              </div>
              <button type="button" onClick={() => setOpenedEntry(null)} className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="mb-4 flex items-center gap-2">
              <span className={`rounded-lg px-2 py-1 text-[10px] font-bold uppercase ${moodMeta[openedEntry.mood].card}`}>{moodMeta[openedEntry.mood].label}</span>
              {openedEntry.tags.map((tag) => (
                <span key={`open-${openedEntry.id}-${tag}`} className="rounded-lg bg-slate-100 px-2 py-1 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  #{tag}
                </span>
              ))}
            </div>

            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{openedEntry.content}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Diary;
