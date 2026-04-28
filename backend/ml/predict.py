"""
predict.py
==========
Unified wellness prediction pipeline.

Model priority (highest to lowest)
-----------------------------------
1. wellness_user_rf.joblib   – trained from real user survey CSVs (10 features)
2. wellness_full_rf_latest.joblib – retrained from live DB data   (10 features)
3. wellness_model.pkl         – baseline Kaggle model             (5 features)

The first model found on disk is used.  Models 1 & 2 run through the full
``encode_survey()`` pipeline (ml/wellness/encoders.py).  Model 3 uses its
own legacy one-hot encoder for backward compatibility.
"""

from __future__ import annotations

import pathlib
from functools import lru_cache
from typing import Optional

import joblib
import pandas as pd

# ── Artifact paths ────────────────────────────────────────────────────────────

ARTIFACT_DIR   = pathlib.Path(__file__).resolve().parent / "artifacts"

# User-survey model (trained from real CSV exports) – highest priority
USER_MODEL_PATH    = ARTIFACT_DIR / "wellness_user_rf.joblib"
# DB-retrain model – second priority
FULL_MODEL_PATH    = ARTIFACT_DIR / "wellness_full_rf_latest.joblib"
# Kaggle baseline – fallback
KAGGLE_MODEL_PATH  = ARTIFACT_DIR / "wellness_model.pkl"
KAGGLE_COLS_PATH   = ARTIFACT_DIR / "model_columns.pkl"

# Feature order expected by the 10-feature models
ALL_FEATURES: list[str] = [
    "sleep_duration",
    "academic_pressure",
    "financial_stress",
    "study_motivation",
    "concentration_difficulty",
    "energy_level",
    "morning_mood",
    "emotional_low",
    "anxiety_level",
    "social_support",
]

# ── Risk labels ───────────────────────────────────────────────────────────────

RISK_LABELS = {
    0: {"label": "Low Risk",      "color": "green",  "emoji": "😊", "level": 0},
    1: {"label": "Moderate Risk", "color": "yellow", "emoji": "😐", "level": 1},
    2: {"label": "High Risk",     "color": "red",    "emoji": "😟", "level": 2},
}

# ── Lazy model cache ──────────────────────────────────────────────────────────

_user_model   = None
_full_model   = None
_kaggle_model = None
_kaggle_cols  = None


def _load_user_model():
    global _user_model
    if _user_model is None and USER_MODEL_PATH.exists():
        _user_model = joblib.load(USER_MODEL_PATH)
    return _user_model


def _load_full_model():
    global _full_model
    if _full_model is None and FULL_MODEL_PATH.exists():
        _full_model = joblib.load(FULL_MODEL_PATH)
    return _full_model


def _load_kaggle_model():
    global _kaggle_model, _kaggle_cols
    if _kaggle_model is None:
        _kaggle_model = joblib.load(KAGGLE_MODEL_PATH)
        _kaggle_cols  = joblib.load(KAGGLE_COLS_PATH)
    return _kaggle_model, _kaggle_cols


def active_model_name() -> str:
    """Return the name of the model that will be used for prediction."""
    if USER_MODEL_PATH.exists():
        return "wellness_user_rf"
    if FULL_MODEL_PATH.exists():
        return "wellness_full_rf_latest"
    return "wellness_model_kaggle"


# ── 10-feature prediction (user / full model) ─────────────────────────────────

def _predict_10feature(model, survey: dict, version: str) -> dict:
    """
    Run prediction using a model trained on all 10 survey features.

    Parameters
    ----------
    model   : sklearn RF already loaded
    survey  : raw text answer dict (same keys the app stores in baseline_surveys)
    version : human-readable model version string
    """
    from ml.wellness.encoders import encode_survey

    encoded = encode_survey(survey)
    row = pd.DataFrame(
        [[encoded[f] for f in ALL_FEATURES]],
        columns=ALL_FEATURES,
    )

    proba    = model.predict_proba(row)[0]
    risk_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])

    if risk_prob < 0.35:
        level = 0
    elif risk_prob < 0.65:
        level = 1
    else:
        level = 2

    info = RISK_LABELS[level]
    wellness_score = int(round((1 - risk_prob) * 100))

    return {
        "risk_probability": round(risk_prob, 4),
        "risk_level":       info["level"],
        "risk_label":       info["label"],
        "risk_color":       info["color"],
        "risk_emoji":       info["emoji"],
        "wellness_score":   wellness_score,
        "model_version":    version,
    }


