// Pure helpers for the Baseline Assessment survey: per-step validation, the
// sleep-duration slider label, and the camelCase -> snake_case API payload.

import { STEP_REQUIRED_FIELDS, SLEEP_DURATION_LABELS } from '../constants/baselineSurvey';

export const isStepValid = (step, formData) =>
  (STEP_REQUIRED_FIELDS[step] || []).every((field) => Boolean(formData[field]));

export const getSleepDurationLabel = (value) =>
  SLEEP_DURATION_LABELS[value] || 'More than 8 hours';

export const buildSurveyPayload = (formData) => ({
  sleep_duration: formData.sleepDuration,
  energy_level: formData.energyLevel,
  academic_pressure: formData.academicPressure,
  study_motivation: formData.studyMotivation,
  concentration_difficulty: formData.concentrationDifficulty,
  morning_mood: formData.morningMood,
  emotional_low: formData.emotionalLow,
  anxiety_level: formData.anxietyLevel,
  social_support: formData.socialSupport,
  financial_stress: formData.financialStress,
});
