"""
WellnessScorer – predict a wellness risk level using a Random Forest
trained on Kaggle-compatible base features.

This module can:
  1. Train a new RF model on synthetic / Kaggle-mapped data.
  2. Load a previously saved model from disk.
  3. Predict a wellness category from encoded base-model features.

Output categories (NOT medical diagnoses):
    "Low risk"      – the student appears to be doing well
    "Moderate risk" – some indicators suggest attention may be helpful
    "High risk"     – multiple indicators suggest the student may benefit
                      from professional wellness support

Internally the RF outputs a probability of the positive (at-risk) class
and we map it to the three categories above with configurable thresholds.
"""

from __future__ import annotations

import pathlib
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from .features import BASE_MODEL_FEATURES

# ── Defaults ──────────────────────────────────────────────────────────────────

_DEFAULT_ARTIFACT_DIR = pathlib.Path(__file__).resolve().parent.parent / "artifacts"

RISK_THRESHOLDS = {
    "low":  0.35,   # probability < 0.35  →  "Low risk"
    "high": 0.65,   # probability ≥ 0.65  →  "High risk"
    #                 in between           →  "Moderate risk"
}

WELLNESS_LABELS = {
    0: "Low risk",
    1: "Moderate risk",
    2: "High risk",
}


class WellnessScorer:
    """
    Wraps a RandomForestClassifier for wellness-risk prediction.

    Parameters
    ----------
    model_path : str or Path, optional
        Path to a saved ``.joblib`` model. If provided the model is loaded
        immediately.  Otherwise call :meth:`train` first.
    """

    def __init__(self, model_path: Optional[str | pathlib.Path] = None):
        self.model: Optional[RandomForestClassifier] = None
        self.feature_names: list[str] = BASE_MODEL_FEATURES
        self._artifact_dir = _DEFAULT_ARTIFACT_DIR
        self._artifact_dir.mkdir(parents=True, exist_ok=True)

        if model_path is not None:
            self.load(model_path)

    # ── Training ──────────────────────────────────────────────────────────────

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        *,
        test_size: float = 0.20,
        random_state: int = 42,
        n_estimators: int = 200,
        max_depth: int = 15,
        verbose: bool = True,
    ) -> dict:
        """
        Train a new Random Forest on Kaggle-compatible features.

        Parameters
        ----------
        X : DataFrame
            Must contain columns listed in ``BASE_MODEL_FEATURES``.
        y : Series
            Binary target (0 / 1).
        test_size, random_state, n_estimators, max_depth
            Standard sklearn hyper-parameters.
        verbose : bool
            Print evaluation metrics.

        Returns
        -------
        dict
            ``{"accuracy": float, "report": str}``
        """
        # Ensure correct column order
        X = X[self.feature_names].copy()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=5,
            random_state=random_state,
            n_jobs=-1,
        )
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(
            y_test, y_pred, target_names=["Low risk", "At risk"]
        )

        if verbose:
            print(f"Accuracy: {acc:.4f}\n")
            print("Classification Report:")
            print(report)
            print("Feature importances:")
            for name, imp in sorted(
                zip(self.feature_names, self.model.feature_importances_),
                key=lambda x: x[1],
                reverse=True,
            ):
                print(f"  {name:<30s} {imp:.4f}")

        return {"accuracy": acc, "report": report}

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, base_features: dict[str, int | float]) -> dict:
        """
        Predict wellness risk from encoded base-model features.

        Parameters
        ----------
        base_features : dict
            Keys = ``BASE_MODEL_FEATURES``, values = encoded numerics.

        Returns
        -------
        dict
            ``{"risk_label": str, "risk_probability": float,
               "risk_level": int}``

        Example
        -------
        >>> scorer = WellnessScorer("artifacts/wellness_base_rf.joblib")
        >>> scorer.predict({
        ...     "sleep_duration": 7.5,
        ...     "academic_pressure": 4,
        ...     "financial_stress": 3,
        ...     "study_motivation": 4,
        ...     "concentration_difficulty": 3,
        ... })
        {'risk_label': 'Moderate risk', 'risk_probability': 0.42, 'risk_level': 1}
        """
        if self.model is None:
            raise RuntimeError("No model loaded. Call train() or load() first.")

        row = pd.DataFrame([base_features], columns=self.feature_names)
        prob = self.model.predict_proba(row)[0]

        # prob[1] = probability of the at-risk class
        risk_prob = float(prob[1]) if len(prob) > 1 else float(prob[0])

        if risk_prob < RISK_THRESHOLDS["low"]:
            risk_level = 0
        elif risk_prob >= RISK_THRESHOLDS["high"]:
            risk_level = 2
        else:
            risk_level = 1

        return {
            "risk_label":       WELLNESS_LABELS[risk_level],
            "risk_probability": round(risk_prob, 4),
            "risk_level":       risk_level,
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: Optional[str | pathlib.Path] = None) -> pathlib.Path:
        """Save the trained model to disk."""
        if self.model is None:
            raise RuntimeError("No model to save.")
        path = pathlib.Path(path) if path else self._artifact_dir / "wellness_base_rf.joblib"
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)
        return path

    def load(self, path: str | pathlib.Path) -> None:
        """Load a model from disk."""
        self.model = joblib.load(path)
