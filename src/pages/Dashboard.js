import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { DASHBOARD_QUOTES } from '../data/quotes';

const navItems = [
  { key: 'home', label: 'Home', icon: 'home', path: '/dashboard' },
  { key: 'diary', label: 'Diary', icon: 'book_2', path: '/diary' },
  { key: 'analytics', label: 'Analytics', icon: 'analytics', disabled: true },
  { key: 'settings', label: 'Settings', icon: 'settings', path: '/settings' },
];

const DAILY_CHECKIN_FIELDS = [
  { key: 'moodLevel', label: 'Mood Level', icon: 'mood' },
  { key: 'sleepQuality', label: 'Sleep Quality', icon: 'bedtime' },
  { key: 'energyLevel', label: 'Energy Level', icon: 'bolt' },
];

const mapApiCheckinToUi = (row) => ({
  moodLevel: Number(row.mood_level),
  sleepQuality: Number(row.sleep_quality),
  energyLevel: Number(row.energy_level),
});

const getDateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const getLastSevenDates = () => {
  const days = [];
  const today = new Date();
  for (let i = 6; i >= 0; i -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - i);
    days.push(date);
  }
  return days;
};

const getCheckinAverage = (entry) => {
  if (!entry) {
    return null;
  }

  const values = [entry.moodLevel, entry.sleepQuality, entry.energyLevel]
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));

  if (!values.length) {
    return null;
  }

  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
};

const areCheckinsEqual = (a, b) => {
  if (!a || !b) {
    return false;
  }

  return DAILY_CHECKIN_FIELDS.every((field) => Number(a[field.key]) === Number(b[field.key]));
};

const pickStartupQuote = () => {
  if (!DASHBOARD_QUOTES.length) {
    return { text: 'Take one steady step today.', author: 'MindTrackAi', category: 'motivation' };
  }

  const key = 'dashboard_startup_quote_index';
  const savedIndex = sessionStorage.getItem(key);

  if (savedIndex !== null) {
    const parsed = Number(savedIndex);
    if (!Number.isNaN(parsed) && DASHBOARD_QUOTES[parsed]) {
      return DASHBOARD_QUOTES[parsed];
    }
  }

  const randomIndex = Math.floor(Math.random() * DASHBOARD_QUOTES.length);
  sessionStorage.setItem(key, String(randomIndex));
  return DASHBOARD_QUOTES[randomIndex];
};

const getRiskStyles = (riskLevel) => {
  if (riskLevel === 0) {
    return {
      badge: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
      ring: 'from-emerald-500 to-green-500',
      iconBg: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300',
      soft: 'bg-emerald-50 border-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-900/40',
      progress: 'bg-emerald-500',
    };
  }

  if (riskLevel === 1) {
    return {
      badge: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
      ring: 'from-amber-500 to-yellow-500',
      iconBg: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300',
      soft: 'bg-amber-50 border-amber-100 dark:bg-amber-900/20 dark:border-amber-900/40',
      progress: 'bg-amber-500',
    };
  }

  return {
    badge: 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
    ring: 'from-rose-500 to-red-500',
    iconBg: 'bg-rose-50 text-rose-600 dark:bg-rose-900/30 dark:text-rose-300',
    soft: 'bg-rose-50 border-rose-100 dark:bg-rose-900/20 dark:border-rose-900/40',
    progress: 'bg-rose-500',
  };
};


