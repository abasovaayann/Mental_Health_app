import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const NAV_ITEMS = [
  { key: 'home', label: 'Home', icon: 'home', path: '/dashboard' },
  { key: 'diary', label: 'Diary', icon: 'book_2', path: '/diary' },
  { key: 'insights', label: 'Insights', icon: 'insights', path: '/insights' },
  { key: 'settings', label: 'Settings', icon: 'settings', path: '/settings' },
];

const isItemActive = (item, pathname) => {
  if (!item.path) return false;
  if (item.path === '/dashboard') return pathname === '/' || pathname.startsWith('/dashboard');
  return pathname.startsWith(item.path);
};

const Sidebar = ({ user, open, onClose, footerSlot, children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col justify-between overflow-y-auto bg-blue-900 px-6 py-6 text-white shadow-2xl transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col gap-8">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-3xl">self_improvement</span>
            <span className="font-display text-xl font-bold tracking-wide">MindTrackAi</span>
          </div>

          <nav className="flex flex-col gap-2">
            {NAV_ITEMS.map((item) => {
              const active = isItemActive(item, location.pathname);
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => {
                    navigate(item.path);
                    onClose?.();
                  }}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 text-left font-medium transition-all ${
                    active ? 'bg-blue-500/30 text-white' : 'text-blue-100 hover:bg-white/10'
                  }`}
                >
                  <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                  <span className="text-sm font-medium">{item.label}</span>
                </button>
              );
            })}
          </nav>

          {children}
        </div>

        <div className="border-t border-blue-800/60 pt-6">
          {footerSlot ?? (
            user && (
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
                  <p className="truncate text-sm font-semibold">
                    {user.firstName} {user.lastName}
                  </p>
                  <p className="truncate text-xs text-blue-200">View Profile</p>
                </div>
              </button>
            )
          )}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
