"""
Train a wellness-risk classifier on real student survey data (EN + TR).

Uses all 10 survey features. Compares four algorithms via 5-fold CV and
trains the best performer on the full dataset.

Saves artifacts/wellness_model.pkl  (Pipeline: scaler + classifier)
       artifacts/model_columns.pkl  (ordered feature column list)
"""

from __future__ import annotations

import pathlib
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = pathlib.Path(__file__).resolve().parent
DATA_DIR     = SCRIPT_DIR / "data"
ARTIFACT_DIR = SCRIPT_DIR / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

EN_CSV = DATA_DIR / "survey_en.csv"
TR_CSV = DATA_DIR / "survey_tr.csv"

# ── Encoding maps ──────────────────────────────────────────────────────────────

FREQ_MAP = {
    "never": 1, "rarely": 2, "sometimes": 3, "often": 4, "always": 5,
}

MORNING_MAP = {
    # English CSV values
    "very sad": 1, "sad": 2, "neutral": 3, "positive": 4, "energized": 5,
    # Turkish CSV values (standardised to English when writing the file)
    "very negative": 1, "negative": 2, "very positive": 5,
}

SUPPORT_MAP = {
    "not at all": 1, "slightly": 2, "moderately": 3,
    "very": 4, "extremely": 5,
}

SLEEP_NORM = {
    "less than 5 hours": "Less than 5 hours",
    "5-6 hours":         "5-6 hours",
    "7-8 hours":         "7-8 hours",
    "more than 8 hours": "More than 8 hours",
}

SLEEP_COLS = [
    "Sleep Duration_5-6 hours",
    "Sleep Duration_7-8 hours",
    "Sleep Duration_Less than 5 hours",
    "Sleep Duration_More than 8 hours",
    "Sleep Duration_Others",
]

# Ordered feature columns – must match predict.py exactly
FEATURE_COLS = [
    "Academic Pressure",
    "Study Satisfaction",
    "Work/Study Hours",
    "Financial Stress",
    "Energy Level",
    "Morning Mood",
    "Emotional Low",
    "Anxiety Level",
    "Social Support",
] + SLEEP_COLS

# ── Label maps ─────────────────────────────────────────────────────────────────

EN_LABEL_MAP = {
    "very poor": 1, "poor": 1,
    "neutral":   0, "good": 0, "very good": 0,
}

def tr_label(val: object) -> int:
    try:
        return 1 if int(val) <= 2 else 0
    except (ValueError, TypeError):
        return 0


# ── Row builder ────────────────────────────────────────────────────────────────

def build_row(sleep, academic, motivation, concentration, financial,
              energy, morning_mood, emotional_low, anxiety, social_support) -> dict:
    ap  = FREQ_MAP.get(str(academic).strip().lower(), 3)
    sm  = int(motivation) if str(motivation).isdigit() else FREQ_MAP.get(str(motivation).strip().lower(), 3)
    cd  = FREQ_MAP.get(str(concentration).strip().lower(), 3)
    fs  = int(financial) if str(financial).isdigit() else FREQ_MAP.get(str(financial).strip().lower(), 3)
    el  = int(energy) if str(energy).isdigit() else FREQ_MAP.get(str(energy).strip().lower(), 3)
    mm  = MORNING_MAP.get(str(morning_mood).strip().lower(), 3)
    emo = FREQ_MAP.get(str(emotional_low).strip().lower(), 3)
    anx = FREQ_MAP.get(str(anxiety).strip().lower(), 3)
    ss  = SUPPORT_MAP.get(str(social_support).strip().lower(), 3)

    sleep_cat = SLEEP_NORM.get(str(sleep).strip().lower(), "Others")
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
    for col in SLEEP_COLS:
        row[col] = 1 if sleep_cat == col.replace("Sleep Duration_", "") else 0
    return row


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_english(path: pathlib.Path) -> tuple[list[dict], list[int]]:
    df = pd.read_csv(path)
    rows, labels = [], []
    for _, r in df.iterrows():
        rows.append(build_row(
            r.sleep, r.academic_pressure, r.study_motivation, r.concentration,
            r.financial_stress, r.energy, r.morning_mood, r.emotional_low,
            r.anxiety, r.social_support,
        ))
        labels.append(EN_LABEL_MAP.get(str(r.wellbeing).strip().lower(), 0))
    return rows, labels


