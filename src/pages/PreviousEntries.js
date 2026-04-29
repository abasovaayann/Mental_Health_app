import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import Sidebar from '../components/Sidebar';

const moodPalette = {
  positive: {
    label: 'Joyful',
    card: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    accent: 'from-emerald-400 to-emerald-500',
    dot: 'bg-emerald-500',
    calendar: 'bg-emerald-500 text-white shadow-emerald-500/20',
    calendarSoft: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-500/30',
  },
  neutral: {
    label: 'Calm',
    card: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    accent: 'from-blue-400 to-cyan-500',
    dot: 'bg-blue-500',
    calendar: 'bg-blue-500 text-white shadow-blue-500/20',
    calendarSoft: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:ring-blue-500/30',
  },
  negative: {
    label: 'Stressed',
    card: 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
    accent: 'from-orange-400 to-amber-500',
    dot: 'bg-orange-500',
    calendar: 'bg-orange-500 text-white shadow-orange-500/20',
    calendarSoft: 'bg-orange-50 text-orange-700 ring-1 ring-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:ring-orange-500/30',
  },
  sad: {
    label: 'Low Mood',
    card: 'bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
    accent: 'from-violet-400 to-slate-500',
    dot: 'bg-violet-500',
    calendar: 'bg-violet-500 text-white shadow-violet-500/20',
    calendarSoft: 'bg-violet-50 text-violet-700 ring-1 ring-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:ring-violet-500/30',
  },
};

const weekdayLabels = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

const todayISO = () => {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const formatDateInput = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const formatDateTime = (value) => {
  if (!value) {
    return '';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '';
  }

  return `${parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} · ${parsed.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })}`;
};

const getMoodKey = (mood) => {
  const value = String(mood || '').toLowerCase();
  if (value.includes('joy') || value.includes('happy') || value.includes('positive') || value.includes('high')) {
    return 'positive';
  }
  if (value.includes('sad') || value.includes('low') || value.includes('gray') || value.includes('grey')) {
    return 'sad';
  }
  if (value.includes('anx') || value.includes('stress') || value.includes('negative') || value.includes('angry') || value.includes('fear')) {
    return 'negative';
  }
  return 'neutral';
};

const getCalendarGrid = (year, month) => {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startOffset = (firstDay.getDay() + 6) % 7;
  const days = [];

  const prevMonthLastDate = new Date(year, month, 0).getDate();
  for (let offset = startOffset - 1; offset >= 0; offset -= 1) {
    days.push({ day: prevMonthLastDate - offset, currentMonth: false });
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

const createEntryMap = (entries) => {
  return entries.reduce((acc, entry) => {
    const dateKey = entry.entry_date;
    if (!acc[dateKey]) {
      acc[dateKey] = [];
    }
    acc[dateKey].push(entry);
    return acc;
  }, {});
};

const mapApiEntry = (entry) => {
  const tags = Array.isArray(entry.tags) ? entry.tags.filter(Boolean) : [];
  const moodKey = getMoodKey(entry.mood);

  return {
    id: String(entry.id),
    entry_date: entry.entry_date,
    created_at: entry.created_at,
    title: entry.title || 'Untitled',
    content: entry.content || '',
    preview: entry.content ? `${entry.content.slice(0, 140)}${entry.content.length > 140 ? '...' : ''}` : '',
    mood: moodKey,
    moodLabel: moodPalette[moodKey].label,
    tags,
  };
};

const EntryCard = ({ entry, onEdit, onDelete }) => {
  const mood = moodPalette[entry.mood] || moodPalette.neutral;

  return (
    <article className="group relative overflow-hidden rounded-3xl border border-slate-100 bg-white p-6 shadow-[0_10px_30px_rgba(15,23,42,0.06)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_18px_40px_rgba(15,23,42,0.12)] dark:border-slate-700 dark:bg-slate-900">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${mood.accent}`} />
      <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-slate-100/60 blur-2xl transition-opacity group-hover:opacity-80 dark:bg-slate-700/30" />

      <div className="relative z-10 flex h-full flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-display text-lg font-bold text-slate-800 dark:text-white">{entry.title}</h3>
            <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">{formatDateTime(entry.created_at)}</p>
          </div>
          <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${mood.card}`}>{entry.moodLabel}</span>
        </div>

        <p className="line-clamp-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {entry.preview || 'No preview available.'}
        </p>

        {entry.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {entry.tags.map((tag) => (
              <span
                key={`${entry.id}-${tag}`}
                className={`rounded-full px-3 py-1 text-[11px] font-semibold ${mood.calendarSoft}`}
              >
                #{String(tag).replace(/^#/, '')}
              </span>
            ))}
          </div>
        )}

        <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-4 dark:border-slate-800">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
            <span className={`h-2.5 w-2.5 rounded-full ${mood.dot}`} />
            Saved entry
          </div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <button
              type="button"
              onClick={() => onEdit(entry)}
              className="rounded-xl px-3 py-2 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-300 dark:hover:bg-blue-900/20"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => onDelete(entry)}
              className="rounded-xl px-3 py-2 text-rose-600 transition-colors hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-900/20"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </article>
  );
};

