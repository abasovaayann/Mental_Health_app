import React, { useEffect, useMemo, useState } from 'react';

const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const toISODate = (d) => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

const sameYMD = (a, b) =>
  a && b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

const CalendarFilterModal = ({ open, onClose, onSelect, onClear, selectedDate, entryDates = [] }) => {
  const [viewMonth, setViewMonth] = useState(() => {
    const base = selectedDate ? new Date(`${selectedDate}T00:00:00`) : new Date();
    return new Date(base.getFullYear(), base.getMonth(), 1);
  });

  useEffect(() => {
    if (!open) return;
    const base = selectedDate ? new Date(`${selectedDate}T00:00:00`) : new Date();
    setViewMonth(new Date(base.getFullYear(), base.getMonth(), 1));
  }, [open, selectedDate]);

  const today = new Date();

  const datesWithEntries = useMemo(() => new Set(entryDates), [entryDates]);

  const monthLabel = viewMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const cells = useMemo(() => {
    const first = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1);
    const last = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 0);
    const startPadding = first.getDay();
    const total = startPadding + last.getDate();
    const rows = Math.ceil(total / 7);
    const out = [];
    for (let i = 0; i < rows * 7; i += 1) {
      const dayNum = i - startPadding + 1;
      if (dayNum < 1 || dayNum > last.getDate()) {
        out.push({ blank: true, key: `b-${i}` });
      } else {
        const date = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), dayNum);
        const iso = toISODate(date);
        out.push({
          date,
          iso,
          dayNum,
          hasEntries: datesWithEntries.has(iso),
          isToday: sameYMD(date, today),
          isSelected: selectedDate === iso,
          key: iso,
        });
      }
    }
    return out;
    // today object reference is stable enough for a single render — not adding to deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMonth, datesWithEntries, selectedDate]);

  const navigateMonth = (delta) => {
    setViewMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  };

  const jumpToToday = () => {
    const now = new Date();
    setViewMonth(new Date(now.getFullYear(), now.getMonth(), 1));
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <button
        type="button"
        aria-label="Close calendar"
        onClick={onClose}
        className="fixed inset-0 cursor-default"
      />
      <div className="relative z-10 w-full max-w-sm overflow-hidden rounded-2xl border border-slate-200/40 bg-white shadow-2xl dark:border-slate-700/40 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-700">
          <button
            type="button"
            onClick={() => navigateMonth(-1)}
            className="flex h-8 w-8 items-center justify-center rounded-xl text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            title="Previous month"
          >
            <span className="material-symbols-outlined text-base">chevron_left</span>
          </button>
          <button
            type="button"
            onClick={jumpToToday}
            className="font-display text-base font-bold text-slate-800 hover:text-blue-600 dark:text-slate-100 dark:hover:text-blue-300"
            title="Jump to today"
          >
            {monthLabel}
          </button>
          <button
            type="button"
            onClick={() => navigateMonth(1)}
            className="flex h-8 w-8 items-center justify-center rounded-xl text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            title="Next month"
          >
            <span className="material-symbols-outlined text-base">chevron_right</span>
          </button>
        </div>

        <div className="p-5">
          <div className="mb-2 grid grid-cols-7 gap-1">
            {WEEKDAY_LABELS.map((w) => (
              <div key={w} className="text-center text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {w}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {cells.map((cell) => {
              if (cell.blank) return <div key={cell.key} className="h-10" />;

              let cls = 'relative mx-auto flex h-10 w-10 items-center justify-center rounded-xl text-sm transition-all';
              if (cell.isSelected) {
                cls += ' bg-blue-600 font-bold text-white shadow-md';
              } else {
                cls += ' text-slate-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-900/30';
                if (cell.hasEntries) cls += ' font-semibold text-blue-700 dark:text-blue-300';
                if (cell.isToday) cls += ' ring-1 ring-orange-400/70';
              }

              return (
                <button
                  key={cell.key}
                  type="button"
                  onClick={() => onSelect?.(cell.iso)}
                  className={cls}
                >
                  {cell.dayNum}
                  {cell.hasEntries && !cell.isSelected && (
                    <span className="absolute bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-blue-500" />
                  )}
                </button>
              );
            })}
          </div>

          <div className="mt-5 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
              <span>Has entries</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded ring-1 ring-orange-400/70" />
              <span>Today</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/50 px-5 py-3 dark:border-slate-700 dark:bg-slate-800/30">
          <button
            type="button"
            onClick={onClear}
            disabled={!selectedDate}
            className="text-xs font-semibold text-blue-600 hover:underline disabled:cursor-not-allowed disabled:text-slate-400 disabled:no-underline dark:text-blue-300 dark:disabled:text-slate-500"
          >
            Clear date filter
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default CalendarFilterModal;