def load_turkish(path: pathlib.Path) -> tuple[list[dict], list[int]]:
    df = pd.read_csv(path)
    rows, labels = [], []
    for _, r in df.iterrows():
        rows.append(build_row(
            r.sleep, r.academic_pressure, r.study_motivation, r.concentration,
            r.financial_stress, r.energy, r.morning_mood, r.emotional_low,
            r.anxiety, r.social_support,
        ))
        labels.append(tr_label(r.wellbeing))
    return rows, labels


# ── Algorithm candidates ───────────────────────────────────────────────────────

def make_candidates() -> dict[str, Pipeline]:
    return {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=0.5, solver="lbfgs", max_iter=1000,
                class_weight="balanced", random_state=42,
            )),
        ]),
        "SVM (RBF)": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(
                kernel="rbf", C=1.0, gamma="scale", probability=True,
                class_weight="balanced", random_state=42,
            )),
        ]),
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=200, max_depth=4, min_samples_leaf=3,
                class_weight="balanced", random_state=42, n_jobs=-1,
            )),
        ]),
        "Gradient Boosting": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=80, max_depth=2, learning_rate=0.1,
                random_state=42,
            )),
        ]),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    en_rows, en_labels = load_english(EN_CSV)
    tr_rows, tr_labels = load_turkish(TR_CSV)

    X = pd.DataFrame(en_rows + tr_rows, columns=FEATURE_COLS)
    y = pd.Series(en_labels + tr_labels, name="at_risk")

    print(f"Samples     : {len(X)}  ({int(y.sum())} at-risk / {int((y==0).sum())} not at-risk)")
    print(f"Features    : {len(X.columns)}  {list(X.columns)}\n")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    candidates = make_candidates()

    # ── Algorithm comparison ──────────────────────────────────────────────────
    print("=== Algorithm comparison (5-fold CV) ===")
    best_name, best_score, best_pipeline = "", 0.0, None
    for name, pipeline in candidates.items():
        scores = cross_val_score(pipeline, X, y, cv=cv, scoring="f1")
        mean, std = scores.mean(), scores.std()
        marker = ""
        if mean > best_score:
            best_score, best_name, best_pipeline = mean, name, pipeline
            marker = "  <-- best"
        print(f"  {name:<22s}  F1 = {mean:.4f} +/- {std:.4f}{marker}")

    print(f"\nWinner: {best_name}  (F1 = {best_score:.4f})\n")

    # ── Train winner on full dataset ──────────────────────────────────────────
    best_pipeline.fit(X, y)
    y_pred = best_pipeline.predict(X)

    print(f"Train accuracy : {accuracy_score(y, y_pred):.4f}")
    print("\nClassification report (full dataset — informational only):")
    print(classification_report(y, y_pred, target_names=["Not at risk", "At risk"]))

    # Feature importance (RF only; skip for others)
    clf = best_pipeline.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        print("Feature importances:")
        for feat, imp in sorted(zip(FEATURE_COLS, clf.feature_importances_),
                                 key=lambda x: x[1], reverse=True):
            print(f"  {feat:<35s} {imp:.4f}")

    # ── Save ──────────────────────────────────────────────────────────────────
    joblib.dump(best_pipeline,     ARTIFACT_DIR / "wellness_model.pkl")
    joblib.dump(X.columns.tolist(), ARTIFACT_DIR / "model_columns.pkl")

    print(f"\nSaved: artifacts/wellness_model.pkl  ({best_name})")
    print("Saved: artifacts/model_columns.pkl")
    print("Done.")


if __name__ == "__main__":
    main()
