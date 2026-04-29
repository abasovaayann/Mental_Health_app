import React from 'react';

const MOOD_STYLES = {
  joyful: { icon: 'sentiment_satisfied', bg: 'bg-emerald-50 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300' },
  calm: { icon: 'self_improvement', bg: 'bg-blue-50 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300' },
  grounded: { icon: 'eco', bg: 'bg-emerald-50 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300' },
  inspired: { icon: 'auto_awesome', bg: 'bg-purple-50 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300' },
  anxious: { icon: 'psychology_alt', bg: 'bg-orange-50 dark:bg-orange-900/30', text: 'text-orange-700 dark:text-orange-300' },
  tired: { icon: 'bedtime', bg: 'bg-slate-100 dark:bg-slate-700/40', text: 'text-slate-700 dark:text-slate-300' },
  sad: { icon: 'sentiment_dissatisfied', bg: 'bg-indigo-50 dark:bg-indigo-900/30', text: 'text-indigo-700 dark:text-indigo-300' },
};

const DEFAULT_STYLE = { icon: 'edit_note', bg: 'bg-slate-100 dark:bg-slate-700/40', text: 'text-slate-600 dark:text-slate-300' };

const getMoodStyle = (mood) => {
  if (!mood) return DEFAULT_STYLE;
  return MOOD_STYLES[mood.toLowerCase()] || DEFAULT_STYLE;
};

const formatRelativeDate = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  if (d.toDateString() === now.toDateString()) return `Today • ${time}`;
  if (d.toDateString() === yesterday.toDateString()) return `Yesterday • ${time}`;
  return `${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} • ${time}`;
};

const wordCount = (text) => {
  if (!text) return 0;
  return text.trim().split(/\s+/).filter(Boolean).length;
};

const DiaryCard = ({ entry, onEdit, onDelete }) => {
  const mood = getMoodStyle(entry.mood);
  const moodLabel = entry.mood || 'Note';

  return (
    <div className="diary-card group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-slate-100 bg-white p-6 shadow-md transition-all duration-300 hover:shadow-xl dark:border-slate-700 dark:bg-slate-800">
      <div className="pointer-events-none absolute -right-6 -top-6 opacity-5 transition-opacity group-hover:opacity-10">
        <span className="material-symbols-outlined" style={{ fontSize: 120 }}>{mood.icon}</span>
      </div>

      <div className="relative z-10">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400">
              {formatRelativeDate(entry.created_at)}
            </span>
            <h4 className="truncate font-display text-lg font-bold text-slate-800 dark:text-slate-100">
              {entry.title || 'Untitled'}
            </h4>
          </div>
          <span className={`flex shrink-0 items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${mood.bg} ${mood.text}`}>
            <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: '"FILL" 1' }}>{mood.icon}</span>
            {moodLabel}
          </span>
        </div>
        <p className="mb-6 line-clamp-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {entry.content}
        </p>
        {entry.tags && entry.tags.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-1.5">
            {entry.tags.slice(0, 4).map((tag) => (
              <span key={tag} className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="relative z-10 flex items-center justify-between border-t border-slate-50 pt-4 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/30">
            <span className="material-symbols-outlined text-lg text-blue-500 dark:text-blue-300">edit_note</span>
          </div>
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{wordCount(entry.content)} words</span>
        </div>
        <div className="hover-actions flex gap-1 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(entry)}
              className="rounded-lg p-2 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-300 dark:hover:bg-blue-900/30"
              title="Edit entry"
            >
              <span className="material-symbols-outlined text-xl">edit</span>
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={() => onDelete(entry)}
              className="rounded-lg p-2 text-rose-500 transition-colors hover:bg-rose-50 dark:hover:bg-rose-900/30"
              title="Delete entry"
            >
              <span className="material-symbols-outlined text-xl">delete</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default DiaryCard;
