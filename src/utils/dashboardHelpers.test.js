import {
  mapApiCheckinToUi,
  getDateKey,
  getLastSevenDates,
  getCheckinAverage,
  areCheckinsEqual,
  getRiskStyles,
  formatDate,
} from './dashboardHelpers';

describe('mapApiCheckinToUi', () => {
  it('maps snake_case API fields to numeric camelCase UI fields', () => {
    const result = mapApiCheckinToUi({ mood_level: '80', sleep_quality: '60', energy_level: '40' });

    expect(result).toEqual({ moodLevel: 80, sleepQuality: 60, energyLevel: 40 });
  });
});

describe('getDateKey', () => {
  it('formats a Date as zero-padded YYYY-MM-DD', () => {
    expect(getDateKey(new Date(2026, 0, 5))).toBe('2026-01-05');
  });
});

describe('getLastSevenDates', () => {
  it('returns seven consecutive dates ending today', () => {
    // Act
    const dates = getLastSevenDates();

    // Assert
    expect(dates).toHaveLength(7);
    expect(getDateKey(dates[6])).toBe(getDateKey(new Date()));

    const dayMs = 24 * 60 * 60 * 1000;
    const spanDays = Math.round((dates[6] - dates[0]) / dayMs);
    expect(spanDays).toBe(6);
  });
});

describe('getCheckinAverage', () => {
  it('returns null for a missing entry', () => {
    expect(getCheckinAverage(null)).toBeNull();
  });

  it('rounds the mean of the three levels', () => {
    expect(getCheckinAverage({ moodLevel: 80, sleepQuality: 60, energyLevel: 40 })).toBe(60);
    expect(getCheckinAverage({ moodLevel: 70, sleepQuality: 70, energyLevel: 71 })).toBe(70);
  });

  it('ignores non-finite values', () => {
    expect(getCheckinAverage({ moodLevel: 90, sleepQuality: 'n/a', energyLevel: 30 })).toBe(60);
  });

  it('returns null when no value is finite', () => {
    expect(getCheckinAverage({ moodLevel: 'a', sleepQuality: 'b', energyLevel: 'c' })).toBeNull();
  });
});

describe('areCheckinsEqual', () => {
  const checkin = { moodLevel: 50, sleepQuality: 60, energyLevel: 70 };

  it('returns false when either side is missing', () => {
    expect(areCheckinsEqual(null, checkin)).toBe(false);
    expect(areCheckinsEqual(checkin, null)).toBe(false);
  });

  it('returns true when all tracked fields match (numeric-coerced)', () => {
    expect(areCheckinsEqual(checkin, { moodLevel: '50', sleepQuality: '60', energyLevel: '70' })).toBe(true);
  });

  it('returns false when any tracked field differs', () => {
    expect(areCheckinsEqual(checkin, { ...checkin, energyLevel: 71 })).toBe(false);
  });
});

describe('getRiskStyles', () => {
  it('returns distinct style sets for low / medium / high risk', () => {
    expect(getRiskStyles(0).progress).toBe('bg-emerald-500');
    expect(getRiskStyles(1).progress).toBe('bg-amber-500');
    expect(getRiskStyles(2).progress).toBe('bg-rose-500');
  });

  it('falls back to the high-risk styles for unknown levels', () => {
    expect(getRiskStyles(99).progress).toBe('bg-rose-500');
  });
});

describe('formatDate', () => {
  it('returns a placeholder for an empty value', () => {
    expect(formatDate(null)).toBe('No recent activity yet');
    expect(formatDate('')).toBe('No recent activity yet');
  });

  it('formats a timestamp with month, day, and time', () => {
    const formatted = formatDate('2026-06-14T09:05:00');
    expect(formatted).toMatch(/Jun/);
    expect(formatted).toMatch(/14/);
  });
});
