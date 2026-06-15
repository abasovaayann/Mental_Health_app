import { isStepValid, getSleepDurationLabel, buildSurveyPayload } from './baselineSurveyHelpers';
import { INITIAL_FORM_DATA } from '../constants/baselineSurvey';

describe('isStepValid', () => {
  it('requires the energy level on step 1', () => {
    expect(isStepValid(1, { ...INITIAL_FORM_DATA })).toBe(false);
    expect(isStepValid(1, { ...INITIAL_FORM_DATA, energyLevel: 'High' })).toBe(true);
  });

  it('requires all three academic fields on step 2', () => {
    const partial = { ...INITIAL_FORM_DATA, academicPressure: 'Often', studyMotivation: 'Motivated' };
    expect(isStepValid(2, partial)).toBe(false);

    const complete = { ...partial, concentrationDifficulty: 'Slightly difficult' };
    expect(isStepValid(2, complete)).toBe(true);
  });

  it('requires all three emotional fields on step 3', () => {
    const complete = {
      ...INITIAL_FORM_DATA,
      morningMood: 'Positive',
      emotionalLow: 'Rarely',
      anxietyLevel: 'Sometimes',
    };
    expect(isStepValid(3, complete)).toBe(true);
    expect(isStepValid(3, { ...complete, anxietyLevel: '' })).toBe(false);
  });

  it('treats steps with no required fields (e.g. step 4) as valid', () => {
    expect(isStepValid(4, { ...INITIAL_FORM_DATA })).toBe(true);
  });
});

describe('getSleepDurationLabel', () => {
  it('maps each slider value to its label', () => {
    expect(getSleepDurationLabel('1')).toBe('Less than 4 hours');
    expect(getSleepDurationLabel('2')).toBe('4-5 hours');
    expect(getSleepDurationLabel('3')).toBe('6 hours');
    expect(getSleepDurationLabel('4')).toBe('7-8 hours');
    expect(getSleepDurationLabel('5')).toBe('More than 8 hours');
  });

  it('falls back to the longest-sleep label for unknown values', () => {
    expect(getSleepDurationLabel('99')).toBe('More than 8 hours');
  });
});

describe('buildSurveyPayload', () => {
  it('maps camelCase form state to the snake_case API payload', () => {
    const formData = {
      sleepDuration: '4',
      energyLevel: 'High',
      academicPressure: 'Often',
      studyMotivation: 'Motivated',
      concentrationDifficulty: 'Slightly difficult',
      morningMood: 'Positive',
      emotionalLow: 'Rarely',
      anxietyLevel: 'Sometimes',
      socialSupport: 'Mostly',
      financialStress: 'Low',
    };

    expect(buildSurveyPayload(formData)).toEqual({
      sleep_duration: '4',
      energy_level: 'High',
      academic_pressure: 'Often',
      study_motivation: 'Motivated',
      concentration_difficulty: 'Slightly difficult',
      morning_mood: 'Positive',
      emotional_low: 'Rarely',
      anxiety_level: 'Sometimes',
      social_support: 'Mostly',
      financial_stress: 'Low',
    });
  });
});
