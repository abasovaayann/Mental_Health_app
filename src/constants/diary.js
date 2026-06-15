// Shared constants for the Diary feature (prompts, tags, mood styling).

export const DAILY_PROMPTS = [
  'What happened today that affected your mood the most, and why do you think it stayed with you?',
  'Which moment today gave you even a small sense of relief or calm?',
  'What thought kept repeating in your mind, and what might it be asking for?',
  'If you could offer yourself one kind sentence today, what would it be?',
  'What felt heavy today, and what helped you carry it?'
];

export const TAG_SUGGESTIONS = ['study', 'sleep', 'exam', 'family', 'anxiety', 'focus', 'gratitude', 'stress'];

export const CALENDAR_VISIBLE_ENTRIES_LIMIT = 6;

export const VOICE_LANGUAGES = [
  { value: 'en-US', label: 'English' },
  { value: 'ru-RU', label: 'Russian' },
  { value: 'tr-TR', label: 'Turkish' },
];

export const moodMeta = {
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

export const moodRank = { negative: 3, neutral: 2, positive: 1 };
