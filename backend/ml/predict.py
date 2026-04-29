"""
predict.py – Map survey answers to the trained model and return a wellness score.

All 10 survey fields are used:
  academic_pressure        → Academic Pressure   (frequency 1-5)
  study_motivation         → Study Satisfaction  (motivation 1-5)
  concentration_difficulty → Work/Study Hours    (difficulty 1-5)
  financial_stress         → Financial Stress    (stress 1-5)
  energy_level             → Energy Level        (1-5)
  morning_mood             → Morning Mood        (1-5)
  emotional_low            → Emotional Low       (frequency 1-5)
  anxiety_level            → Anxiety Level       (frequency 1-5)
  social_support           → Social Support      (1-5)
  sleep_duration           → Sleep Duration_*    (one-hot, slider 1-5)
"""

from __future__ import annotations

import pathlib

import joblib
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
ARTIFACT_DIR = pathlib.Path(__file__).resolve().parent / "artifacts"
MODEL_PATH   = ARTIFACT_DIR / "wellness_model.pkl"
COLUMNS_PATH = ARTIFACT_DIR / "model_columns.pkl"

# ── Encoding maps ──────────────────────────────────────────────────────────────

FREQUENCY_MAP = {
    "never": 1, "rarely": 2, "sometimes": 3,
    "often": 4, "almost always": 5, "constantly": 5, "always": 5,
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

ENERGY_MAP = {
    "very low": 1, "low": 2, "moderate": 3,
    "high": 4, "very high": 5,
}

MORNING_MAP = {
    "very sad / hopeless": 1, "very sad": 1, "sad": 2,
    "neutral": 3,
    "positive": 4,
    "very happy / energized": 5, "energized": 5, "very happy": 5,
}

SUPPORT_MAP = {
    "not at all": 1, "slightly": 2, "moderately": 3,
    "mostly": 4, "very supported": 5,
}

# Frontend sends sleep_duration as slider "1"–"5"
SLEEP_SLIDER_TO_CATEGORY = {
    "1": "Less than 5 hours",
    "2": "5-6 hours",
    "3": "5-6 hours",
    "4": "7-8 hours",
    "5": "More than 8 hours",
}

SLEEP_CATEGORIES = [
    "5-6 hours", "7-8 hours",
    "Less than 5 hours", "More than 8 hours", "Others",
]

# ── Risk labels ────────────────────────────────────────────────────────────────
RISK_LABELS = {
    0: {"label": "Low Risk",      "color": "green",  "emoji": "😊", "level": 0},
    1: {"label": "Moderate Risk", "color": "yellow", "emoji": "😐", "level": 1},
    2: {"label": "High Risk",     "color": "red",    "emoji": "😟", "level": 2},
}

# ── Model cache ────────────────────────────────────────────────────────────────
_cached_model   = None
_cached_columns = None


def get_model():
    global _cached_model, _cached_columns
    if _cached_model is None:
        _cached_model   = joblib.load(MODEL_PATH)
        _cached_columns = joblib.load(COLUMNS_PATH)
    return _cached_model, _cached_columns


# ── Feature builder ────────────────────────────────────────────────────────────

def map_survey_to_features(survey: dict) -> pd.DataFrame:
    """Convert raw survey answers to the feature DataFrame the model expects."""
    _, columns = get_model()

    def get(key, mapping, default=3):
        return mapping.get(survey.get(key, "").strip().lower(), default)

    ap  = get("academic_pressure",        FREQUENCY_MAP)
    sm  = get("study_motivation",         MOTIVATION_MAP)
    cd  = get("concentration_difficulty", CONCENTRATION_MAP)
    fs  = get("financial_stress",         FINANCIAL_MAP)
    el  = get("energy_level",             ENERGY_MAP)
    mm  = get("morning_mood",             MORNING_MAP)
    emo = get("emotional_low",            FREQUENCY_MAP)
    anx = get("anxiety_level",            FREQUENCY_MAP)
    ss  = get("social_support",           SUPPORT_MAP)

    raw_sleep = str(survey.get("sleep_duration", "3")).strip()
    sleep_cat = SLEEP_SLIDER_TO_CATEGORY.get(raw_sleep, raw_sleep)

    row: dict = {
        "Academic Pressure":  ap,
        "Study Satisfaction": sm,
        "Work/Study Hours":   cd,
        "Financial Stress":   fs,
        "Energy Level":       el,
        "Morning Mood":       mm,
        "Emotional Low":      emo,
        "Anxiety Level":      anx,
        "Social Support":     ss,
    }
    for cat in SLEEP_CATEGORIES:
        row[f"Sleep Duration_{cat}"] = 1 if sleep_cat == cat else 0

    df = pd.DataFrame([row], columns=columns)
    df = df.fillna(0)
    return df


# ── Public prediction API ──────────────────────────────────────────────────────

def predict_wellness(survey: dict) -> dict:
    """
    Run the full prediction pipeline.

    Returns
    -------
    dict with keys:
        risk_probability  float
        risk_level        int   (0 low / 1 moderate / 2 high)
        risk_label        str
        risk_color        str
        risk_emoji        str
        wellness_score    int   (0-100, higher = better)
    """
    model, _ = get_model()
    features  = map_survey_to_features(survey)
    proba     = model.predict_proba(features)[0]

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
    }
