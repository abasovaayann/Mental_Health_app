

from __future__ import annotations

import os
import pathlib
import sys

import numpy as np
import pandas as pd

# Make sure the backend package is importable
BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ml.wellness.scorer import WellnessScorer
from ml.wellness.features import BASE_MODEL_FEATURES

# ── Locate dataset ───────────────────────────────────────────────────────────

KAGGLE_PATH = pathlib.Path(
    "/kaggle/input/student-depression-dataset/student_depression_dataset.csv"
)
LOCAL_PATH = pathlib.Path(
    os.path.expanduser(
        "~/.cache/kagglehub/datasets/hopesb/"
        "student-depression-dataset/versions/1/"
        "Student Depression Dataset.csv"
    )
)
CSV_PATH = KAGGLE_PATH if KAGGLE_PATH.exists() else LOCAL_PATH

# ── Kaggle column → our feature name ─────────────────────────────────────────
#
# Kaggle dataset columns (after drop):
#   Sleep Duration, Academic Pressure, Financial Stress,
#   Study Satisfaction, CGPA, Work/Study Hours, ...
#
# Our 5 base features and how they map:
#   sleep_duration           ← Sleep Duration (encoded to hours)
#   academic_pressure        ← Academic Pressure (already 1-5 float)
#   financial_stress         ← Financial Stress  (already 1-5 float)
#   study_motivation         ← Study Satisfaction (proxy, 1-5 float)
#   concentration_difficulty ← derive from Work/Study Hours (scaled 1-5)

SLEEP_MAP = {
    "Less than 5 hours": 4.0,
    "5-6 hours":         5.5,
    "7-8 hours":         7.5,
    "More than 8 hours": 9.0,
    "Others":            6.0,   
}


def _prepare_kaggle_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Map Kaggle dataset columns to our 5 base features + target.
    """
    out = pd.DataFrame()

    # sleep_duration  (text → hours)
    out["sleep_duration"] = df["Sleep Duration"].map(SLEEP_MAP)
    out["sleep_duration"].fillna(6.0, inplace=True)

    # academic_pressure  (already numeric 1-5)
    out["academic_pressure"] = df["Academic Pressure"].fillna(3)

    # financial_stress  (already numeric 1-5)
    out["financial_stress"] = df["Financial Stress"].fillna(3)

    # study_motivation ← Study Satisfaction (1-5)
    out["study_motivation"] = df["Study Satisfaction"].fillna(3)

    # concentration_difficulty ← Work/Study Hours scaled to 1-5
    # Higher work/study hours → more concentration demand → higher difficulty
    wsh = df["Work/Study Hours"].fillna(6)
    out["concentration_difficulty"] = np.clip(
        np.round(1 + (wsh - wsh.min()) / (wsh.max() - wsh.min() + 1e-9) * 4),
        1, 5,
    ).astype(int)

    target = df["Depression"]
    return out, target


def main() -> None:
    print(f"Loading Kaggle data from: {CSV_PATH}\n")
    raw = pd.read_csv(CSV_PATH)

    # Drop rows without target
    raw.dropna(subset=["Depression"], inplace=True)

    X, y = _prepare_kaggle_data(raw)
    print(f"Prepared {len(X)} samples with features: {BASE_MODEL_FEATURES}\n")

    scorer = WellnessScorer()
    results = scorer.train(X, y, verbose=True)

    model_path = scorer.save()
    print(f"\nModel saved to: {model_path}")

    # Quick sanity check
    sample = {
        "sleep_duration": 5.5,
        "academic_pressure": 4,
        "financial_stress": 3,
        "study_motivation": 2,
        "concentration_difficulty": 4,
    }
    pred = scorer.predict(sample)
    print(f"\nSample prediction: {pred}")


if __name__ == "__main__":
    main()
