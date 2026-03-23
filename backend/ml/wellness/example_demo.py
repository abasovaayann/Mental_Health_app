"""
example_demo.py – End-to-end demo of the wellness module.

Shows:
  1. Encoding a raw survey
  2. Feature splitting
  3. Building a DB-ready record
  4. Loading the base model & predicting
  5. Simulating future retraining with synthetic data
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ml.wellness.encoders import encode_answer, encode_sleep_duration, encode_survey
from ml.wellness.features import split_features, BASE_MODEL_FEATURES, ADDITIONAL_FEATURES, ALL_FEATURES
from ml.wellness.process_survey import process_survey
from ml.wellness.scorer import WellnessScorer
from ml.wellness.retrainer import WellnessRetrainer, MIN_SAMPLES


def _pprint(label: str, obj: object) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")
    print(json.dumps(obj, indent=2, default=str))


def main() -> None:
    # ── Sample raw survey (exactly as stored in DB) ───────────────────────
    raw_answers = {
        "sleep_duration":            "4",                        # slider value
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

    # ── 1. Individual encoding examples ───────────────────────────────────
    print("=== Individual encoding examples ===")
    print(f"  encode_answer('academic_pressure', 'Often')       → {encode_answer('academic_pressure', 'Often')}")
    print(f"  encode_answer('energy_level', 'Very low')         → {encode_answer('energy_level', 'Very low')}")
    print(f"  encode_sleep_duration('4')                        → {encode_sleep_duration('4')}")
    print(f"  encode_sleep_duration('Less than 5 hours')        → {encode_sleep_duration('Less than 5 hours')}")

    # ── 2. Full survey encoding ───────────────────────────────────────────
    encoded = encode_survey(raw_answers)
    _pprint("Encoded survey", encoded)

    # ── 3. Feature split ──────────────────────────────────────────────────
    split = split_features(encoded)
    _pprint("Base model features (Kaggle-compatible)", split["base_features"])
    _pprint("Additional custom features (for future)", split["additional_features"])

    # ── 4. DB-ready record (without model prediction) ─────────────────────
    record = process_survey(raw_answers, user_id=42)
    _pprint("DB-ready record (no model loaded)", record)

    # ── 5. Load base model and predict ────────────────────────────────────
    model_path = pathlib.Path(__file__).resolve().parent.parent / "artifacts" / "wellness_base_rf.joblib"
    if model_path.exists():
        scorer = WellnessScorer(model_path)
        record_with_pred = process_survey(raw_answers, user_id=42, scorer=scorer)
        _pprint("DB-ready record (with wellness prediction)", record_with_pred)
    else:
        print(f"\n⚠ Base model not found at {model_path}.")
        print("  Run  python -m ml.wellness.train_base_model  first.\n")

    # ── 6. Simulate future retraining ─────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  Simulating future retraining ({MIN_SAMPLES} synthetic records)")
    print(f"{'=' * 60}")

    rng = np.random.default_rng(42)
    synthetic_records = []
    for _ in range(MIN_SAMPLES):
        rec = {feat: int(rng.integers(1, 6)) for feat in ALL_FEATURES}
        rec["sleep_duration"] = float(rng.choice([3.5, 4.5, 5.5, 6.0, 7.5, 9.0]))
        # Synthetic label: higher pressure + lower motivation → more at-risk
        risk_score = (
            rec["academic_pressure"]
            + rec["financial_stress"]
            + rec["anxiety_level"]
            - rec["study_motivation"]
            - rec["social_support"]
        )
        rec["label"] = int(risk_score > 2)
        synthetic_records.append(rec)

    retrainer = WellnessRetrainer()
    print(f"  Ready to retrain? {retrainer.is_ready(len(synthetic_records))}")

    result = retrainer.retrain(synthetic_records, verbose=True)
    _pprint("Retraining result", {
        "accuracy":      result["accuracy"],
        "model_path":    result["model_path"],
        "trained_at":    result["trained_at"],
        "n_samples":     result["n_samples"],
        "features_used": result["features_used"],
    })

    # Predict with the retrained full model
    full_pred = retrainer.predict(encoded)
    _pprint("Full-model prediction (retrained)", full_pred)

    print("\n✓ Demo complete.\n")


if __name__ == "__main__":
    main()
