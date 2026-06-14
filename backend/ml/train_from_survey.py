"""
Train a wellness-risk model from the exported survey CSVs, augmented with
synthetic mock data for the minority "at-risk" class.

This script produces the primary 14-column model used by ``predict.py``:

- ``ml/artifacts/wellness_user_rf.joblib``
- ``ml/artifacts/wellness_user_meta.json``

Key choices:

* Sleep is one-hot encoded (5 columns).
* Hyperparameters are picked with ``RandomizedSearchCV`` using an
  honest custom CV where every train fold = real_train + ALL mock samples,
  and every test fold = real_test only. This means mock data improves the
  model without polluting the F1 estimate.
* The decision threshold is tuned on out-of-fold probabilities from real
  samples by maximising F1 along the precision-recall curve. The tuned
  threshold is persisted so ``predict.py`` can use it at inference time.

The exported survey files are expected at:

- ``ml/data/survey_en.csv``
- ``ml/data/survey_tr.csv``

The mock dataset is regenerated each run and written to
``ml/data/survey_mock.csv`` for auditability.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_recall_curve,
)
from sklearn.base import clone
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
)

from ml.mock_data import (
    FEATURE_CHOICES,
    generate_empirical_dataset,
    write_csv,
)
from ml.predict import ALL_FEATURES, USER_MODEL_PATH, _encode_survey

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
ARTIFACT_DIR = SCRIPT_DIR / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

EN_CSV = DATA_DIR / "survey_en.csv"
TR_CSV = DATA_DIR / "survey_tr.csv"
MOCK_CSV = DATA_DIR / "survey_mock.csv"
META_PATH = ARTIFACT_DIR / "wellness_user_meta.json"

EN_LABEL_MAP = {
    "very poor": 1,
    "poor": 1,
    "neutral": 0,
    "good": 0,
    "very good": 0,
}

PARAM_DISTRIBUTIONS = {
    "n_estimators": [200, 300, 400, 600, 800],
    "max_depth": [4, 5, 6, 8, 10, 12, None],
    "min_samples_leaf": [1, 2, 3, 5, 8],
    "min_samples_split": [2, 5, 10],
    "max_features": ["sqrt", "log2", 0.5, 0.7],
}
RANDOM_STATE = 42
N_SEARCH_ITERS = 40
CV_SPLITS = 5

# Mock-data volume. Skewed toward the minority "at-risk" class to balance
# the dataset; keeping not-at-risk mock smaller avoids drowning the real
# signal in synthetic samples.
N_MOCK_AT_RISK = 250
N_MOCK_NOT_AT_RISK = 150


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


def _encode_row_dict(raw: dict[str, object]) -> dict[str, float]:
    encoded = _encode_survey(raw)
    return {name: float(encoded[name]) for name in ALL_FEATURES}


def _english_label(value: object) -> int:
    return EN_LABEL_MAP.get(str(value or "").strip().lower(), 0)


def _turkish_label(value: object) -> int:
    try:
        return 1 if int(value) <= 2 else 0
    except (TypeError, ValueError):
        return 0


def _load_csv_raw(
    path: pathlib.Path, label_fn
) -> tuple[list[dict[str, str]], list[int]]:
    df = pd.read_csv(path)
    raw: list[dict[str, str]] = []
    labels: list[int] = []
    for _, record in df.iterrows():
        answers = _build_raw_answers(record)
        raw.append({k: str(v).strip() for k, v in answers.items()})
        labels.append(label_fn(record["wellbeing"]))
    return raw, labels


def load_real_dataset() -> tuple[pd.DataFrame, pd.Series, list[dict[str, str]]]:
    if not EN_CSV.exists():
        raise FileNotFoundError(f"Missing English survey export: {EN_CSV}")
    if not TR_CSV.exists():
        raise FileNotFoundError(f"Missing Turkish survey export: {TR_CSV}")

    en_raw, en_labels = _load_csv_raw(EN_CSV, _english_label)
    tr_raw, tr_labels = _load_csv_raw(TR_CSV, _turkish_label)
    raw_answers = en_raw + tr_raw
    label_list = en_labels + tr_labels

    encoded = [_encode_row_dict(row) for row in raw_answers]
    features = pd.DataFrame(encoded, columns=ALL_FEATURES)
    labels = pd.Series(label_list, name="at_risk")
    return features, labels, raw_answers


def build_mock_dataset(
    real_raw: list[dict[str, str]],
    real_labels: pd.Series,
    n_at_risk: int,
    n_not_at_risk: int,
    *,
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series, list[dict[str, str]]]:
    raw_rows, raw_labels = generate_empirical_dataset(
        real_raw,
        real_labels.tolist(),
        n_at_risk,
        n_not_at_risk,
        random_state=random_state,
    )
    encoded_rows = [_encode_row_dict(row) for row in raw_rows]
    features = pd.DataFrame(encoded_rows, columns=ALL_FEATURES)
    labels = pd.Series(raw_labels, name="at_risk")
    return features, labels, raw_rows


def base_estimator() -> RandomForestClassifier:
    return RandomForestClassifier(
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=1,
    )


def real_mock_cv(
    n_real: int,
    real_labels: pd.Series,
    n_mock: int,
    n_splits: int,
    random_state: int,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """
    Yield (train_indices, test_indices) for the combined real+mock dataset
    in which:

    * the combined arrays are laid out as ``[real_rows..., mock_rows...]``
    * every train fold = real_train + ALL mock samples
    * every test fold = real_test only

    This makes the CV F1 honest: synthetic samples never appear in the
    held-out split that the score is computed on.
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    mock_indices = np.arange(n_real, n_real + n_mock)
    real_index_array = np.arange(n_real)
    for train_real, test_real in skf.split(real_index_array, real_labels):
        train_combined = np.concatenate([train_real, mock_indices])
        yield train_combined, test_real


