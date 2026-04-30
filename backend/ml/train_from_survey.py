"""
Train a wellness-risk model from the exported English and Turkish survey CSVs.

This script produces the primary 10-feature model used by ``predict.py``:

- ``ml/artifacts/wellness_user_rf.joblib``
- ``ml/artifacts/wellness_user_meta.json``

The exported survey files are expected at:

- ``ml/data/survey_en.csv``
- ``ml/data/survey_tr.csv``
"""

from __future__ import annotations

import json
import pathlib

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score

from ml.predict import ALL_FEATURES, USER_MODEL_PATH, _encode_10feature_survey

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
ARTIFACT_DIR = SCRIPT_DIR / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

EN_CSV = DATA_DIR / "survey_en.csv"
TR_CSV = DATA_DIR / "survey_tr.csv"
META_PATH = ARTIFACT_DIR / "wellness_user_meta.json"

EN_LABEL_MAP = {
    "very poor": 1,
    "poor": 1,
    "neutral": 0,
    "good": 0,
    "very good": 0,
}


def _normalize_morning_mood(value: object) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "negative": "sad",
        "very negative": "very sad",
        "very positive": "very happy",
    }
    return aliases.get(text, str(value or "").strip())


def _normalize_sleep(value: object) -> str:
    text = str(value or "").strip()
    aliases = {
        "Less than 4 hours": "Less than 5 hours",
        "4-5 hours": "5-6 hours",
        "6 hours": "5-6 hours",
    }
    return aliases.get(text, text)


def _build_raw_answers(row: pd.Series) -> dict[str, object]:
    return {
        "sleep_duration": _normalize_sleep(row["sleep"]),
        "energy_level": row["energy"],
        "academic_pressure": row["academic_pressure"],
        "study_motivation": row["study_motivation"],
        "concentration_difficulty": row["concentration"],
        "morning_mood": _normalize_morning_mood(row["morning_mood"]),
        "emotional_low": row["emotional_low"],
        "anxiety_level": row["anxiety"],
        "social_support": row["social_support"],
        "financial_stress": row["financial_stress"],
    }


def _encode_row(row: pd.Series) -> dict[str, float]:
    encoded = _encode_10feature_survey(_build_raw_answers(row))
    return {name: float(encoded[name]) for name in ALL_FEATURES}


def _english_label(value: object) -> int:
    return EN_LABEL_MAP.get(str(value or "").strip().lower(), 0)


def _turkish_label(value: object) -> int:
    try:
        return 1 if int(value) <= 2 else 0
    except (TypeError, ValueError):
        return 0


def _load_csv(path: pathlib.Path, label_fn) -> tuple[list[dict[str, float]], list[int]]:
    df = pd.read_csv(path)
    rows: list[dict[str, float]] = []
    labels: list[int] = []

    for _, record in df.iterrows():
        rows.append(_encode_row(record))
        labels.append(label_fn(record["wellbeing"]))

    return rows, labels


def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    if not EN_CSV.exists():
        raise FileNotFoundError(f"Missing English survey export: {EN_CSV}")
    if not TR_CSV.exists():
        raise FileNotFoundError(f"Missing Turkish survey export: {TR_CSV}")

    en_rows, en_labels = _load_csv(EN_CSV, _english_label)
    tr_rows, tr_labels = _load_csv(TR_CSV, _turkish_label)

    features = pd.DataFrame(en_rows + tr_rows, columns=ALL_FEATURES)
    labels = pd.Series(en_labels + tr_labels, name="at_risk")
    return features, labels


def build_model() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=1,
    )


def train_model(
    features: pd.DataFrame,
    labels: pd.Series,
) -> tuple[RandomForestClassifier, dict[str, object]]:
    model = build_model()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, features, labels, cv=cv, scoring="f1")

    model.fit(features, labels)
    predictions = model.predict(features)

    metadata: dict[str, object] = {
        "model_name": "wellness_user_rf",
        "samples": int(len(features)),
        "at_risk_samples": int(labels.sum()),
        "not_at_risk_samples": int((labels == 0).sum()),
        "feature_names": list(features.columns),
        "cv_f1_scores": [round(float(score), 4) for score in cv_scores],
        "cv_f1_mean": round(float(cv_scores.mean()), 4),
        "cv_f1_std": round(float(cv_scores.std()), 4),
        "train_accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "classification_report": classification_report(
            labels,
            predictions,
            target_names=["Not at risk", "At risk"],
            output_dict=True,
            zero_division=0,
        ),
    }

    return model, metadata


def main() -> None:
    features, labels = load_dataset()
    model, metadata = train_model(features, labels)

    joblib.dump(model, USER_MODEL_PATH)
    META_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Samples: {metadata['samples']}")
    print(
        "Class balance: "
        f"{metadata['at_risk_samples']} at-risk / "
        f"{metadata['not_at_risk_samples']} not at-risk"
    )
    print(f"Cross-val F1: {metadata['cv_f1_mean']} +/- {metadata['cv_f1_std']}")
    print(f"Train accuracy: {metadata['train_accuracy']}")
    print(f"Saved model: {USER_MODEL_PATH}")
    print(f"Saved metadata: {META_PATH}")


if __name__ == "__main__":
    main()
