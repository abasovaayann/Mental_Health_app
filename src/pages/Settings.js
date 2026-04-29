import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import Sidebar from '../components/Sidebar';
import ReminderSettings from '../components/ReminderSettings';
import { getStoredTheme, setTheme } from '../theme';

const SETTINGS_SECTIONS = [
  { key: 'profile', label: 'Account & Profile', icon: 'person' },
  { key: 'reminders', label: 'Email Reminders', icon: 'mail_outline' },
  { key: 'appearance', label: 'Appearance', icon: 'palette' },
  { key: 'privacy', label: 'Privacy & Security', icon: 'shield' },
];

/* ─── Section wrapper ─── */
const Section = ({ id, icon, title, desc, children }) => (
  <section id={id} className="rounded-2xl border border-slate-100 bg-surface-light p-6 shadow-sm transition-colors dark:border-border-dark dark:bg-surface-dark md:p-8">
    <div className="mb-6 flex items-start gap-3">
      <div className="rounded-xl bg-blue-50 p-3 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
        <span className="material-symbols-outlined text-2xl">{icon}</span>
      </div>
      <div>
        <h3 className="font-display text-xl font-bold text-slate-800 dark:text-slate-100">{title}</h3>
        {desc && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{desc}</p>}
      </div>
    </div>
    <div className="space-y-5">{children}</div>
  </section>
);

/* ─── Row inside section ─── */
const Row = ({ label, desc, children }) => (
  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
    <div className="min-w-0">
      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{label}</p>
      {desc && <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{desc}</p>}
    </div>
    <div className="shrink-0">{children}</div>
  </div>
);

/* ─── Confirm Modal ─── */
const ConfirmModal = ({ open, title, message, danger, confirmText, onConfirm, onCancel }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-surface-light dark:bg-surface-dark rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4 animate-fade-in-down">
        <h3 className="text-lg font-bold text-text-primary-light dark:text-text-primary-dark">{title}</h3>
        <p className="text-sm text-text-secondary-light dark:text-text-secondary-dark mt-2">{message}</p>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg text-sm font-semibold text-text-secondary-light dark:text-text-secondary-dark hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors">Cancel</button>
          <button onClick={onConfirm} className={`px-4 py-2 rounded-lg text-sm font-bold text-white transition-colors ${danger ? 'bg-red-500 hover:bg-red-600' : 'bg-primary hover:bg-primary-hover'}`}>{confirmText || 'Confirm'}</button>
        </div>
      </div>
    </div>
  );
};

/* ═════════════════════════════════════════════
   MAIN  SETTINGS  COMPONENT
   ═════════════════════════════════════════════ */