const formatDate = (value) => {
  if (!value) {
    return 'No recent activity yet';
  }

  return new Date(value).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [score, setScore] = useState(null);
  const [activityStats, setActivityStats] = useState({ currentStreak: 0, totalEntries: 0, lastEntryAt: null });
  const [diaryStats, setDiaryStats] = useState({ totalEntries: 0, lastEntryAt: null });
  const [dailyCheckin, setDailyCheckin] = useState({ moodLevel: 68, sleepQuality: 70, energyLevel: 66 });
  const [dailyCheckinHistory, setDailyCheckinHistory] = useState({});
  const [scoreLoading, setScoreLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) {
      navigate('/auth');
      return;
    }

    setUser(JSON.parse(userData));
  }, [navigate]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      const [profileResult, scoreResult, activityResult, diaryResult, checkinsResult] = await Promise.allSettled([
        api.get('/auth/me'),
        api.get('/survey/wellness-score'),
        api.get('/survey/activity-stats'),
        api.get('/diary/stats'),
        api.get('/survey/daily-checkins'),
      ]);

      if (profileResult.status === 'fulfilled') {
        const profile = profileResult.value.data;
        setUser((currentUser) => ({
          ...currentUser,
          firstName: profile.first_name,
          lastName: profile.last_name,
          email: profile.email,
          baselineCompleted: profile.baseline_completed,
          baselineCompletedAt: profile.baseline_completed_at,
          createdAt: profile.created_at,
          degree: profile.degree,
          university: profile.university,
        }));
      } else if (profileResult.reason?.response?.status !== 404) {
        console.error('Could not load profile data', profileResult.reason);
      }

      if (scoreResult.status === 'fulfilled') {
        setScore(scoreResult.value.data.prediction);
      } else if (scoreResult.reason?.response?.status !== 404) {
        console.error('Could not load wellness score', scoreResult.reason);
      }

      if (activityResult.status === 'fulfilled') {
        setActivityStats({
          currentStreak: activityResult.value.data.current_streak ?? 0,
          totalEntries: activityResult.value.data.total_entries ?? 0,
          lastEntryAt: activityResult.value.data.last_entry_at ?? null,
        });
      } else if (activityResult.reason?.response?.status !== 404) {
        console.error('Could not load activity stats', activityResult.reason);
      }

      if (diaryResult.status === 'fulfilled') {
        setDiaryStats({
          totalEntries: diaryResult.value.data.total_entries ?? 0,
          lastEntryAt: diaryResult.value.data.last_entry_at ?? null,
        });
      } else if (diaryResult.reason?.response?.status !== 404) {
        console.error('Could not load diary stats', diaryResult.reason);
      }

      if (checkinsResult.status === 'fulfilled') {
        const rows = Array.isArray(checkinsResult.value.data) ? checkinsResult.value.data : [];
        const historyMap = rows.reduce((acc, row) => {
          acc[row.checkin_date] = mapApiCheckinToUi(row);
          return acc;
        }, {});
        setDailyCheckinHistory(historyMap);
        const currentDateKey = getDateKey(new Date());
        if (historyMap[currentDateKey]) {
          setDailyCheckin(historyMap[currentDateKey]);
        }
      } else if (checkinsResult.reason?.response?.status !== 404) {
        console.error('Could not load daily check-ins', checkinsResult.reason);
      }

      if (
        profileResult.status === 'rejected' &&
        scoreResult.status === 'rejected' &&
        activityResult.status === 'rejected' &&
        diaryResult.status === 'rejected' &&
        checkinsResult.status === 'rejected'
      ) {
        const firstError = profileResult.reason || scoreResult.reason || activityResult.reason || diaryResult.reason || checkinsResult.reason;
        if (firstError?.response?.status !== 404) {
          console.error('Could not load dashboard data', firstError);
        }
      }

      setScoreLoading(false);
    };

    const token = localStorage.getItem('token');
    if (token) {
      fetchDashboardData();
    }
  }, []);

  const handleCheckinChange = (field, value) => {
    setDailyCheckin((prev) => ({ ...prev, [field]: Number(value) }));
  };

  const todayKey = useMemo(() => getDateKey(new Date()), []);
  const todaysSavedCheckin = dailyCheckinHistory[todayKey] || null;

  const isCheckinChanged = useMemo(
    () => !areCheckinsEqual(todaysSavedCheckin, dailyCheckin),
    [todaysSavedCheckin, dailyCheckin]
  );

  const handleSaveDailyCheckin = async () => {
    try {
      await api.put('/survey/daily-checkin', {
        checkin_date: todayKey,
        mood_level: Number(dailyCheckin.moodLevel),
        sleep_quality: Number(dailyCheckin.sleepQuality),
        energy_level: Number(dailyCheckin.energyLevel),
      });

      const nextHistory = {
        ...dailyCheckinHistory,
        [todayKey]: dailyCheckin,
      };
      setDailyCheckinHistory(nextHistory);
    } catch (error) {
      console.error('Failed to save daily check-in', error);
    }
  };

  const todayLabel = useMemo(
    () =>
      new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      }),
    []
  );

  const quote = useMemo(() => pickStartupQuote(), []);

  const weeklyCheckinData = useMemo(
    () =>
      getLastSevenDates().map((date) => {
        const key = getDateKey(date);
        return {
          key,
          label: date.toLocaleDateString('en-US', { weekday: 'short' }),
          value: getCheckinAverage(dailyCheckinHistory[key]),
        };
      }),
    [dailyCheckinHistory]
  );

  const weeklyCompletedCount = useMemo(
    () => weeklyCheckinData.filter((day) => day.value !== null).length,
    [weeklyCheckinData]
  );

  const weeklyCompletionPercent = useMemo(
    () => Math.round((weeklyCompletedCount / 7) * 100),
    [weeklyCompletedCount]
  );
  const riskStyles = getRiskStyles(score?.risk_level ?? 1);
  const totalEntriesValue = diaryStats.totalEntries;

  const stats = [
    {
      label: 'Wellness Score',
      value: scoreLoading ? '...' : score ? `${score.wellness_score}/100` : 'Pending',
      icon: 'monitoring',
      iconClass: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300',
    },
    {
      label: 'Risk Probability',
      value: scoreLoading ? '...' : score ? `${(score.risk_probability * 100).toFixed(1)}%` : 'Unavailable',
      icon: 'network_intelligence',
      iconClass: 'bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:text-orange-300',
    },
    {
      label: 'Current Streak',
      value: scoreLoading ? '...' : `${activityStats.currentStreak} day${activityStats.currentStreak === 1 ? '' : 's'}`,
      icon: 'local_fire_department',
      iconClass: 'bg-rose-50 text-rose-600 dark:bg-rose-900/30 dark:text-rose-300',
    },
    {
      label: 'Total Entries',
      value: scoreLoading ? '...' : totalEntriesValue,
      icon: 'edit_note',
      iconClass: 'bg-cyan-50 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-300',
    },
  ];

  const recentActivity = [
    {
      title: score ? 'Wellness score generated' : 'Wellness score waiting for survey',
      time: score ? 'Latest prediction available' : 'Complete your baseline survey to unlock insights',
      icon: 'auto_graph',
      iconClass: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300',
    },
    {
      title: 'Account registered',
      time: user?.createdAt ? formatDate(user.createdAt) : 'Registration date unavailable',
      icon: 'person_add',
      iconClass: 'bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-300',
    },
    {
      title: diaryStats.totalEntries > 0 ? 'Latest diary entry' : 'No diary entries yet',
      time: diaryStats.lastEntryAt
        ? formatDate(diaryStats.lastEntryAt)
        : 'Complete a check-in or survey to create your first entry',
      icon: 'schedule',
      iconClass: 'bg-teal-50 text-teal-600 dark:bg-teal-900/30 dark:text-teal-300',
    },
  ];

  if (!user) {
    return null;
  }

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
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col justify-between bg-blue-900 px-6 py-6 text-white shadow-2xl transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } overflow-y-auto`}
      >
        <div className="flex flex-col gap-8">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-3xl">self_improvement</span>
            <span className="font-display text-xl font-bold tracking-wide">MindTrackAi</span>
          </div>

          <nav className="flex flex-col gap-2">
            {navItems.map((item) => {
              const active = item.path === '/dashboard';

              return (
                <button
                  key={item.key}
                  type="button"
                  disabled={item.disabled}
                  onClick={() => {
                    if (item.path) {
                      navigate(item.path);
                      setSidebarOpen(false);
                    }
                  }}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 text-left font-medium transition-all ${
                    active
                      ? 'bg-blue-500/30 text-white'
                      : item.disabled
                        ? 'cursor-not-allowed text-blue-200/60'
                        : 'text-blue-100 hover:bg-white/10'
                  }`}
                >
                  <span className="material-symbols-outlined">{item.icon}</span>
                  <span>{item.label}</span>
                  {item.disabled && <span className="ml-auto text-[10px] uppercase tracking-wide">Soon</span>}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="border-t border-blue-800/60 pt-6">
          <button
            type="button"
            onClick={() => navigate('/settings')}
            className="flex w-full items-center gap-3 rounded-xl p-2 text-left transition hover:bg-white/10"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-blue-300 to-blue-500 font-bold text-blue-950">
              {(user.firstName?.[0] || 'U').toUpperCase()}
              {(user.lastName?.[0] || '').toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{user.firstName} {user.lastName}</p>
              <p className="truncate text-xs text-blue-200">View Profile</p>
            </div>
          </button>
        </div>
      </aside>

      <main className="h-full flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
        <div className="w-full space-y-8">
          <header className="flex flex-col gap-4">
            <div className="flex items-start gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="mt-1 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-slate-600 shadow-sm dark:bg-slate-800 dark:text-slate-200 lg:hidden"
              >
                <span className="material-symbols-outlined">menu</span>
              </button>
              <div>
                <h1 className="font-display text-3xl font-bold text-text-heading md:text-4xl">
                  Good {new Date().getHours() < 12 ? 'Morning' : new Date().getHours() < 18 ? 'Afternoon' : 'Evening'}, {user.firstName}
                </h1>
                <p className="mt-1 flex items-center gap-2 font-medium text-text-secondary-light dark:text-text-secondary-dark">
                  <span className="material-symbols-outlined text-sm">calendar_month</span>
                  {todayLabel}
                </p>
              </div>
            </div>
          </header>

          <section className="relative overflow-hidden rounded-[28px] bg-gradient-to-r from-blue-700 via-blue-600 to-blue-500 p-8 text-white shadow-lg md:p-10">
            <div className="relative z-10">
              <div className="max-w-4xl">
                <p className="font-serif text-2xl italic leading-relaxed text-blue-50 md:text-3xl md:whitespace-nowrap">
                  &ldquo;{quote.text}&rdquo;
                </p>
                <p className="mt-4 text-sm font-semibold uppercase tracking-[0.18em] text-blue-100 md:text-base">
                  - {quote.author || 'MindTrackAi'}
                </p>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-cols-4">
            <div className="rounded-2xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark md:col-span-2 lg:col-span-2">
              <div className="mb-4 flex items-center gap-3">
                <div className={`rounded-xl p-3 ${riskStyles.iconBg}`}>
                  <span className="material-symbols-outlined text-2xl">psychology</span>
                </div>
                <h3 className="font-display text-xl font-bold text-slate-800 dark:text-slate-100">Your wellness overview</h3>
              </div>

              <p className="mb-6 text-slate-500 dark:text-slate-400">
                {score
                  ? 'Your latest survey has been analyzed. Review the current risk level and keep your profile updated for better guidance.'
                  : 'Complete your baseline survey to unlock wellness scoring, tailored recommendations, and trend tracking.'}
              </p>

              <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-4">
                  <div className={`flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br ${riskStyles.ring} text-white shadow-lg`}>
                    {scoreLoading ? (
                      <span className="text-sm font-bold">...</span>
                    ) : score ? (
                      <div className="text-center">
                        <div className="text-3xl font-extrabold leading-none">{score.wellness_score}</div>
                        <div className="mt-1 text-xs font-semibold opacity-90">/ 100</div>
                      </div>
                    ) : (
                      <span className="material-symbols-outlined text-3xl">hourglass_top</span>
                    )}
                  </div>

                  <div>
                    <div className={`inline-flex rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ${riskStyles.badge}`}>
                      {score ? score.risk_label : 'Survey Required'}
                    </div>
                    <p className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-100">
                      {scoreLoading ? 'Loading analysis...' : score ? `Risk probability: ${(score.risk_probability * 100).toFixed(1)}%` : 'No prediction available yet'}
                    </p>
                    <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">
                      {score
                        ? 'This indicator helps prioritize support and reflection. It is not a medical diagnosis.'
                        : 'Finish the baseline assessment first so the model can generate your first wellness score.'}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => navigate('/baseline-survey')}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 font-semibold text-white shadow-md transition-all hover:bg-primary-hover"
                >
                  {user.baselineCompleted ? 'Review Survey' : 'Start Check-in'}
                  <span className="material-symbols-outlined text-sm">arrow_forward</span>
                </button>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark md:col-span-1 lg:col-span-2">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h3 className="font-display text-xl font-bold text-slate-800 dark:text-slate-100">Daily Check-in</h3>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Rate each item from 0 to 100</p>
                </div>
                <span className="material-symbols-outlined text-3xl text-blue-500 dark:text-blue-300">task_alt</span>
              </div>

              <div className="space-y-5">
                {DAILY_CHECKIN_FIELDS.map((field) => (
                  <div key={field.key}>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-200">
                        <span className="material-symbols-outlined text-base text-blue-500 dark:text-blue-300">{field.icon}</span>
                        {field.label}
                      </span>
                      <span className="font-bold text-slate-800 dark:text-slate-100">{dailyCheckin[field.key]}/100</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={dailyCheckin[field.key]}
                      onChange={(event) => handleCheckinChange(field.key, event.target.value)}
                      className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-blue-600 dark:bg-slate-700"
                    />
                  </div>
                ))}

                <button
                  type="button"
                  onClick={handleSaveDailyCheckin}
                  disabled={!isCheckinChanged}
                  className={`mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-colors ${
                    isCheckinChanged
                      ? 'bg-blue-600 hover:bg-blue-700'
                      : 'cursor-not-allowed bg-emerald-500/80'
                  }`}
                >
                  <span className="material-symbols-outlined text-base">check_circle</span>
                  {isCheckinChanged ? "Save today's check-in" : "Today's check-in saved"}
                </button>
              </div>
            </div>

            {stats.map((stat) => (
              <div
                key={stat.label}
                className={`rounded-2xl border border-slate-100 bg-surface-light p-5 shadow-sm dark:border-border-dark dark:bg-surface-dark ${stat.button ? 'cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/80' : ''}`}
                onClick={stat.button ? () => navigate('/settings') : undefined}
                role={stat.button ? 'button' : undefined}
                tabIndex={stat.button ? 0 : undefined}
                onKeyDown={stat.button ? (event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    navigate('/settings');
                  }
                } : undefined}
              >
                <div className="flex items-center gap-4">
                  <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${stat.iconClass}`}>
                    <span className="material-symbols-outlined">{stat.icon}</span>
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{stat.label}</p>
                    <p className="text-xl font-bold text-slate-800 dark:text-slate-100">{stat.value}</p>
                  </div>
                </div>
              </div>
            ))}
          </section>

          <section className="grid grid-cols-1 gap-6 pb-8 lg:grid-cols-3">
            <div className="rounded-2xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark lg:col-span-2">
              <div className="mb-6 flex items-center justify-between">
                <h3 className="font-display text-lg font-bold text-slate-800 dark:text-slate-100">Mood Trends</h3>
                <div className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {weeklyCompletedCount}/7 days
                </div>
              </div>

              <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/50">
                <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                  <div
                    className="h-full rounded-full bg-blue-500 transition-all"
                    style={{ width: `${weeklyCompletionPercent}%` }}
                  />
                </div>

                <div className="flex h-40 items-end justify-between gap-2">
                  {weeklyCheckinData.map((day) => {
                    const hasValue = day.value !== null;
                    const barHeight = hasValue ? Math.max(12, Math.round((day.value / 100) * 128)) : 8;
                    return (
                      <div key={day.key} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          {hasValue ? `${day.value}%` : '-'}
                        </div>
                        <div className="flex h-32 w-full items-end rounded-md bg-white px-1 dark:bg-slate-800">
                          <div
                            className={`w-full rounded-sm transition-all ${hasValue ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'}`}
                            style={{ height: `${barHeight}px` }}
                          />
                        </div>
                        <div className="text-xs font-medium text-slate-500 dark:text-slate-400">{day.label}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className={`mt-6 rounded-xl border p-4 ${riskStyles.soft}`}>
                <div className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-primary dark:text-blue-300">insights</span>
                  <div>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">AI summary</p>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                      {score
                        ? `Your current wellness score is ${score.wellness_score}/100 with a ${score.risk_label.toLowerCase()} profile. The strongest next step is consistency: complete check-ins regularly so your trends become more reliable.`
                        : 'Your dashboard is ready, but there is not enough survey data yet for personalized trend analysis.'}
                    </p>
                    {score && (
                      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/70 dark:bg-slate-800">
                        <div className={`h-full rounded-full ${riskStyles.progress}`} style={{ width: `${score.wellness_score}%` }} />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-100 bg-surface-light p-6 shadow-sm dark:border-border-dark dark:bg-surface-dark">
              <h3 className="mb-4 font-display text-lg font-bold text-slate-800 dark:text-slate-100">Recent Activity</h3>
              <div className="space-y-4">
                {recentActivity.map((activity, index) => (
                  <div key={activity.title} className={`flex items-center gap-3 ${index < recentActivity.length - 1 ? 'border-b border-slate-50 pb-3 dark:border-slate-800' : ''}`}>
                    <div className={`rounded-lg p-2 ${activity.iconClass}`}>
                      <span className="material-symbols-outlined text-xl">{activity.icon}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{activity.title}</p>
                      <p className="truncate text-xs text-slate-500 dark:text-slate-400">{activity.time}</p>
                    </div>
                    <span className="material-symbols-outlined text-lg text-slate-300 dark:text-slate-600">chevron_right</span>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-xl bg-blue-50 p-4 dark:bg-blue-900/20">
                <p className="text-xs font-bold uppercase tracking-wide text-blue-700 dark:text-blue-300">Next recommended step</p>
                <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">
                  {user.baselineCompleted
                    ? 'Review your profile and preferences in settings so recommendations stay aligned with your current study context.'
                    : 'Complete the baseline survey first. The rest of the dashboard becomes much more useful once the model has your first response set.'}
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
