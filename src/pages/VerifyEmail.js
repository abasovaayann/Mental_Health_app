import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

const RESEND_COOLDOWN_SECONDS = 30;

const getStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}');
  } catch {
    return {};
  }
};

const nextRouteFor = (user) => (user.baselineCompleted ? '/dashboard' : '/baseline-survey');

const VerifyEmail = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(getStoredUser);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  // Not logged in, or already verified — leave this page.
  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/auth');
    } else if (user.isVerified) {
      navigate(nextRouteFor(user));
    }
  }, [user, navigate]);

  // Resend cooldown ticker.
  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const finishVerified = useCallback(() => {
    const updated = { ...user, isVerified: true };
    localStorage.setItem('user', JSON.stringify(updated));
    navigate(nextRouteFor(updated));
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = code.trim();
    if (trimmed.length < 4) {
      setError('Enter the code from your email.');
      return;
    }
    setLoading(true);
    setError('');
    setInfo('');
    try {
      await api.post('/auth/verify-email', { code: trimmed });
      finishVerified();
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    setError('');
    setInfo('');
    try {
      const res = await api.post('/auth/resend-verification');
      if (res.data?.isVerified) {
        finishVerified();
        return;
      }
      setInfo('A new code is on its way to your inbox.');
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not resend the code. Try again later.');
    } finally {
      setResending(false);
    }
  };

  const handleUseDifferent = () => {
    // Verification is mandatory, so there is no "skip" — let the user log out
    // and start over with a different/correct email instead.
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    navigate('/auth');
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background-light p-6 dark:bg-background-dark">
      <div className="w-full max-w-md rounded-2xl border border-slate-100 bg-surface-light p-8 shadow-sm dark:border-border-dark dark:bg-surface-dark">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
            <span className="material-symbols-outlined text-3xl">mark_email_read</span>
          </div>
          <h1 className="font-display text-2xl font-bold text-slate-800 dark:text-slate-100">Verify your email</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            We sent a 6-digit code to{' '}
            <span className="font-semibold text-slate-700 dark:text-slate-200">{user.email || 'your inbox'}</span>.
            Enter it below to confirm this address.
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
            {error}
          </div>
        )}
        {info && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300">
            {info}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            placeholder="------"
            className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-center text-2xl font-bold tracking-[0.5em] text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Verifying…' : 'Verify Email'}
          </button>
        </form>

        <div className="mt-6 flex items-center justify-between text-sm">
          <button
            type="button"
            onClick={handleResend}
            disabled={resending || cooldown > 0}
            className="font-semibold text-blue-600 hover:underline disabled:opacity-50 disabled:no-underline dark:text-blue-400"
          >
            {cooldown > 0 ? `Resend in ${cooldown}s` : resending ? 'Sending…' : 'Resend code'}
          </button>
          <button
            type="button"
            onClick={handleUseDifferent}
            className="text-slate-500 hover:underline dark:text-slate-400"
          >
            Use a different email
          </button>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400 dark:text-slate-500">
          Email reminders are only sent to verified addresses.
        </p>
      </div>
    </div>
  );
};

export default VerifyEmail;
