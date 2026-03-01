import React, { useState } from 'react';
import { authService } from '../api/authService';

const Login = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError(''); // Clear error when user types
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await authService.login(formData.email, formData.password);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex flex-col gap-1 pt-4">
        <h3 className="text-text-heading dark:text-white tracking-tight text-3xl font-bold leading-tight text-left">
          Welcome Back
        </h3>
        <p className="text-text-muted dark:text-gray-400 text-sm">
          Please enter your details to sign in.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-xl text-sm">
          {error}
        </div>
      )}

      <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-2">
          <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
            University Email
          </p>
          <div className="relative">
            <input
              className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] pr-12 text-base font-normal leading-normal transition-all shadow-sm"
              placeholder="student@university.edu"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
            />
            <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              <span className="material-symbols-outlined text-xl">mail</span>
            </div>
          </div>
        </label>

        <label className="flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
              Password
            </p>
          </div>
          <div className="relative">
            <input
              className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] pr-12 text-base font-normal leading-normal transition-all shadow-sm"
              placeholder="••••••••"
              type={showPassword ? 'text' : 'password'}
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
            />
            <button
              className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-primary transition-colors cursor-pointer flex items-center"
              type="button"
              onClick={() => setShowPassword(!showPassword)}
            >
              <span className="material-symbols-outlined text-xl">
                {showPassword ? 'visibility' : 'visibility_off'}
              </span>
            </button>
          </div>
        </label>

        <div className="flex justify-end">
          <a
            className="text-sm font-semibold text-primary hover:text-primary-dark hover:underline"
            href="#"
          >
            Forgot Password?
          </a>
        </div>

        <button
          className="flex w-full cursor-pointer items-center justify-center overflow-hidden rounded-xl h-12 px-5 bg-primary hover:bg-primary-dark text-white text-base font-bold leading-normal tracking-[0.015em] shadow-lg shadow-primary/25 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          type="submit"
          disabled={loading}
        >
          <span className="truncate">{loading ? 'Signing In...' : 'Sign In'}</span>
        </button>
      </form>

      <p className="text-center text-xs text-text-muted dark:text-gray-400 mt-4">
        By continuing, you agree to MindTrackAi's{' '}
        <a className="font-medium text-primary hover:underline" href="#">
          Terms of Service
        </a>{' '}
        and{' '}
        <a className="font-medium text-primary hover:underline" href="#">
          Privacy Policy
        </a>
        .
      </p>

      <div className="flex items-center justify-center gap-2 mt-2 bg-blue-100 dark:bg-blue-900/40 py-2 rounded-lg">
        <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-sm">
          lock
        </span>
        <span className="text-xs font-medium text-blue-700 dark:text-blue-300">
          100% Private &amp; Secure
        </span>
      </div>
    </>
  );
};

export default Login;
