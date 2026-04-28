"""
train_from_survey.py
====================
Train a wellness risk model from real user survey exports (English + Turkish).

Label logic
-----------
The last question in both surveys is an overall mental well-being self-rating:
  English:  "Very poor" / "Poor" / "Neutral" / "Good" / "Very good"  (text)
  Turkish:  1 / 2 / 3 / 4 / 5                                        (numeric)

We convert to a 1-5 scale and then binarise:
  ≤ 2  →  at-risk   (label = 1)
  ≥ 3  →  not at-risk (label = 0)

Usage
-----
    cd backend
    python -m ml.train_from_survey

    # Override CSV paths via env vars if needed:
    EN_SURVEY_PATH=... TR_SURVEY_PATH=... python -m ml.train_from_survey

Outputs
-------
  ml/artifacts/wellness_user_rf.joblib    – trained RandomForestClassifier
  ml/artifacts/wellness_user_meta.json    – training metadata + CV scores
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score

# ── Paths ─────────────────────────────────────────────────────────────────────

ARTIFACT_DIR = pathlib.Path(__file__).resolve().parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_EN_PATH = (
    r"C:\Users\User\Downloads"
    r"\Student Mental Wellness Survey (Ответы) - Ответы на форму (1).csv"
)
_DEFAULT_TR_PATH = (
    r"C:\Users\User\Downloads"
    r"\Öğrenci Ruh Sağlığı ve İyi Oluş Anketi (Ответы) - Ответы на форму (1).csv"
)

EN_SURVEY_PATH = os.environ.get("EN_SURVEY_PATH", _DEFAULT_EN_PATH)
TR_SURVEY_PATH = os.environ.get("TR_SURVEY_PATH", _DEFAULT_TR_PATH)

# ── Column name maps ──────────────────────────────────────────────────────────

EN_COLS: dict[str, str] = {
    "sleep":         "On average, how many hours do you sleep each night?",
    "energy":        "How would you rate your energy level throughout the day?",
    "pressure":      "How often do you feel under academic pressure?",
    "motivation":    "How motivated do you feel to study or complete daily tasks?",
    "concentration": "How often do you find it difficult to concentrate?",
    "mood":          "How do you usually feel when you wake up?",
    "emotional":     "How often have you felt emotionally low recently?",
    "anxiety":       "How often do you feel anxious or worried?",
    "social":        "Do you feel supported by friends or family when you need it?",
    "financial":     "How much financial stress are you currently experiencing?",
    "wellbeing":     "Overall, how would you rate your mental well-being recently?",
}

TR_COLS: dict[str, str] = {
    "sleep":         "Ortalama olarak her gece kaç saat uyuyorsunuz?",
    "energy":        "Gün içindeki enerji seviyenizi nasıl değerlendirirsiniz?",
    "pressure":      "Kendinizi ne sıklıkla akademik baskı altında hissediyorsunuz?",
    "motivation":    "Ders çalışmaya veya günlük görevleri tamamlamaya ne kadar motive hissediyorsunuz?",
    "concentration": "Ne sıklıkla odaklanmakta veya konsantre olmakta zorlanırsınız?",
    "mood":          "Sabah uyandığınızda genellikle nasıl hissedersiniz?",
    "emotional":     "Son zamanlarda kendinizi ne sıklıkla duygusal olarak kötü hissediyorsunuz?",
    "anxiety":       "Kendinizi ne sıklıkla endişeli veya kaygılı hissedersiniz?",
    "social":        "İhtiyaç duyduğunuzda arkadaşlarınızdan veya ailenizden destek gördüğünüzü düşünüyor musunuz?",
    "financial":     "Şu anda ne kadar finansal stres yaşıyorsunuz?",
    "wellbeing":     "Genel olarak son zamanlarda ruh halinizi nasıl değerlendirirsiniz?",
}

# ── Feature order (must match ALL_FEATURES in ml/wellness/features.py) ────────

ALL_FEATURES: list[str] = [
    "sleep_duration",           # float  – estimated hours
    "academic_pressure",        # int 1-5
    "financial_stress",         # int 1-5
    "study_motivation",         # int 1-5
    "concentration_difficulty", # int 1-5
    "energy_level",             # int 1-5
    "morning_mood",             # int 1-5
    "emotional_low",            # int 1-5
    "anxiety_level",            # int 1-5
    "social_support",           # int 1-5
]

# ── Encoding maps (CSV-specific; handles English + Turkish) ───────────────────

# Sleep duration → float hours
# Note: CSVs use en-dash (–); we normalise to hyphen before lookup.
_SLEEP_MAP: dict[str, float] = {
    # English
    "less than 5 hours":  4.0,
    "5-6 hours":          5.5,
    "7-8 hours":          7.5,
    "more than 8 hours":  9.0,
    # Turkish
    "5 saatten az":       4.0,
    "5-6 saat":           5.5,
    "7-8 saat":           7.5,
    "8 saatten fazla":    9.0,
}

# Frequency text → 1-5 (used for academic_pressure, concentration, emotional_low, anxiety)
_FREQ_MAP: dict[str, int] = {
    # English
    "never": 1, "rarely": 2, "sometimes": 3, "often": 4,
    "always": 5, "constantly": 5,
    # Turkish
    "hiç": 1, "nadiren": 2, "bazen": 3, "sık sık": 4, "her zaman": 5,
}

# Morning mood → 1-5
_MOOD_MAP: dict[str, int] = {
    # English
    "very sad":           1,
    "sad":                2,
    "neutral":            3,
    "positive":           4,
    "energized":          5,
    # Turkish
    "çok olumsuz":        1,
    "olumsuz":            2,
    "nötr":               3,
    "olumlu":             4,
    "çok olumlu":         5,
}

# Social support → 1-5
# CSV uses "Not at all / Slightly / Moderately / Very / Extremely" (en)
# and "Hiç / Az / Orta düzeyde / Oldukça / Çok fazla" (tr).
_SOCIAL_MAP: dict[str, int] = {
    # English
    "not at all":   1,
    "slightly":     2,
    "moderately":   3,
    "very":         4,
    "extremely":    5,
    # Turkish
    "hiç":          1,
    "az":           2,
    "orta düzeyde": 3,
    "oldukça":      4,
    "çok fazla":    5,
}

# Well-being rating → 1-5 (English only; Turkish CSV stores numeric directly)
_WELLBEING_MAP: dict[str, int] = {
    "very poor": 1,
    "poor":      2,
    "neutral":   3,
    "good":      4,
    "very good": 5,
}

# Rows with self-rated well-being ≤ this threshold are labelled at-risk (1)
RISK_THRESHOLD: int = 2


# ── Helper ────────────────────────────────────────────────────────────────────

def _norm(val: object) -> str:
    """Lowercase + strip + replace en-dash with hyphen."""
    return str(val).strip().lower().replace("–", "-").replace("\u2013", "-")


def _lookup(val: object, mapping: dict, field: str = "") -> float:
    """
    Return float from mapping, or pass through if already numeric.
    Returns np.nan on failure.
    """
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        v = float(val)
        return v if not np.isnan(v) else np.nan
    key = _norm(val)
    if key not in mapping:
        return np.nan
    return float(mapping[key])


# ── Row processor ─────────────────────────────────────────────────────────────

def _process_row(row: pd.Series, col_map: dict[str, str]) -> dict | None:
    """
    Convert one CSV row → feature dict with 'label', or None if invalid.
    """
    try:
        sleep    = _lookup(row[col_map["sleep"]],         _SLEEP_MAP, "sleep")
        energy   = _lookup(row[col_map["energy"]],        {},         "energy")   # numeric
        pressure = _lookup(row[col_map["pressure"]],      _FREQ_MAP,  "pressure")
        motiv    = _lookup(row[col_map["motivation"]],    {},         "motiv")    # numeric
        conc     = _lookup(row[col_map["concentration"]], _FREQ_MAP,  "conc")
        mood     = _lookup(row[col_map["mood"]],          _MOOD_MAP,  "mood")
        emot     = _lookup(row[col_map["emotional"]],     _FREQ_MAP,  "emot")
        anx      = _lookup(row[col_map["anxiety"]],       _FREQ_MAP,  "anx")
        social   = _lookup(row[col_map["social"]],        _SOCIAL_MAP,"social")
        fin      = _lookup(row[col_map["financial"]],     {},         "fin")      # numeric

        wb_raw   = row[col_map["wellbeing"]]
        wb_score = _lookup(wb_raw, _WELLBEING_MAP, "wellbeing")

        features: dict[str, float] = {
            "sleep_duration":           sleep,
            "academic_pressure":        pressure,
            "financial_stress":         fin,
            "study_motivation":         motiv,
            "concentration_difficulty": conc,
            "energy_level":             energy,
            "morning_mood":             mood,
            "emotional_low":            emot,
            "anxiety_level":            anx,
            "social_support":           social,
            "label":                    float(1 if wb_score <= RISK_THRESHOLD else 0),
        }

        # Drop rows with any NaN
        if any(np.isnan(v) for v in features.values()):
            return None

        return features

    except (KeyError, ValueError, TypeError):
        return None


# ── CSV loader ────────────────────────────────────────────────────────────────

def load_csv(path: str, col_map: dict[str, str], label: str = "") -> list[dict]:
    """Load, process and return valid records from one survey CSV."""
    df = pd.read_csv(path)
    records = []
    skipped = 0
    for _, row in df.iterrows():
        result = _process_row(row, col_map)
        if result is not None:
            records.append(result)
        else:
            skipped += 1
    if label:
        print(f"  [{label}] {len(records)} valid rows, {skipped} skipped")
    return records


# ── Training ──────────────────────────────────────────────────────────────────

def train(records: list[dict]) -> tuple[RandomForestClassifier, dict]:
    """
    Train a RandomForest on the combined survey records.

    Returns
    -------
    (model, meta_dict)
    """
    df  = pd.DataFrame(records)
    X   = df[ALL_FEATURES]
    y   = df["label"].astype(int)

    print(f"\nDataset summary")
    print(f"  Total rows  : {len(df)}")
    print(f"  Not at risk : {(y == 0).sum()}  ({(y==0).mean()*100:.1f}%)")
    print(f"  At risk     : {(y == 1).sum()}  ({(y==1).mean()*100:.1f}%)")
    print(f"  Features    : {ALL_FEATURES}")

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    # ── Cross-validation ──────────────────────────────────────────────────────
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    cv_f1  = cross_val_score(clf, X, y, cv=cv, scoring="f1_weighted")
    cv_acc = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")

    print(f"\n5-Fold Cross-Validation")
    print(f"  Accuracy (weighted) : {cv_acc.mean():.4f} ± {cv_acc.std():.4f}")
    print(f"  F1       (weighted) : {cv_f1.mean():.4f}  ± {cv_f1.std():.4f}")

    # ── Final fit on full dataset ─────────────────────────────────────────────
    clf.fit(X, y)

    y_pred = clf.predict(X)
    print("\nFull-data classification report (training set):")
    print(classification_report(y, y_pred, target_names=["Not at risk", "At risk"]))

    print("Feature importances (ranked):")
    pairs = sorted(
        zip(ALL_FEATURES, clf.feature_importances_),
        key=lambda t: t[1],
        reverse=True,
    )
    for name, imp in pairs:
        bar = "#" * int(imp * 40)
        print(f"  {name:<28s} {imp:.4f}  {bar}")

    meta = {
        "cv_accuracy_mean": round(float(cv_acc.mean()), 4),
        "cv_accuracy_std":  round(float(cv_acc.std()),  4),
        "cv_f1_mean":       round(float(cv_f1.mean()),  4),
        "cv_f1_std":        round(float(cv_f1.std()),   4),
        "n_samples":        len(df),
        "n_at_risk":        int((y == 1).sum()),
        "n_not_at_risk":    int((y == 0).sum()),
        "features":         ALL_FEATURES,
        "risk_threshold":   RISK_THRESHOLD,
        "label_logic":      "well_being_score <= 2 → at-risk (1); else → not at-risk (0)",
        "sources":          ["English student wellness survey CSV",
                             "Turkish student wellness survey CSV"],
        "model_params": {
            "n_estimators":     300,
            "max_depth":        6,
            "min_samples_leaf": 2,
            "class_weight":     "balanced",
        },
    }

    return clf, meta


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  MindTrackAI – training from user survey data")
    print("=" * 60)

    print("\nLoading CSVs …")
    en_records = load_csv(EN_SURVEY_PATH, EN_COLS, label="English")
    tr_records = load_csv(TR_SURVEY_PATH, TR_COLS, label="Turkish")

    all_records = en_records + tr_records

    if not all_records:
        print("ERROR: no valid records found. Check CSV paths and column names.")
        sys.exit(1)

    clf, meta = train(all_records)

    # ── Save model ────────────────────────────────────────────────────────────
    model_path = ARTIFACT_DIR / "wellness_user_rf.joblib"
    meta_path  = ARTIFACT_DIR / "wellness_user_meta.json"

    joblib.dump(clf, model_path)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"  Model saved : {model_path}")
    print(f"  Meta  saved : {meta_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
