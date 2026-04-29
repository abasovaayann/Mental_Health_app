"""
Wellness prediction pipeline.

Model priority:
1. ``wellness_user_rf.joblib`` - 10-feature model trained from survey exports
2. ``wellness_full_rf_latest.joblib`` - 10-feature model retrained from app data
3. ``wellness_model.pkl`` - legacy Kaggle fallback model

The 10-feature models use the app's full baseline survey answers. The Kaggle
fallback uses the older 5-feature layout and is kept for compatibility with
the artifacts currently present in this repo.
"""

from __future__ import annotations

import pathlib

import joblib
import pandas as pd

ARTIFACT_DIR = pathlib.Path(__file__).resolve().parent / "artifacts"

USER_MODEL_PATH = ARTIFACT_DIR / "wellness_user_rf.joblib"
FULL_MODEL_PATH = ARTIFACT_DIR / "wellness_full_rf_latest.joblib"
KAGGLE_MODEL_PATH = ARTIFACT_DIR / "wellness_model.pkl"
KAGGLE_COLS_PATH = ARTIFACT_DIR / "model_columns.pkl"

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

RISK_LABELS = {
    0: {"label": "Low Risk", "color": "green", "emoji": "calm", "level": 0},
    1: {"label": "Moderate Risk", "color": "yellow", "emoji": "concerned", "level": 1},
    2: {"label": "High Risk", "color": "red", "emoji": "distressed", "level": 2},
}

_user_model = None
_full_model = None
_kaggle_model = None
_kaggle_cols = None

_FREQ_MAP = {
    "never": 1,
    "rarely": 2,
    "sometimes": 3,
    "often": 4,
    "almost always": 5,
    "constantly": 5,
    "always": 5,
}
_MOTIVATION_MAP = {
    "not motivated": 1,
    "slightly motivated": 2,
    "neutral": 3,
    "motivated": 4,
    "highly motivated": 5,
}
_CONCENTRATION_MAP = {
    "not difficult": 1,
    "slightly difficult": 2,
    "moderately difficult": 3,
    "very difficult": 4,
    "extremely difficult": 5,
}
_FINANCIAL_MAP = {
    "none": 1,
    "low": 2,
    "moderate": 3,
    "high": 4,
    "extremely high": 5,
}
_ENERGY_MAP = {
    "very low": 1,
    "low": 2,
    "moderate": 3,
    "high": 4,
    "very high": 5,
}
_MORNING_MAP = {
    "very sad / hopeless": 1,
    "very sad": 1,
    "sad": 2,
    "neutral": 3,
    "positive": 4,
    "energized": 5,
    "very happy": 5,
    "very happy / energized": 5,
}
_SUPPORT_MAP = {
    "not at all": 1,
    "slightly": 2,
    "moderately": 3,
    "mostly": 4,
    "very supported": 5,
    "very": 4,
    "extremely": 5,
}
_SLEEP_SLIDER_TO_CATEGORY = {
    "1": "Less than 5 hours",
    "2": "5-6 hours",
    "3": "5-6 hours",
    "4": "7-8 hours",
    "5": "More than 8 hours",
}
_SLEEP_CATEGORY_TO_SCORE = {
    "less than 5 hours": 1.0,
    "5-6 hours": 2.0,
    "7-8 hours": 3.0,
    "more than 8 hours": 4.0,
    "others": 2.5,
}
_SLEEP_CATEGORY_CANONICAL = {
    "less than 5 hours": "Less than 5 hours",
    "5-6 hours": "5-6 hours",
    "7-8 hours": "7-8 hours",
    "more than 8 hours": "More than 8 hours",
    "others": "Others",
}
_KAGGLE_SLEEP_CATS = [
    "5-6 hours",
    "7-8 hours",
    "Less than 5 hours",
    "More than 8 hours",
    "Others",
]


def _force_single_worker(model) -> None:
    estimator = model
    if hasattr(model, "steps") and model.steps:
        estimator = model.steps[-1][1]
    if hasattr(estimator, "n_jobs"):
        estimator.n_jobs = 1


def _normalize_text(value: object) -> str:
    return str(value or "").strip().lower()


def _map_text(value: object, mapping: dict[str, int], default: int = 3) -> int:
    text = _normalize_text(value)
    if text.isdigit():
        return int(text)
    return mapping.get(text, default)


def _normalize_sleep_category(value: object) -> str:
    text = str(value or "3").strip()
    if text in _SLEEP_SLIDER_TO_CATEGORY:
        return _SLEEP_SLIDER_TO_CATEGORY[text]
    normalized = _normalize_text(text)
    if normalized in _SLEEP_CATEGORY_CANONICAL:
        return _SLEEP_CATEGORY_CANONICAL[normalized]
    return text