const PreviousEntries = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [calendarDate, setCalendarDate] = useState(() => new Date());

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) {
      navigate('/auth');
    }
  }, [navigate]);

  useEffect(() => {
    const loadEntries = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await api.get('/diary/entries');
        const mappedEntries = Array.isArray(response.data) ? response.data.map(mapApiEntry) : [];
        setEntries(mappedEntries);
      } catch (fetchError) {
        console.error('Failed to load diary entries', fetchError);
        setError('Unable to load previous entries right now.');
        setEntries([]);
      } finally {
        setLoading(false);
      }
    };

    loadEntries();
  }, []);

  const newEntryRoute = useMemo(() => '/diary/new', []);
  const filteredEntries = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();

    return entries.filter((entry) => {
      const matchesDate = !selectedDate || entry.entry_date === selectedDate;
      if (!matchesDate) {
        return false;
      }

      if (!normalizedQuery) {
        return true;
      }

      const haystack = [
        entry.title,
        entry.content,
        entry.moodLabel,
        ...entry.tags,
      ]
        .join(' ')
        .toLowerCase();

      return haystack.includes(normalizedQuery);
    });
  }, [entries, searchQuery, selectedDate]);

  const entriesByDate = useMemo(() => createEntryMap(entries), [entries]);

  const moodByDate = useMemo(() => {
    return Object.entries(entriesByDate).reduce((acc, [dateKey, dayEntries]) => {
      const moods = Array.from(new Set(dayEntries.map((entry) => entry.mood)));
      acc[dateKey] = moods;
      return acc;
    }, {});
  }, [entriesByDate]);

  const calendarDays = useMemo(
    () => getCalendarGrid(calendarDate.getFullYear(), calendarDate.getMonth()),
    [calendarDate]
  );

  const openCalendar = () => {
    const baseDate = selectedDate ? new Date(`${selectedDate}T00:00:00`) : new Date();
    setCalendarDate(Number.isNaN(baseDate.getTime()) ? new Date() : baseDate);
    setCalendarOpen(true);
  };

  const closeCalendar = () => setCalendarOpen(false);

  const handleEdit = (entry) => {
    sessionStorage.setItem('diary_edit_entry_id', entry.id);
    navigate(`/diary/entry/${entry.entry_date}`);
  };

  const handleDelete = async (entry) => {
    try {
      await api.delete(`/diary/entries/${entry.id}`);
      setEntries((current) => current.filter((item) => item.id !== entry.id));
    } catch (deleteError) {
      console.error('Failed to delete diary entry', deleteError);
    }
  };

  const shiftMonth = (delta) => {
    setCalendarDate((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  };

  const selectDate = (dateKey) => {
    setSelectedDate(dateKey);
    setCalendarOpen(false);
  };

  const clearFilter = () => {
    setSelectedDate('');
  };

  const renderCalendarDay = (item, index) => {
    const cellDate = formatDateInput(new Date(calendarDate.getFullYear(), calendarDate.getMonth(), item.day));
    const moods = moodByDate[cellDate] || [];
    const hasEntries = moods.length > 0;
    const isSelected = selectedDate === cellDate;
    const isToday = cellDate === todayISO();

    const firstMood = moodPalette[moods[0]] || moodPalette.neutral;
    const secondMood = moodPalette[moods[1]] || moodPalette.neutral;
    const baseClass = hasEntries
      ? moods.length > 1
        ? `bg-gradient-to-br ${firstMood.accent} ${secondMood.accent} text-white shadow-lg`
        : `${firstMood.calendar} ${isSelected ? 'ring-2 ring-offset-2 ring-slate-300 dark:ring-slate-500' : ''}`
      : isToday
        ? 'bg-slate-900 text-white shadow-lg dark:bg-white dark:text-slate-900'
        : item.currentMonth
          ? 'bg-slate-50 text-slate-700 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
          : 'cursor-not-allowed text-slate-400 dark:text-slate-600';

    return (
      <button
        key={`${item.day}-${index}`}
        type="button"
        disabled={!item.currentMonth || !hasEntries}
        onClick={() => {
          if (hasEntries) {
            selectDate(cellDate);
          }
        }}
        className={`relative aspect-square rounded-2xl text-sm font-semibold transition-all disabled:cursor-not-allowed ${baseClass}`}
      >
        {item.day}
        {hasEntries && moods.length > 1 && (
          <span className="absolute bottom-1.5 left-1/2 flex -translate-x-1/2 gap-1">
            {moods.slice(0, 3).map((mood) => (
              <span key={`${cellDate}-${mood}`} className={`h-1.5 w-1.5 rounded-full ${moodPalette[mood]?.dot || moodPalette.neutral.dot}`} />
            ))}
          </span>
        )}
        {isSelected && hasEntries && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-white/90" />}
      </button>
    );
  };

  return (
    <div className="h-screen overflow-hidden bg-background-light text-text-primary-light dark:bg-background-dark dark:text-text-primary-dark lg:flex">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        footerSlot={
          <button
            type="button"
            onClick={() => navigate(newEntryRoute)}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-white/10 py-3.5 font-semibold text-white transition-all hover:bg-white/15"
          >
            <span className="material-symbols-outlined text-sm font-bold">edit</span>
            <span className="text-sm">New Entry</span>
          </button>
        }
      />

      <main className="custom-scrollbar h-full flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">

          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800/50 dark:bg-rose-900/20 dark:text-rose-200">
              {error}
            </div>
          )}

          <section className="rounded-3xl border border-slate-100 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-xl font-bold text-slate-900 dark:text-white">Saved reflections</h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  {selectedDate
                    ? `Showing entries for selected date. ${new Date(`${selectedDate}T00:00:00`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`
                    : 'Showing all saved entries'}
                </p>
              </div>

              <div className="flex items-center gap-2">
                {selectedDate && (
                  <button
                    type="button"
                    onClick={clearFilter}
                    className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Clear date filter
                  </button>
                )}
                <span className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {filteredEntries.length} entr{filteredEntries.length === 1 ? 'y' : 'ies'}
                </span>
              </div>
            </div>

            <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center">
              <label className="relative flex-1">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                  <span className="material-symbols-outlined text-[20px]">search</span>
                </span>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search title, mood, tags, or diary text"
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3 pl-12 pr-4 text-sm text-slate-700 placeholder:text-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
                />
              </label>

              <button
                type="button"
                onClick={openCalendar}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                <span className="material-symbols-outlined text-[18px]">calendar_month</span>
                Filter by date
              </button>
            </div>

            {loading ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="h-56 animate-pulse rounded-3xl bg-slate-100 dark:bg-slate-800" />
                ))}
              </div>
            ) : filteredEntries.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {filteredEntries.map((entry) => (
                  <EntryCard key={entry.id} entry={entry} onEdit={handleEdit} onDelete={handleDelete} />
                ))}
              </div>
            ) : (
              <div className="rounded-3xl border border-dashed border-slate-200 bg-slate-50 px-6 py-12 text-center dark:border-slate-700 dark:bg-slate-800/40">
                <p className="font-display text-xl font-bold text-slate-800 dark:text-white">No entries found</p>
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                  {selectedDate || searchQuery ? 'Try another filter or clear the selected date.' : 'Create your first diary entry to see it here.'}
                </p>
              </div>
            )}
          </section>
        </div>
      </main>

      {calendarOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
          <button type="button" aria-label="Close calendar" onClick={closeCalendar} className="fixed inset-0 cursor-default" />
          <div className="relative z-10 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Calendar</p>
                <h3 className="mt-1 font-display text-xl font-bold text-slate-900 dark:text-white">
                  {calendarDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Select a highlighted day to filter entries.</p>
              </div>
              <button
                type="button"
                onClick={closeCalendar}
                className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="mb-4 flex items-center justify-between">
              <button
                type="button"
                onClick={() => shiftMonth(-1)}
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                <span className="material-symbols-outlined text-[20px]">chevron_left</span>
              </button>
              <div className="text-sm font-semibold text-slate-600 dark:text-slate-300">Diary mood calendar</div>
              <button
                type="button"
                onClick={() => shiftMonth(1)}
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                <span className="material-symbols-outlined text-[20px]">chevron_right</span>
              </button>
            </div>

            <div className="mb-3 grid grid-cols-7 gap-2 text-center text-[11px] font-bold uppercase tracking-wider text-slate-400">
              {weekdayLabels.map((day) => (
                <span key={day}>{day}</span>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-2 text-sm">
              {calendarDays.map(renderCalendarDay)}
            </div>

            <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 dark:bg-slate-800">
                <span className="h-2 w-2 rounded-full bg-emerald-500" /> Joyful
              </span>
              <span className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 dark:bg-slate-800">
                <span className="h-2 w-2 rounded-full bg-blue-500" /> Calm
              </span>
              <span className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 dark:bg-slate-800">
                <span className="h-2 w-2 rounded-full bg-orange-500" /> Stressed
              </span>
              <span className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 dark:bg-slate-800">
                <span className="h-2 w-2 rounded-full bg-violet-500" /> Low mood
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PreviousEntries;