def tune_threshold(y_true: np.ndarray, y_proba: np.ndarray) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    precision = precision[:-1]
    recall = recall[:-1]
    denom = precision + recall
    f1_curve = np.where(denom > 0, 2 * precision * recall / np.maximum(denom, 1e-12), 0.0)
    if f1_curve.size == 0:
        return 0.5, 0.0
    best_idx = int(np.argmax(f1_curve))
    return float(thresholds[best_idx]), float(f1_curve[best_idx])


def train_model(
    real_features: pd.DataFrame,
    real_labels: pd.Series,
    mock_features: pd.DataFrame,
    mock_labels: pd.Series,
) -> tuple[RandomForestClassifier, dict[str, object]]:
    n_real = len(real_features)
    n_mock = len(mock_features)

    combined_features = pd.concat([real_features, mock_features], ignore_index=True)
    combined_labels = pd.concat([real_labels, mock_labels], ignore_index=True)

    cv_iter = list(
        real_mock_cv(
            n_real=n_real,
            real_labels=real_labels,
            n_mock=n_mock,
            n_splits=CV_SPLITS,
            random_state=RANDOM_STATE,
        )
    )

    search = RandomizedSearchCV(
        estimator=base_estimator(),
        param_distributions=PARAM_DISTRIBUTIONS,
        n_iter=N_SEARCH_ITERS,
        scoring="f1",
        cv=cv_iter,
        random_state=RANDOM_STATE,
        n_jobs=1,
        refit=True,
    )
    search.fit(combined_features, combined_labels)
    model = search.best_estimator_
    search_f1 = float(search.best_score_)

    # Manual OOF probabilities: train on (real_train + all mock), predict
    # on real_test only. Each real sample appears in exactly one real_test
    # fold so we end up with one probability per real sample.
    real_oof_proba = np.zeros(n_real, dtype=float)
    for train_idx, test_idx in cv_iter:
        fold_model = clone(model)
        fold_model.fit(
            combined_features.iloc[train_idx],
            combined_labels.iloc[train_idx],
        )
        fold_proba = fold_model.predict_proba(combined_features.iloc[test_idx])[:, 1]
        real_oof_proba[test_idx] = fold_proba
    y_real = real_labels.to_numpy()

    oof_pred_default = (real_oof_proba >= 0.5).astype(int)
    oof_f1_default = float(f1_score(y_real, oof_pred_default, zero_division=0))

    best_threshold, oof_f1_tuned = tune_threshold(y_real, real_oof_proba)
    oof_pred_tuned = (real_oof_proba >= best_threshold).astype(int)

    train_pred = model.predict(combined_features)
    train_acc = float(accuracy_score(combined_labels, train_pred))

    metadata: dict[str, object] = {
        "model_name": "wellness_user_rf",
        "real_samples": int(n_real),
        "mock_samples": int(n_mock),
        "samples": int(n_real + n_mock),
        "at_risk_samples": int(real_labels.sum()),
        "not_at_risk_samples": int((real_labels == 0).sum()),
        "mock_at_risk_samples": int(mock_labels.sum()),
        "mock_not_at_risk_samples": int((mock_labels == 0).sum()),
        "feature_names": list(combined_features.columns),
        "best_params": {k: (None if v is None else v) for k, v in search.best_params_.items()},
        "search_cv_f1_mean": round(search_f1, 4),
        "oof_f1_at_0_5": round(oof_f1_default, 4),
        "oof_f1_at_optimal": round(oof_f1_tuned, 4),
        "optimal_threshold": round(best_threshold, 4),
        "train_accuracy": round(train_acc, 4),
        "classification_report_oof_tuned": classification_report(
            y_real,
            oof_pred_tuned,
            target_names=["Not at risk", "At risk"],
            output_dict=True,
            zero_division=0,
        ),
        "cv_strategy": (
            "StratifiedKFold over real samples only; each train fold "
            "augmented with all mock samples, test fold is real-only."
        ),
    }
    return model, metadata


def main() -> None:
    real_features, real_labels, real_raw = load_real_dataset()
    mock_features, mock_labels, mock_raw = build_mock_dataset(
        real_raw,
        real_labels,
        N_MOCK_AT_RISK,
        N_MOCK_NOT_AT_RISK,
        random_state=RANDOM_STATE,
    )

    write_csv(MOCK_CSV, mock_raw, mock_labels.tolist())

    model, metadata = train_model(real_features, real_labels, mock_features, mock_labels)

    joblib.dump(model, USER_MODEL_PATH)
    META_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Real samples: {metadata['real_samples']} "
          f"({metadata['at_risk_samples']} at-risk / "
          f"{metadata['not_at_risk_samples']} not at-risk)")
    print(f"Mock samples: {metadata['mock_samples']} "
          f"({metadata['mock_at_risk_samples']} at-risk / "
          f"{metadata['mock_not_at_risk_samples']} not at-risk)")
    print(f"Best params: {metadata['best_params']}")
    print(f"Search CV F1 (real-test folds): {metadata['search_cv_f1_mean']}")
    print(f"OOF F1 @ 0.5 (real samples):    {metadata['oof_f1_at_0_5']}")
    print(
        f"OOF F1 @ tuned threshold "
        f"({metadata['optimal_threshold']}): {metadata['oof_f1_at_optimal']}"
    )
    print(f"Train accuracy (real + mock):   {metadata['train_accuracy']}")
    print(f"Saved model:    {USER_MODEL_PATH}")
    print(f"Saved metadata: {META_PATH}")
    print(f"Saved mock CSV: {MOCK_CSV}")


if __name__ == "__main__":
    main()
