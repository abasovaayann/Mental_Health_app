// Constants for the multi-step Baseline Assessment survey.

export const TOTAL_STEPS = 4;

export const INITIAL_FORM_DATA = {
  sleepDuration: '4',
  energyLevel: '',
  academicPressure: '',
  studyMotivation: '',
  concentrationDifficulty: '',
  morningMood: '',
  emotionalLow: '',
  anxietyLevel: '',
  socialSupport: '',
  financialStress: '',
};

// Fields that must be answered before advancing past each step. Step 4 is the
// final step (submitted rather than advanced), so it has no entry here.
export const STEP_REQUIRED_FIELDS = {
  1: ['energyLevel'],
  2: ['academicPressure', 'studyMotivation', 'concentrationDifficulty'],
  3: ['morningMood', 'emotionalLow', 'anxietyLevel'],
};

export const SLEEP_DURATION_LABELS = {
  1: 'Less than 4 hours',
  2: '4-5 hours',
  3: '6 hours',
  4: '7-8 hours',
  5: 'More than 8 hours',
};
