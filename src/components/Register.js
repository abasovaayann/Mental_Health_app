import React, { useState } from 'react';
import { authService } from '../api/authService';

const validatePassword = (password) => {
  if (password.length < 8) {
    return 'Password must be at least 8 characters long';
  }
  if (!/[A-Z]/.test(password)) {
    return 'Password must include at least one uppercase letter';
  }
  if (!/[a-z]/.test(password)) {
    return 'Password must include at least one lowercase letter';
  }
  if (!/\d/.test(password)) {
    return 'Password must include at least one number';
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    return 'Password must include at least one special character';
  }
  return null;
};

const getApiErrorMessage = (err, fallback) => {
  const detail = err?.response?.data?.detail;
  const message = err?.response?.data?.message;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    if (first?.msg) {
      return first.msg;
    }
  }

  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  return fallback;
};

const Register = ({ onSuccess, onSwitchToLogin }) => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    age: '',
    gender: '',
    degree: '',
    university: '',
    city: '',
    country: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
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

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    // Validate password strength to match backend policy
    const passwordError = validatePassword(formData.password);
    if (passwordError) {
      setError(passwordError);
      setLoading(false);
      return;
    }

    try {
      const { confirmPassword, ...registrationData } = formData;
      await authService.register(registrationData);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Registration failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex flex-col gap-1 pt-4">
        <h3 className="text-text-heading dark:text-white tracking-tight text-3xl font-bold leading-tight text-left">
          Create Account
        </h3>
        <p className="text-text-muted dark:text-gray-400 text-sm">
          Get started with your mental health journey.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-xl text-sm">
          {error}
        </div>
      )}

      <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
        <div className="flex gap-4">
          <label className="flex flex-col gap-2 flex-1">
            <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
              First Name
            </p>
            <input
              className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] text-base font-normal leading-normal transition-all shadow-sm"
              placeholder="John"
              type="text"
              name="firstName"
              value={formData.firstName}
              onChange={handleChange}
              required
            />
          </label>

          <label className="flex flex-col gap-2 flex-1">
            <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
              Last Name
            </p>
            <input
              className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] text-base font-normal leading-normal transition-all shadow-sm"
              placeholder="Doe"
              type="text"
              name="lastName"
              value={formData.lastName}
              onChange={handleChange}
              required
            />
          </label>
        </div>

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
          <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
            Password
          </p>
          <div className="relative">
            <input
              className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] pr-12 text-base font-normal leading-normal transition-all shadow-sm"
              placeholder="••••••••"
              type={showPassword ? 'text' : 'password'}
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              minLength="8"
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

        <label className="flex flex-col gap-2">
          <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
            Confirm Password
          </p>
          <div className="relative">
            <input
              className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] pr-12 text-base font-normal leading-normal transition-all shadow-sm"
              placeholder="••••••••"
              type={showConfirmPassword ? 'text' : 'password'}
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              minLength="8"
            />
            <button
              className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-primary transition-colors cursor-pointer flex items-center"
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            >
              <span className="material-symbols-outlined text-xl">
                {showConfirmPassword ? 'visibility' : 'visibility_off'}
              </span>
            </button>
          </div>
        </label>

        {/* Demographic Information Section */}
        <div className="pt-4 border-t border-border-medium dark:border-gray-700">
          <p className="text-text-heading dark:text-white text-sm font-semibold mb-4">
            Additional Information (Optional)
          </p>

          <div className="flex gap-4 mb-5">
            <label className="flex flex-col gap-2 flex-1">
              <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
                Age
              </p>
              <input
                className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] text-base font-normal leading-normal transition-all shadow-sm"
                placeholder="25"
                type="number"
                name="age"
                min="16"
                max="100"
                value={formData.age}
                onChange={handleChange}
              />
            </label>

            <label className="flex flex-col gap-2 flex-1">
              <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
                Gender
              </p>
              <select
                className="form-select flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 px-[15px] text-base font-normal leading-normal transition-all shadow-sm"
                name="gender"
                value={formData.gender}
                onChange={handleChange}
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Non-binary">Non-binary</option>
                <option value="Prefer not to say">Prefer not to say</option>
              </select>
            </label>
          </div>

          <div className="flex gap-4 mb-5">
            <label className="flex flex-col gap-2 flex-1">
              <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
                Degree Program
              </p>
              <input
                className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] text-base font-normal leading-normal transition-all shadow-sm"
                placeholder="Computer Science"
                type="text"
                name="degree"
                value={formData.degree}
                onChange={handleChange}
              />
            </label>

            <label className="flex flex-col gap-2 flex-1">
              <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
                University
              </p>
              <input
                className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] text-base font-normal leading-normal transition-all shadow-sm"
                placeholder="University name"
                type="text"
                name="university"
                value={formData.university}
                onChange={handleChange}
              />
            </label>
          </div>

          <div className="flex gap-4">
            <label className="flex flex-col gap-2 flex-1">
              <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
                City
              </p>
              <input
                className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] text-base font-normal leading-normal transition-all shadow-sm"
                placeholder="New York"
                type="text"
                name="city"
                value={formData.city}
                onChange={handleChange}
              />
            </label>

            <label className="flex flex-col gap-2 flex-1">
              <p className="text-text-heading dark:text-white text-sm font-semibold leading-normal">
                Country
              </p>
              <input
                className="form-input flex w-full min-w-0 resize-none overflow-hidden rounded-xl text-text-body dark:text-white focus:outline-0 focus:ring-4 focus:ring-primary/20 border border-border-medium dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-primary h-14 placeholder:text-slate-400 dark:placeholder:text-gray-500 p-[15px] text-base font-normal leading-normal transition-all shadow-sm"
                placeholder="United States"
                type="text"
                name="country"
                value={formData.country}
                onChange={handleChange}
              />
            </label>
          </div>
        </div>

        <button
          className="flex w-full cursor-pointer items-center justify-center overflow-hidden rounded-xl h-12 px-5 bg-primary hover:bg-primary-dark text-white text-base font-bold leading-normal tracking-[0.015em] shadow-lg shadow-primary/25 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          type="submit"
          disabled={loading}
        >
          <span className="truncate">{loading ? 'Creating Account...' : 'Create Account'}</span>
        </button>

        <p className="text-center text-sm text-text-muted dark:text-gray-400">
          Already have an account?{' '}
          <button
            type="button"
            className="font-semibold text-primary hover:text-primary-dark hover:underline"
            onClick={onSwitchToLogin}
          >
            Login
          </button>
        </p>
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

export default Register;