def _sleep_numeric_value(value: object) -> float:
    category = _normalize_sleep_category(value)
    return _SLEEP_CATEGORY_TO_SCORE.get(_normalize_text(category), 2.5)


def _load_user_model():
    global _user_model
    if _user_model is None and USER_MODEL_PATH.exists():
        _user_model = joblib.load(USER_MODEL_PATH)
        _force_single_worker(_user_model)
    return _user_model


def _load_full_model():
    global _full_model
    if _full_model is None and FULL_MODEL_PATH.exists():
        _full_model = joblib.load(FULL_MODEL_PATH)
        _force_single_worker(_full_model)
    return _full_model


def _load_kaggle_model():
    global _kaggle_model, _kaggle_cols
    if _kaggle_model is None:
        _kaggle_model = joblib.load(KAGGLE_MODEL_PATH)
        _kaggle_cols = joblib.load(KAGGLE_COLS_PATH)
        _force_single_worker(_kaggle_model)
    return _kaggle_model, _kaggle_cols


def active_model_name() -> str:
    if USER_MODEL_PATH.exists():
        return "wellness_user_rf"
    if FULL_MODEL_PATH.exists():
        return "wellness_full_rf_latest"
    return "wellness_model_kaggle"


def _build_prediction_payload(risk_prob: float, model_version: str) -> dict:
    if risk_prob < 0.35:
        level = 0
    elif risk_prob < 0.65:
        level = 1
    else:
        level = 2

    info = RISK_LABELS[level]
    return {
        "risk_probability": round(risk_prob, 4),
        "risk_level": info["level"],
        "risk_label": info["label"],
        "risk_color": info["color"],
        "risk_emoji": info["emoji"],
        "wellness_score": int(round((1 - risk_prob) * 100)),
        "model_version": model_version,
    }


def _encode_10feature_survey(survey: dict) -> dict[str, float]:
    return {
        "sleep_duration": _sleep_numeric_value(survey.get("sleep_duration")),
        "academic_pressure": _map_text(survey.get("academic_pressure"), _FREQ_MAP),
        "financial_stress": _map_text(survey.get("financial_stress"), _FINANCIAL_MAP),
        "study_motivation": _map_text(survey.get("study_motivation"), _MOTIVATION_MAP),
        "concentration_difficulty": _map_text(
            survey.get("concentration_difficulty"), _CONCENTRATION_MAP
        ),
        "energy_level": _map_text(survey.get("energy_level"), _ENERGY_MAP),
        "morning_mood": _map_text(survey.get("morning_mood"), _MORNING_MAP),
        "emotional_low": _map_text(survey.get("emotional_low"), _FREQ_MAP),
        "anxiety_level": _map_text(survey.get("anxiety_level"), _FREQ_MAP),
        "social_support": _map_text(survey.get("social_support"), _SUPPORT_MAP),
    }


def _predict_10feature(model, survey: dict, version: str) -> dict:
    encoded = _encode_10feature_survey(survey)
    frame = pd.DataFrame([[encoded[name] for name in ALL_FEATURES]], columns=ALL_FEATURES)
    proba = model.predict_proba(frame)[0]
    risk_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])
    return _build_prediction_payload(risk_prob, version)


def _predict_kaggle(survey: dict) -> dict:
    model, columns = _load_kaggle_model()

    sleep_category = _normalize_sleep_category(survey.get("sleep_duration"))
    row = {
        "Academic Pressure": _map_text(survey.get("academic_pressure"), _FREQ_MAP),
        "Study Satisfaction": _map_text(survey.get("study_motivation"), _MOTIVATION_MAP),
        "Work/Study Hours": _map_text(
            survey.get("concentration_difficulty"), _CONCENTRATION_MAP
        ),
        "Financial Stress": _map_text(survey.get("financial_stress"), _FINANCIAL_MAP),
    }
    for category in _KAGGLE_SLEEP_CATS:
        row[f"Sleep Duration_{category}"] = 1 if sleep_category == category else 0

    frame = pd.DataFrame([row], columns=columns).fillna(0)
    proba = model.predict_proba(frame)[0]
    risk_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])
    return _build_prediction_payload(risk_prob, "wellness_model_kaggle")


def predict_wellness(survey: dict) -> dict:
    """
    Run the full prediction pipeline.

    The function prefers the newer 10-feature models when their artifacts are
    available, and falls back to the legacy Kaggle model otherwise.
    """
    user_model = _load_user_model()
    if user_model is not None:
        return _predict_10feature(user_model, survey, "wellness_user_rf")

    full_model = _load_full_model()
    if full_model is not None:
        return _predict_10feature(full_model, survey, "wellness_full_rf_latest")

    return _predict_kaggle(survey)
