"""
WellnessRetrainer – scaffolding for future model retraining using **all**
10 custom survey features once enough user-generated data has been collected.

Phase 1 (now):
    Only the 5 Kaggle-compatible features drive the live model.

Phase 2 (future):
    When ``MIN_SAMPLES`` user records exist the system can retrain a richer
    model that includes the 5 additional custom features as well.

This module provides:
    • ``build_training_dataframe``  – assemble features + labels from DB rows
    • ``WellnessRetrainer.retrain`` – fit, evaluate, and save a new model
"""

from __future__ import annotations

import pathlib
from datetime import datetime
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from .features import ALL_FEATURES, BASE_MODEL_FEATURES

# ── Config ────────────────────────────────────────────────────────────────────

MIN_SAMPLES: int = 200
"""Minimum number of labelled user records required before retraining."""

_DEFAULT_ARTIFACT_DIR = pathlib.Path(__file__).resolve().parent.parent / "artifacts"


def build_training_dataframe(
    records: list[dict],
    *,
    feature_columns: Optional[list[str]] = None,
    label_column: str = "label",
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Convert a list of DB-style dicts into (X, y) for sklearn.

    Parameters
    ----------
    records : list[dict]
        Each dict should contain all encoded feature columns plus
        a ``label_column`` key (0 / 1).
    feature_columns : list[str], optional
        Defaults to ``ALL_FEATURES``.
    label_column : str
        Key that holds the binary target.

    Returns
    -------
    (X, y) : tuple[DataFrame, Series]
    """
    feature_columns = feature_columns or ALL_FEATURES
    df = pd.DataFrame(records)
    X = df[feature_columns]
    y = df[label_column]
    return X, y


class WellnessRetrainer:
    """
    Manages retraining of a full-feature wellness model.

    Parameters
    ----------
    artifact_dir : str or Path, optional
        Directory for saving model files.
    """

    def __init__(self, artifact_dir: Optional[str | pathlib.Path] = None):
        self._artifact_dir = pathlib.Path(artifact_dir) if artifact_dir else _DEFAULT_ARTIFACT_DIR
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        self.model: Optional[RandomForestClassifier] = None

    # ── Readiness check ───────────────────────────────────────────────────────

    @staticmethod
    def is_ready(n_samples: int) -> bool:
        """Return ``True`` if we have enough data to retrain."""
        return n_samples >= MIN_SAMPLES

    # ── Retraining ────────────────────────────────────────────────────────────

    def retrain(
        self,
        records: list[dict],
        *,
        feature_columns: Optional[list[str]] = None,
        label_column: str = "label",
        test_size: float = 0.20,
        n_estimators: int = 300,
        max_depth: int = 18,
        random_state: int = 42,
        verbose: bool = True,
    ) -> dict:
        """
        Retrain a Random Forest on all custom features.

        Parameters
        ----------
        records : list[dict]
            User-generated encoded survey records **with labels**.
        feature_columns : list[str], optional
            Defaults to all 10 survey features.
        label_column : str
            Binary target column name in each record.
        verbose : bool
            Print metrics.

        Returns
        -------
        dict
            ``{"accuracy": float, "report": str, "model_path": str,
               "trained_at": str, "n_samples": int, "features_used": list}``
        """
        feature_columns = feature_columns or ALL_FEATURES

        if not self.is_ready(len(records)):
            raise ValueError(
                f"Not enough data to retrain. Need {MIN_SAMPLES}, "
                f"got {len(records)}."
            )

        X, y = build_training_dataframe(
            records,
            feature_columns=feature_columns,
            label_column=label_column,
        )

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y,
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
            print(f"[Retrain] Samples: {len(records)}  Features: {len(feature_columns)}")
            print(f"[Retrain] Accuracy: {acc:.4f}\n")
            print(report)

        # Save with timestamp
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_path = self._artifact_dir / f"wellness_full_rf_{ts}.joblib"
        joblib.dump(self.model, model_path)

        # Also save a "latest" symlink-style copy
        latest_path = self._artifact_dir / "wellness_full_rf_latest.joblib"
        joblib.dump(self.model, latest_path)

        if verbose:
            print(f"Model saved to: {model_path}")
            print(f"Latest copy:    {latest_path}")

        return {
            "accuracy":       acc,
            "report":         report,
            "model_path":     str(model_path),
            "trained_at":     ts,
            "n_samples":      len(records),
            "features_used":  feature_columns,
        }

    # ── Prediction with full model ────────────────────────────────────────────

    def predict(
        self,
        encoded_survey: dict[str, int | float],
        feature_columns: Optional[list[str]] = None,
    ) -> dict:
        """
        Predict using the retrained full-feature model.

        Returns the same structure as ``WellnessScorer.predict``.
        """
        if self.model is None:
            raise RuntimeError("No retrained model loaded.")

        feature_columns = feature_columns or ALL_FEATURES
        row = pd.DataFrame([encoded_survey], columns=feature_columns)
        prob = self.model.predict_proba(row)[0]
        risk_prob = float(prob[1]) if len(prob) > 1 else float(prob[0])

        if risk_prob < 0.35:
            level, label = 0, "Low risk"
        elif risk_prob >= 0.65:
            level, label = 2, "High risk"
        else:
            level, label = 1, "Moderate risk"

        return {
            "risk_label":       label,
            "risk_probability": round(risk_prob, 4),
            "risk_level":       level,
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def load(self, path: str | pathlib.Path) -> None:
        """Load a retrained model from disk."""
        self.model = joblib.load(path)
