import { formatTime, formatRelative, formatDuration } from './insightsHelpers';

describe('formatTime', () => {
  it('returns an empty string for empty or invalid input', () => {
    expect(formatTime('')).toBe('');
    expect(formatTime(undefined)).toBe('');
    expect(formatTime('not-a-date')).toBe('');
  });

  it('formats a local timestamp as h:mm with meridiem', () => {
    const result = formatTime('2026-06-14T09:05:00');
    expect(result).toMatch(/9:05/);
    expect(result).toMatch(/AM/i);
  });
});

describe('formatRelative', () => {
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  it('returns an empty string for empty or invalid input', () => {
    expect(formatRelative('')).toBe('');
    expect(formatRelative('nonsense')).toBe('');
  });

  it('returns "now" for timestamps under a minute old', () => {
    expect(formatRelative(new Date().toISOString())).toBe('now');
  });

  it('returns minutes-ago for recent timestamps', () => {
    expect(formatRelative(new Date(Date.now() - 5 * minute).toISOString())).toBe('5m ago');
  });

  it('returns hours-ago within the same day', () => {
    expect(formatRelative(new Date(Date.now() - 3 * hour).toISOString())).toBe('3h ago');
  });

  it('returns "Yesterday" one day back', () => {
    expect(formatRelative(new Date(Date.now() - 25 * hour).toISOString())).toBe('Yesterday');
  });

  it('returns a weekday name a few days back', () => {
    const result = formatRelative(new Date(Date.now() - 3 * day).toISOString());
    expect(result).toMatch(/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$/);
  });
});

describe('formatDuration', () => {
  it('zero-pads minutes and seconds', () => {
    expect(formatDuration(5)).toBe('00:05');
    expect(formatDuration(125)).toBe('02:05');
    expect(formatDuration(0)).toBe('00:00');
  });
});
