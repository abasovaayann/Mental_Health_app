import React, { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';

const TIMEZONES = [
  'UTC',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Istanbul',
  'Europe/Moscow',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Bangkok',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Australia/Sydney',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Toronto',
  'America/Mexico_City',
  'America/Sao_Paulo',
  'Africa/Cairo',
  'Africa/Johannesburg',
];

const ReminderSettings = ({ onToast }) => {
  const [reminders, setReminders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const loadReminders = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/reminders/preferences');
      setReminders(response.data);
      setError(null);
    } catch (err) {
      console.error('Error loading reminders:', err);
      setError('Failed to load reminder settings');
      onToast?.('Error loading reminder settings', 'error');
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  // Load reminders on mount
  useEffect(() => {
    loadReminders();
  }, [loadReminders]);

  const handleUpdate = async () => {
    try {
      setSaving(true);
      await api.put('/reminders/preferences', reminders);
      onToast?.('Reminder settings updated successfully!', 'success');
      setError(null);
    } catch (err) {
      console.error('Error updating reminders:', err);
      setError(err.response?.data?.detail || 'Failed to update reminders');
      onToast?.('Error updating reminder settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDisable = async () => {
    if (!window.confirm('Are you sure you want to disable all reminders?')) {
      return;
    }
    try {
      setSaving(true);
      await api.delete('/reminders/preferences');
      setReminders({ ...reminders, enabled: false });
      onToast?.('Reminders disabled', 'success');
      setError(null);
    } catch (err) {
      console.error('Error disabling reminders:', err);
      setError('Failed to disable reminders');
      onToast?.('Error disabling reminders', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!reminders) {
    return (
      <div className="text-center p-8">
        <p className="text-slate-600 dark:text-slate-400">Unable to load reminder settings</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Message */}
      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Enable/Disable */}
      <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <div>
          <p className="font-semibold text-slate-800 dark:text-slate-100">Email Reminders</p>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Receive daily email reminders to complete your check-in
          </p>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={reminders.enabled}
            onChange={(e) => setReminders({ ...reminders, enabled: e.target.checked })}
            disabled={saving}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-300 dark:bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
        </label>
      </div>

      {reminders.enabled && (
        <div className="space-y-5 p-6 rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50 dark:bg-blue-900/20">
          {/* Reminder Time */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-100 mb-2">
              ⏰ Reminder Time
            </label>
            <input
              type="time"
              value={reminders.reminder_time}
              onChange={(e) => setReminders({ ...reminders, reminder_time: e.target.value })}
              disabled={saving}
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              You'll receive your check-in reminder at this time every day
            </p>
          </div>

          {/* Timezone */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-100 mb-2">
              🌍 Timezone
            </label>
            <select
              value={reminders.reminder_timezone}
              onChange={(e) => setReminders({ ...reminders, reminder_timezone: e.target.value })}
              disabled={saving}
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Reminders will be sent at the specified time in your timezone
            </p>
          </div>

          {/* Frequency */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-100 mb-2">
              📅 Frequency
            </label>
            <div className="flex gap-3">
              {['daily'].map((freq) => (
                <label key={freq} className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    name="frequency"
                    value={freq}
                    checked={reminders.frequency === freq}
                    onChange={(e) => setReminders({ ...reminders, frequency: e.target.value })}
                    disabled={saving}
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 cursor-pointer"
                  />
                  <span className="ml-2 text-sm text-slate-700 dark:text-slate-300 capitalize">
                    {freq}
                  </span>
                </label>
              ))}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Daily reminders help you build a consistent check-in habit
            </p>
          </div>

          {/* Info Box */}
          <div className="rounded-lg bg-white/50 dark:bg-slate-800/50 p-4 border border-blue-100 dark:border-blue-800">
            <p className="text-xs text-slate-600 dark:text-slate-300">
              💡 <strong>Pro tip:</strong> Set your reminder for a time you're usually available and in a good
              mental state to reflect on your day.
            </p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-end pt-6">
        {reminders.enabled && (
          <button
            onClick={handleDisable}
            disabled={saving}
            className="px-6 py-2 text-sm font-semibold rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Disable Reminders
          </button>
        )}
        <button
          onClick={handleUpdate}
          disabled={saving}
          className="px-6 py-2 text-sm font-semibold rounded-lg bg-blue-600 dark:bg-blue-500 text-white hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Saving...
            </>
          ) : (
            '💾 Save Preferences'
          )}
        </button>
      </div>
    </div>
  );
};

export default ReminderSettings;
