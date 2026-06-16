import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api/axios';

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState('request'); // 'request' | 'reset'
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const requestCode = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Enter your email address.');
      return;
    }
    setLoading(true);
    setError('');
    setInfo('');
    try {
      const res = await api.post('/auth/forgot-password', { email: email.trim() });
      setInfo(res.data?.message || 'If that email is registered, a reset code has been sent.');
      setStep('reset');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not send a reset code. Try again later.');
    } finally {
      setLoading(false);
    }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    if (newPassword !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    setError('');
    setInfo('');
    try {
      await api.post('/auth/reset-password', {
        email: email.trim(),
        code: code.trim(),
        new_password: newPassword,
      });
      navigate('/auth', { state: { passwordReset: true } });
    } catch (err) {
      setError(err.response?.data?.detail || 'Reset failed. Check the code and try again.');
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    'w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100';

  return (
    <div className="flex min-h-screen items-center justify-center bg-background-light p-6 dark:bg-background-dark">
      <div className="w-full max-w-md rounded-2xl border border-slate-100 bg-surface-light p-8 shadow-sm dark:border-border-dark dark:bg-surface-dark">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
            <span className="material-symbols-outlined text-3xl">lock_reset</span>
          </div>
          <h1 className="font-display text-2xl font-bold text-slate-800 dark:text-slate-100">Reset your password</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {step === 'request'
              ? 'Enter your email and we’ll send a 6-digit reset code.'
              : 'Enter the code from your email and choose a new password.'}
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

        {step === 'request' ? (
          <form onSubmit={requestCode} className="space-y-4">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className={inputClass}
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Sending…' : 'Send reset code'}
            </button>
          </form>
        ) : (
          <form onSubmit={submitReset} className="space-y-4">
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="6-digit code"
              className={`${inputClass} text-center tracking-[0.4em]`}
            />
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="New password"
              className={inputClass}
            />
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Confirm new password"
              className={inputClass}
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Resetting…' : 'Reset password'}
            </button>
            <button
              type="button"
              onClick={requestCode}
              disabled={loading}
              className="w-full text-center text-sm font-semibold text-blue-600 hover:underline disabled:opacity-50 dark:text-blue-400"
            >
              Resend code
            </button>
          </form>
        )}

        <p className="mt-6 text-center text-sm">
          <Link to="/auth" className="text-slate-500 hover:underline dark:text-slate-400">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
};

export default ForgotPassword;
