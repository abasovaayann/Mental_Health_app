// Helpers for the Dashboard feature: check-in mapping/aggregation, date keys,
// the rotating startup quote, and risk-level styling. The pure functions here
// are unit-tested in isolation.

import { DASHBOARD_QUOTES } from '../data/quotes';
import { DAILY_CHECKIN_FIELDS } from '../constants/dashboard';

export const mapApiCheckinToUi = (row) => ({
  moodLevel: Number(row.mood_level),
  sleepQuality: Number(row.sleep_quality),
  energyLevel: Number(row.energy_level),
});

export const getDateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const getLastSevenDates = () => {
  const days = [];
  const today = new Date();
  for (let i = 6; i >= 0; i -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - i);
    days.push(date);
  }
  return days;
};

export const getCheckinAverage = (entry) => {
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

export const areCheckinsEqual = (a, b) => {
  if (!a || !b) {
    return false;
  }

  return DAILY_CHECKIN_FIELDS.every((field) => Number(a[field.key]) === Number(b[field.key]));
};

export const pickStartupQuote = () => {
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

export const getRiskStyles = (riskLevel) => {
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

export const formatDate = (value) => {
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
