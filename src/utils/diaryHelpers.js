// Pure helpers for the Diary feature: date/time formatting, calendar grid
// construction, and API <-> UI entry mapping. No React or I/O here so these
// can be unit-tested in isolation.

export const formatDateInput = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const formatMonthLabel = (value) => {
  const parsed = new Date(`${value}T00:00:00`);
  return parsed.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

export const formatDateShort = (value) => {
  const parsed = new Date(`${value}T00:00:00`);
  return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

export const formatDuration = (seconds) => {
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');
  return `${mm}:${ss}`;
};

export const formatReadableDate = (value) => {
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

export const getCalendarGrid = (year, month) => {
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

export const isFutureDate = (dateValue, todayValue) => dateValue > todayValue;

// The NLP pipeline stores mood as low/medium/high, while the diary editor uses
// positive/neutral/negative. The UI (moodMeta) only knows the latter three, so
// normalize to those keys and default anything unknown/missing to 'neutral'.
const MOOD_ALIASES = { low: 'negative', medium: 'neutral', high: 'positive' };

export const normalizeMood = (mood) => {
  const key = (mood || '').toString().toLowerCase();
  if (key === 'positive' || key === 'neutral' || key === 'negative') {
    return key;
  }
  return MOOD_ALIASES[key] || 'neutral';
};

export const mapApiEntryToUi = (entry) => {
  const parsedDate = entry.created_at ? new Date(entry.created_at) : new Date();
  const safeTags = Array.isArray(entry.tags) ? entry.tags : [];

  return {
    id: String(entry.id),
    date: entry.entry_date,
    time: parsedDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    title: entry.title,
    content: entry.content,
    preview: entry.content.slice(0, 120) + (entry.content.length > 120 ? '...' : ''),
    mood: normalizeMood(entry.mood),
    tags: safeTags,
  };
};

export const composeVoiceNoteContent = (baseContent, voiceText) => {
  const cleanBase = (baseContent || '').trimEnd();
  const cleanVoiceText = (voiceText || '').trim();
  if (!cleanVoiceText) {
    return cleanBase;
  }
  return cleanBase ? `${cleanBase}\n\nVoice note: ${cleanVoiceText}` : `Voice note: ${cleanVoiceText}`;
};