const Settings = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [activeSection, setActiveSection] = useState('profile');
  const [toast, setToast] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  /* ── Profile state ── */
  const [profileForm, setProfileForm] = useState({ first_name: '', last_name: '', age: '', gender: '', degree: '', university: '', city: '', country: '' });
  const [profileSaving, setProfileSaving] = useState(false);
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [prefsLoaded, setPrefsLoaded] = useState(false);

  /* ── Privacy / delete-account ── */
  const [deleteModal, setDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);

  /* ── Appearance ── */
  const [theme, setThemeState] = useState(() => getStoredTheme());

  /* ── Init ── */
  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) { navigate('/auth'); return; }
    const u = JSON.parse(userData);
    setUser(u);

    const loadAll = async () => {
      try {
        const meRes = await api.get('/auth/me');
        const d = meRes.data;
        setProfileForm({
          first_name: d.first_name || '', last_name: d.last_name || '',
          age: d.age ?? '', gender: d.gender || '', degree: d.degree || '',
          university: d.university || '', city: d.city || '', country: d.country || '',
        });
      } catch {
        setProfileForm(f => ({ ...f, first_name: u.firstName || '', last_name: u.lastName || '' }));
      } finally {
        setPrefsLoaded(true);
      }
    };

    loadAll();
  }, [navigate]);

  // Sync theme to backend in the background — localStorage is the source of truth
  useEffect(() => {
    if (!prefsLoaded) return;
    const timeout = setTimeout(async () => {
      try {
        await api.put('/auth/preferences', { appearance: { theme } });
      } catch {
        // Theme stays applied locally even if the server save fails.
      }
    }, 450);
    return () => clearTimeout(timeout);
  }, [prefsLoaded, theme]);

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  /* ── Handlers ── */
  const handleProfileSave = async () => {
    setProfileSaving(true);
    try {
      const payload = { ...profileForm, age: profileForm.age ? Number(profileForm.age) : null };
      const res = await api.put('/auth/profile', payload);
      const u = res.data.user;
      const stored = JSON.parse(localStorage.getItem('user') || '{}');
      localStorage.setItem('user', JSON.stringify({ ...stored, firstName: u.firstName, lastName: u.lastName }));
      showToast('Profile updated');
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to update profile', 'error');
    } finally { setProfileSaving(false); }
  };

  const handlePasswordChange = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) { showToast('Passwords do not match', 'error'); return; }
    if (passwordForm.new_password.length < 6) { showToast('Password must be at least 6 characters', 'error'); return; }
    setPasswordSaving(true);
    try {
      await api.put('/auth/change-password', { current_password: passwordForm.current_password, new_password: passwordForm.new_password });
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      showToast('Password changed');
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to change password', 'error');
    } finally { setPasswordSaving(false); }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await api.delete('/auth/account');
      localStorage.clear();
      navigate('/auth');
    } catch (e) {
      showToast('Failed to delete account', 'error');
      setDeleting(false);
      setDeleteModal(false);
    }
  };

  const handleExportData = async () => {
    setExporting(true);
    try {
      const res = await api.get('/auth/export-data');
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'mindtrackai_data_export.json'; a.click();
      URL.revokeObjectURL(url);
      showToast('Data exported');
    } catch { showToast('Export failed', 'error'); }
    finally { setExporting(false); }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    navigate('/auth');
  };

  const scrollToSection = (key) => {
    setActiveSection(key);
    document.getElementById(`section-${key}`)?.scrollIntoView({ behavior: 'smooth' });
    setSidebarOpen(false);
  };

  if (!user) return null;

  return (
    <div className="h-screen overflow-hidden bg-background-light dark:bg-background-dark text-text-primary-light dark:text-text-primary-dark lg:flex">
      {/* ── Toast ── */}
      {toast && (
        <div className={`fixed top-4 right-4 z-[100] flex items-center gap-2 rounded-xl px-4 py-3 shadow-lg text-sm font-semibold animate-fade-in-down ${toast.type === 'error' ? 'bg-red-500 text-white' : 'bg-green-500 text-white'}`}>
          <span className="material-symbols-outlined text-[18px]">{toast.type === 'error' ? 'error' : 'check_circle'}</span>
          {toast.msg}
        </div>
      )}

      <div className="relative flex min-h-0 flex-1 lg:flex">
        <Sidebar user={user} open={sidebarOpen} onClose={() => setSidebarOpen(false)}>
          <div>
            <p className="mb-2 px-3 text-[11px] font-bold uppercase tracking-widest text-blue-200">Settings</p>
            <div className="flex flex-col gap-1">
              {SETTINGS_SECTIONS.map(s => (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => scrollToSection(s.key)}
                  className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left font-medium transition-all ${activeSection === s.key ? 'bg-blue-500/30 text-white' : 'text-blue-100 hover:bg-white/10'}`}
                >
                  <span className="material-symbols-outlined text-[20px]">{s.icon}</span>
                  <span className="text-sm font-medium">{s.label}</span>
                </button>
              ))}
            </div>
          </div>
        </Sidebar>

        {/* ── Content ── */}
        <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
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
                <h1 className="font-display text-3xl font-bold text-text-heading md:text-4xl">Settings</h1>
                <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">
                  Manage your account, preferences, and privacy.
                </p>
              </div>
            </div>
          </header>

          {/* ═══════════════════════════════════════
             1. ACCOUNT & PROFILE
             ═══════════════════════════════════════ */}
          <Section id="section-profile" icon="person" title="Account & Profile" desc="Update your personal information and credentials.">
            {/* Avatar + name */}
            <div className="flex items-center gap-4 pb-4 border-b border-blue-50 dark:border-border-dark">
              <div className="h-16 w-16 rounded-full bg-gradient-to-br from-blue-400 to-primary flex items-center justify-center text-white font-bold text-xl shadow-lg">
                {profileForm.first_name?.[0]?.toUpperCase()}{profileForm.last_name?.[0]?.toUpperCase()}
              </div>
              <div>
                <p className="font-bold text-text-primary-light dark:text-text-primary-dark">{profileForm.first_name} {profileForm.last_name}</p>
                <p className="text-xs text-text-secondary-light dark:text-text-secondary-dark">{user.email}</p>
              </div>
            </div>

            {/* Edit fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { key: 'first_name', label: 'First Name', icon: 'badge' },
                { key: 'last_name', label: 'Last Name', icon: 'badge' },
                { key: 'age', label: 'Age', icon: 'cake', type: 'number' },
                { key: 'gender', label: 'Gender', icon: 'wc', select: ['', 'Male', 'Female', 'Non-binary', 'Prefer not to say'] },
                { key: 'degree', label: 'Degree', icon: 'school' },
                { key: 'university', label: 'University', icon: 'account_balance' },
                { key: 'city', label: 'City', icon: 'location_city' },
                { key: 'country', label: 'Country', icon: 'public' },
              ].map(f => (
                <div key={f.key}>
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary-light dark:text-text-secondary-dark mb-1">
                    <span className="material-symbols-outlined text-[14px]">{f.icon}</span>{f.label}
                  </label>
                  {f.select ? (
                    <select value={profileForm[f.key]} onChange={e => setProfileForm(p => ({ ...p, [f.key]: e.target.value }))}
                      className="w-full rounded-lg border border-blue-200 dark:border-border-dark bg-white dark:bg-slate-800 text-sm px-3 py-2 text-text-primary-light dark:text-text-primary-dark focus:ring-2 focus:ring-primary focus:border-primary transition-colors">
                      {f.select.map(o => <option key={o} value={o}>{o || '— Select —'}</option>)}
                    </select>
                  ) : (
                    <input type={f.type || 'text'} value={profileForm[f.key]} onChange={e => setProfileForm(p => ({ ...p, [f.key]: e.target.value }))}
                      className="w-full rounded-lg border border-blue-200 dark:border-border-dark bg-white dark:bg-slate-800 text-sm px-3 py-2 text-text-primary-light dark:text-text-primary-dark focus:ring-2 focus:ring-primary focus:border-primary transition-colors" />
                  )}
                </div>
              ))}
            </div>

            <button onClick={handleProfileSave} disabled={profileSaving}
              className="mt-2 flex items-center gap-2 rounded-xl px-5 py-2.5 bg-primary hover:bg-primary-hover text-white text-sm font-bold transition-colors disabled:opacity-50">
              <span className="material-symbols-outlined text-[18px]">{profileSaving ? 'hourglass_top' : 'save'}</span>
              {profileSaving ? 'Saving…' : 'Save Profile'}
            </button>

            {/* Change password */}
            <div className="pt-5 border-t border-blue-50 dark:border-border-dark">
              <h4 className="text-sm font-bold text-text-primary-light dark:text-text-primary-dark mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">lock</span>Change Password
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input type="password" placeholder="Current password" value={passwordForm.current_password} onChange={e => setPasswordForm(p => ({ ...p, current_password: e.target.value }))}
                  className="rounded-lg border border-blue-200 dark:border-border-dark bg-white dark:bg-slate-800 text-sm px-3 py-2 text-text-primary-light dark:text-text-primary-dark focus:ring-2 focus:ring-primary transition-colors" />
                <input type="password" placeholder="New password" value={passwordForm.new_password} onChange={e => setPasswordForm(p => ({ ...p, new_password: e.target.value }))}
                  className="rounded-lg border border-blue-200 dark:border-border-dark bg-white dark:bg-slate-800 text-sm px-3 py-2 text-text-primary-light dark:text-text-primary-dark focus:ring-2 focus:ring-primary transition-colors" />
                <input type="password" placeholder="Confirm new password" value={passwordForm.confirm_password} onChange={e => setPasswordForm(p => ({ ...p, confirm_password: e.target.value }))}
                  className="rounded-lg border border-blue-200 dark:border-border-dark bg-white dark:bg-slate-800 text-sm px-3 py-2 text-text-primary-light dark:text-text-primary-dark focus:ring-2 focus:ring-primary transition-colors" />
              </div>
              <button onClick={handlePasswordChange} disabled={passwordSaving || !passwordForm.current_password || !passwordForm.new_password}
                className="mt-3 flex items-center gap-2 rounded-xl px-4 py-2 bg-blue-50 dark:bg-blue-900/30 text-primary dark:text-blue-400 text-sm font-bold hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-40">
                <span className="material-symbols-outlined text-[16px]">key</span>
                {passwordSaving ? 'Updating…' : 'Update Password'}
              </button>
            </div>
          </Section>

          {/* ═══════════════════════════════════════
             2. EMAIL REMINDERS
             ═══════════════════════════════════════ */}
          <Section id="section-reminders" icon="mail_outline" title="Email Reminders" desc="Set up daily check-in reminders via email.">
            <ReminderSettings onToast={showToast} />
          </Section>

          {/* ═══════════════════════════════════════
             3. APPEARANCE
             ═══════════════════════════════════════ */}
          <Section id="section-appearance" icon="palette" title="Appearance" desc="Customise how MindTrackAi looks.">
            <Row label="Theme">
              <div className="flex gap-2">
                {[
                  { value: 'light', icon: 'light_mode', label: 'Light' },
                  { value: 'dark', icon: 'dark_mode', label: 'Dark' },
                  { value: 'system', icon: 'computer', label: 'System' },
                ].map(t => (
                  <button
                    key={t.value}
                    onClick={() => {
                      setTheme(t.value);
                      setThemeState(t.value);
                    }}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-colors ${theme === t.value ? 'bg-primary text-white shadow' : 'bg-blue-50 dark:bg-slate-700 text-text-secondary-light dark:text-text-secondary-dark hover:bg-blue-100 dark:hover:bg-slate-600'}`}>
                    <span className="material-symbols-outlined text-[16px]">{t.icon}</span>{t.label}
                  </button>
                ))}
              </div>
            </Row>
          </Section>

          {/* ═══════════════════════════════════════
             4. PRIVACY & SECURITY
             ═══════════════════════════════════════ */}
          <Section id="section-privacy" icon="shield" title="Privacy & Security" desc="Control your data and protect your account.">
            <div className="flex flex-wrap gap-3">
              <button onClick={handleExportData} disabled={exporting}
                className="flex items-center gap-2 rounded-xl px-4 py-2 bg-blue-50 dark:bg-blue-900/30 text-primary dark:text-blue-400 text-sm font-bold hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50">
                <span className="material-symbols-outlined text-[18px]">download</span>
                {exporting ? 'Exporting…' : 'Export My Data'}
              </button>
              <button onClick={() => setDeleteModal(true)}
                className="flex items-center gap-2 rounded-xl px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm font-bold hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors">
                <span className="material-symbols-outlined text-[18px]">delete_forever</span>
                Delete Account
              </button>
            </div>
          </Section>

          <section className="rounded-2xl border border-red-100 bg-red-50/60 p-6 shadow-sm dark:border-red-900/40 dark:bg-red-900/10">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-base font-bold text-red-700 dark:text-red-300">Session</h3>
                <p className="mt-1 text-sm text-red-600 dark:text-red-300/90">
                  Log out from this account on this device.
                </p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-500 px-5 py-2.5 text-sm font-bold text-white transition-colors hover:bg-red-600"
              >
                <span className="material-symbols-outlined text-[18px]">logout</span>
                Logout
              </button>
            </div>
          </section>

          {/* Bottom spacer */}
          <div className="h-8" />
          </div>
        </main>
      </div>

      {/* ── Delete account modal ── */}
      <ConfirmModal
        open={deleteModal}
        title="Delete Account"
        message="This action is permanent. All your data, including surveys, diary entries, and wellness scores, will be permanently deleted. This cannot be undone."
        danger
        confirmText={deleting ? 'Deleting…' : 'Delete My Account'}
        onConfirm={handleDeleteAccount}
        onCancel={() => setDeleteModal(false)}
      />
    </div>
  );
};

export default Settings;
