"""
Feature splitting – separate encoded survey into base-model (Kaggle-compatible)
features and additional custom features for future retraining.

Kaggle dataset columns used by the pre-trained RF model
-------------------------------------------------------
The original Kaggle model uses these columns (after cleaning):
  Sleep Duration, Academic Pressure, Financial Stress,
  Study Satisfaction, CGPA, Work/Study Hours, ...

Our custom survey maps onto a subset of those:
  sleep_duration         → Sleep Duration    (hours, float)
  academic_pressure      → Academic Pressure (1-5)
  financial_stress       → Financial Stress  (1-5)
  study_motivation       → Study Satisfaction (1-5, proxy)
  concentration_difficulty → mapped to work/study difficulty (1-5)

The remaining five questions are *custom* and will be used once we
collect enough user-generated data to retrain a full model.
"""

from __future__ import annotations

from typing import TypedDict


# ── Feature lists ─────────────────────────────────────────────────────────────

BASE_MODEL_FEATURES: list[str] = [
    "sleep_duration",            # → Kaggle: Sleep Duration
    "academic_pressure",         # → Kaggle: Academic Pressure
    "financial_stress",          # → Kaggle: Financial Stress
    "study_motivation",          # → Kaggle: Study Satisfaction (proxy)
    "concentration_difficulty",  # → Kaggle: concentration / work difficulty
]
"""Features compatible with the Kaggle pre-trained Random Forest."""

ADDITIONAL_FEATURES: list[str] = [
    "energy_level",
    "morning_mood",
    "emotional_low",
    "anxiety_level",
    "social_support",
]
"""Custom-only features – collected & stored now, used for future retraining."""

ALL_FEATURES: list[str] = BASE_MODEL_FEATURES + ADDITIONAL_FEATURES
"""All 10 survey features."""


# ── Typed outputs ─────────────────────────────────────────────────────────────

class FeatureSplit(TypedDict):
    base_features: dict[str, int | float]
    additional_features: dict[str, int | float]


# ── Public function ───────────────────────────────────────────────────────────

def split_features(encoded_survey: dict[str, int | float]) -> FeatureSplit:
    """
    Split an encoded survey dict into base-model and additional feature groups.

    Parameters
    ----------
    encoded_survey : dict
        Output of ``encode_survey()`` – all 10 fields with numeric values.

    Returns
    -------
    FeatureSplit
        ``{"base_features": {...}, "additional_features": {...}}``

    Examples
    --------
    >>> from ml.wellness.encoders import encode_survey
    >>> raw = {
    ...     "sleep_duration": "4",
    ...     "energy_level": "Moderate",
    ...     "academic_pressure": "Often",
    ...     "study_motivation": "Motivated",
    ...     "concentration_difficulty": "Moderately difficult",
    ...     "morning_mood": "Neutral",
    ...     "emotional_low": "Sometimes",
    ...     "anxiety_level": "Sometimes",
    ...     "social_support": "Moderately",
    ...     "financial_stress": "Moderate",
    ... }
    >>> encoded = encode_survey(raw)
    >>> result = split_features(encoded)
    >>> sorted(result["base_features"].keys())
    ['academic_pressure', 'concentration_difficulty', 'financial_stress', 'sleep_duration', 'study_motivation']
    >>> sorted(result["additional_features"].keys())
    ['anxiety_level', 'emotional_low', 'energy_level', 'morning_mood', 'social_support']
    """
    base = {k: encoded_survey[k] for k in BASE_MODEL_FEATURES if k in encoded_survey}
    additional = {k: encoded_survey[k] for k in ADDITIONAL_FEATURES if k in encoded_survey}

    return FeatureSplit(
        base_features=base,
        additional_features=additional,
    )