# ── Legacy Kaggle 5-feature prediction ───────────────────────────────────────

# Encoding maps (kept for backward-compat with the Kaggle model)
_FREQ_MAP = {
    "never": 1, "rarely": 2, "sometimes": 3,
    "often": 4, "constantly": 5, "almost always": 5, "always": 5,
}
_MOTIV_MAP = {
    "not motivated": 1, "slightly motivated": 2,
    "neutral": 3, "motivated": 4, "highly motivated": 5,
}
_CONC_MAP = {
    "not difficult": 1, "slightly difficult": 2,
    "moderately difficult": 3, "very difficult": 4, "extremely difficult": 5,
}
_FIN_MAP = {
    "none": 1, "low": 2, "moderate": 3, "high": 4, "extremely high": 5,
}
_SLEEP_SLIDER = {
    "1": "Less than 5 hours", "2": "5-6 hours",
    "3": "5-6 hours",         "4": "7-8 hours",
    "5": "More than 8 hours",
}
_SLEEP_CATS = ["5-6 hours", "7-8 hours", "Less than 5 hours", "More than 8 hours", "Others"]


def _predict_kaggle(survey: dict) -> dict:
    """Legacy prediction using the Kaggle 5-feature model."""
    model, columns = _load_kaggle_model()

    ap  = _FREQ_MAP.get(survey.get("academic_pressure", "").strip().lower(), 3)
    sm  = _MOTIV_MAP.get(survey.get("study_motivation", "").strip().lower(), 3)
    cd  = _CONC_MAP.get(survey.get("concentration_difficulty", "").strip().lower(), 3)
    fs  = _FIN_MAP.get(survey.get("financial_stress", "").strip().lower(), 3)

    raw_sleep  = str(survey.get("sleep_duration", "3")).strip()
    sleep_cat  = _SLEEP_SLIDER.get(raw_sleep, raw_sleep)

    row = {
        "Academic Pressure":  ap,
        "Study Satisfaction": sm,
        "Work/Study Hours":   cd,
        "Financial Stress":   fs,
    }
    for cat in _SLEEP_CATS:
        row[f"Sleep Duration_{cat}"] = 1 if sleep_cat == cat else 0

    df = pd.DataFrame([row], columns=columns).fillna(0)

    proba     = model.predict_proba(df)[0]
    risk_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])

    if risk_prob < 0.35:
        level = 0
    elif risk_prob < 0.65:
        level = 1
    else:
        level = 2

    info = RISK_LABELS[level]
    return {
        "risk_probability": round(risk_prob, 4),
        "risk_level":       info["level"],
        "risk_label":       info["label"],
        "risk_color":       info["color"],
        "risk_emoji":       info["emoji"],
        "wellness_score":   int(round((1 - risk_prob) * 100)),
        "model_version":    "wellness_model_kaggle",
    }


# ── Public API ────────────────────────────────────────────────────────────────

def predict_wellness(survey: dict) -> dict:
    """
    Run the full prediction pipeline.

    Tries models in priority order:
      1. User-survey RF  (10 features, trained from real exported CSVs)
      2. Full DB RF      (10 features, retrained from live app data)
      3. Kaggle baseline (5 features, fallback)

    Parameters
    ----------
    survey : dict
        Raw text answers from ``baseline_surveys`` DB record, e.g.::

            {
                "sleep_duration":            "4",
                "energy_level":              "Moderate",
                "academic_pressure":         "Often",
                "study_motivation":          "Motivated",
                "concentration_difficulty":  "Moderately difficult",
                "morning_mood":              "Neutral",
                "emotional_low":             "Sometimes",
                "anxiety_level":             "Sometimes",
                "social_support":            "Moderately",
                "financial_stress":          "Moderate",
            }

    Returns
    -------
    dict
        {
            "risk_probability": float,
            "risk_level":       int   (0=Low, 1=Moderate, 2=High),
            "risk_label":       str,
            "risk_color":       str,
            "risk_emoji":       str,
            "wellness_score":   int   (0-100, higher = better),
            "model_version":    str,
        }
    """
    # 1. User-survey model (highest priority)
    user_model = _load_user_model()
    if user_model is not None:
        return _predict_10feature(user_model, survey, "wellness_user_rf_v1")

    # 2. DB-retrained full model
    full_model = _load_full_model()
    if full_model is not None:
        return _predict_10feature(full_model, survey, "wellness_full_rf_latest")

    # 3. Kaggle baseline fallback
    return _predict_kaggle(survey)
