import {
  formatDateInput,
  formatMonthLabel,
  formatDateShort,
  formatDuration,
  formatReadableDate,
  getCalendarGrid,
  isFutureDate,
  mapApiEntryToUi,
  composeVoiceNoteContent,
} from './diaryHelpers';

describe('formatDateInput', () => {
  it('formats a Date as zero-padded YYYY-MM-DD', () => {
    // Arrange
    const date = new Date(2026, 5, 9); // 9 June 2026 (month is 0-indexed)

    // Act
    const result = formatDateInput(date);

    // Assert
    expect(result).toBe('2026-06-09');
  });

  it('keeps two-digit months and days correct', () => {
    expect(formatDateInput(new Date(2026, 10, 25))).toBe('2026-11-25');
  });
});

describe('formatMonthLabel', () => {
  it('renders the full month name and year', () => {
    expect(formatMonthLabel('2026-06-14')).toBe('June 2026');
  });
});

describe('formatDateShort', () => {
  it('renders abbreviated month and numeric day', () => {
    expect(formatDateShort('2026-06-14')).toBe('Jun 14');
  });
});

describe('formatDuration', () => {
  it('formats seconds under a minute as 00:ss', () => {
    expect(formatDuration(5)).toBe('00:05');
  });

  it('formats whole minutes and remaining seconds', () => {
    expect(formatDuration(125)).toBe('02:05');
  });

  it('formats zero as 00:00', () => {
    expect(formatDuration(0)).toBe('00:00');
  });
});

describe('formatReadableDate', () => {
  it('returns a long human-readable date for a valid value', () => {
    expect(formatReadableDate('2026-06-14')).toBe('June 14, 2026');
  });

  it('falls back to "Today" for an invalid date', () => {
    expect(formatReadableDate('not-a-date')).toBe('Today');
  });
});

describe('getCalendarGrid', () => {
  it('always returns a 42-cell (6-week) grid', () => {
    expect(getCalendarGrid(2026, 5)).toHaveLength(42);
  });

  it('marks exactly the days of the target month as currentMonth', () => {
    // Arrange: June 2026 has 30 days.
    // Act
    const grid = getCalendarGrid(2026, 5);
    const currentMonthDays = grid.filter((cell) => cell.currentMonth);

    // Assert
    expect(currentMonthDays).toHaveLength(30);
  });

  it('places leading days from the previous month before day 1', () => {
    // May 2026 starts on a Friday → 4 leading (Mon–Thu) cells.
    const grid = getCalendarGrid(2026, 4);
    const leading = grid.slice(0, 4);

    expect(leading.every((cell) => cell.currentMonth === false)).toBe(true);
    expect(grid[4]).toEqual({ day: 1, currentMonth: true });
  });
});

describe('isFutureDate', () => {
  it('returns true when the date is after today', () => {
    expect(isFutureDate('2026-06-15', '2026-06-14')).toBe(true);
  });

  it('returns false for today or past dates', () => {
    expect(isFutureDate('2026-06-14', '2026-06-14')).toBe(false);
    expect(isFutureDate('2026-06-13', '2026-06-14')).toBe(false);
  });
});

describe('mapApiEntryToUi', () => {
  const baseEntry = {
    id: 7,
    entry_date: '2026-06-14',
    created_at: '2026-06-14T09:05:00Z',
    title: 'Morning thoughts',
    content: 'A short reflection.',
    mood: 'positive',
    tags: ['focus', 'calm'],
  };

  it('maps API fields to the UI shape and stringifies the id', () => {
    const result = mapApiEntryToUi(baseEntry);

    expect(result.id).toBe('7');
    expect(result.date).toBe('2026-06-14');
    expect(result.title).toBe('Morning thoughts');
    expect(result.content).toBe('A short reflection.');
    expect(result.mood).toBe('positive');
    expect(result.tags).toEqual(['focus', 'calm']);
  });

  it('returns the full content as preview when under 120 chars', () => {
    const result = mapApiEntryToUi(baseEntry);
    expect(result.preview).toBe('A short reflection.');
  });

  it('truncates the preview with an ellipsis when content exceeds 120 chars', () => {
    const longContent = 'x'.repeat(200);
    const result = mapApiEntryToUi({ ...baseEntry, content: longContent });

    expect(result.preview).toBe(`${'x'.repeat(120)}...`);
  });

  it('defaults tags to an empty array when not an array', () => {
    const result = mapApiEntryToUi({ ...baseEntry, tags: undefined });
    expect(result.tags).toEqual([]);
  });
});

describe('composeVoiceNoteContent', () => {
  it('returns the trimmed base content when there is no voice text', () => {
    expect(composeVoiceNoteContent('Hello there  ', '')).toBe('Hello there');
  });

  it('appends the voice note beneath existing content', () => {
    expect(composeVoiceNoteContent('My day', 'felt calm')).toBe(
      'My day\n\nVoice note: felt calm'
    );
  });

  it('prefixes a voice-only note when base content is empty', () => {
    expect(composeVoiceNoteContent('', 'felt calm')).toBe('Voice note: felt calm');
  });

  it('treats whitespace-only voice text as empty', () => {
    expect(composeVoiceNoteContent('Base', '   ')).toBe('Base');
  });
});
