"""
predict.py – Map survey answers to the trained RF model and return a wellness score.

The model was trained on these Kaggle columns (after get_dummies):
  'Academic Pressure', 'Study Satisfaction', 'Work/Study Hours',
  'Financial Stress',
  'Sleep Duration_5-6 hours', 'Sleep Duration_7-8 hours',
  'Sleep Duration_Less than 5 hours', 'Sleep Duration_More than 8 hours',
  'Sleep Duration_Others'

Our survey fields map as follows:
  academic_pressure        → Academic Pressure   (frequency 1-5)
  study_motivation         → Study Satisfaction   (motivation 1-5, proxy)
  concentration_difficulty → Work/Study Hours     (difficulty 1-5, proxy)
  financial_stress         → Financial Stress     (stress 1-5)
  sleep_duration           → one-hot Sleep Duration columns
"""

from __future__ import annotations

import os
import pathlib
from typing import Optional

import joblib
import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
ARTIFACT_DIR = pathlib.Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "wellness_model.pkl"
COLUMNS_PATH = ARTIFACT_DIR / "model_columns.pkl"

# ── Encoding maps ────────────────────────────────────────────────────────────

FREQUENCY_MAP = {
    "never": 1, "rarely": 2, "sometimes": 3,
    "often": 4, "constantly": 5, "almost always": 5, "always": 5,
}

MOTIVATION_MAP = {
    "not motivated": 1, "slightly motivated": 2,
    "neutral": 3, "motivated": 4, "highly motivated": 5,
}

CONCENTRATION_MAP = {
    "not difficult": 1, "slightly difficult": 2,
    "moderately difficult": 3, "very difficult": 4,
    "extremely difficult": 5,
}

FINANCIAL_MAP = {
    "none": 1, "low": 2, "moderate": 3,
    "high": 4, "extremely high": 5,
}

# Frontend sends sleep_duration as slider "1"-"5" → Kaggle category
SLEEP_SLIDER_TO_CATEGORY = {
    "1": "Less than 5 hours",   # < 4 h
    "2": "5-6 hours",           # 4-5 h
    "3": "5-6 hours",           # 6 h  (closest bucket)
    "4": "7-8 hours",           # 7-8 h
    "5": "More than 8 hours",   # > 8 h
}

# All possible Kaggle sleep categories for one-hot
SLEEP_CATEGORIES = [
    "5-6 hours", "7-8 hours",
    "Less than 5 hours", "More than 8 hours", "Others",
]

# ── Risk labels ───────────────────────────────────────────────────────────────
RISK_LABELS = {
    0: {"label": "Low Risk",      "color": "green",  "emoji": "😊", "level": 0},
    1: {"label": "Moderate Risk",  "color": "yellow", "emoji": "😐", "level": 1},
    2: {"label": "High Risk",     "color": "red",    "emoji": "😟", "level": 2},
}


def _load_model():
    """Load model and columns (cached after first call)."""
    model = joblib.load(MODEL_PATH)
    columns = joblib.load(COLUMNS_PATH)
    return model, columns


_cached_model = None
_cached_columns = None


def get_model():
    global _cached_model, _cached_columns
    if _cached_model is None:
        _cached_model, _cached_columns = _load_model()
    return _cached_model, _cached_columns


def map_survey_to_features(survey: dict) -> pd.DataFrame:
    """
    Convert raw survey answers to the feature DataFrame the model expects.

    Parameters
    ----------
    survey : dict
        Keys: sleep_duration, academic_pressure, study_motivation,
              concentration_difficulty, financial_stress
        (plus other fields that are ignored by this model)

    Returns
    -------
    pd.DataFrame  – single row with the model's expected columns
    """
    _, columns = get_model()

    # Encode numeric features
    ap = FREQUENCY_MAP.get(survey.get("academic_pressure", "").strip().lower(), 3)
    sm = MOTIVATION_MAP.get(survey.get("study_motivation", "").strip().lower(), 3)
    cd = CONCENTRATION_MAP.get(survey.get("concentration_difficulty", "").strip().lower(), 3)
    fs = FINANCIAL_MAP.get(survey.get("financial_stress", "").strip().lower(), 3)

    # Sleep one-hot
    raw_sleep = str(survey.get("sleep_duration", "3")).strip()
    sleep_cat = SLEEP_SLIDER_TO_CATEGORY.get(raw_sleep, raw_sleep)

    row = {
        "Academic Pressure": ap,
        "Study Satisfaction": sm,
        "Work/Study Hours": cd,
        "Financial Stress": fs,
    }
    for cat in SLEEP_CATEGORIES:
        col_name = f"Sleep Duration_{cat}"
        row[col_name] = 1 if sleep_cat == cat else 0

    df = pd.DataFrame([row], columns=columns)
    df = df.fillna(0)
    return df


def predict_wellness(survey: dict) -> dict:
    """
    Run the full prediction pipeline.

    Parameters
    ----------
    survey : dict
        Raw survey answers from the database.

    Returns
    -------
    dict
        {
            "risk_probability": float,
            "risk_level": int (0, 1, 2),
            "risk_label": str,
            "risk_color": str,
            "risk_emoji": str,
            "wellness_score": int (0-100, higher = better)
        }
    """
    model, _ = get_model()
    features = map_survey_to_features(survey)
    proba = model.predict_proba(features)[0]

    # proba[1] = probability of Depression (at-risk class)
    risk_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])

    # Map to risk level
    if risk_prob < 0.35:
        level = 0
    elif risk_prob < 0.65:
        level = 1
    else:
        level = 2

    info = RISK_LABELS[level]

    # Wellness score: 100 = perfect, 0 = highest risk
    wellness_score = int(round((1 - risk_prob) * 100))

    return {
        "risk_probability": round(risk_prob, 4),
        "risk_level":       info["level"],
        "risk_label":       info["label"],
        "risk_color":       info["color"],
        "risk_emoji":       info["emoji"],
        "wellness_score":   wellness_score,
    }
