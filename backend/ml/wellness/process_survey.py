"""
process_survey – end-to-end helper that takes raw survey answers,
encodes them, splits features, produces a DB-ready record, and
optionally scores wellness risk with the base RF model.

This is the single entry-point the API route layer should call.
"""

from __future__ import annotations

import pathlib
from typing import Optional

from .encoders import encode_survey
from .features import split_features, BASE_MODEL_FEATURES, ADDITIONAL_FEATURES
from .scorer import WellnessScorer

_ARTIFACT_DIR = pathlib.Path(__file__).resolve().parent.parent / "artifacts"


def process_survey(
    raw_answers: dict[str, str],
    user_id: int,
    *,
    scorer: Optional[WellnessScorer] = None,
    model_path: Optional[str | pathlib.Path] = None,
) -> dict:
    """
    Full pipeline: encode → split → score → build DB record.

    Parameters
    ----------
    raw_answers : dict[str, str]
        The 10 survey fields exactly as stored in the database
        (text values).
    user_id : int
        Current user's ID.
    scorer : WellnessScorer, optional
        A pre-loaded scorer instance. If ``None`` and *model_path* is
        given, a new scorer is created automatically.
    model_path : str or Path, optional
        Fallback model file. If neither *scorer* nor *model_path* is
        given, the wellness prediction step is skipped.

    Returns
    -------
    dict
        Database-ready record::

            {
                "user_id": 42,
                "raw_answers": {<original text answers>},
                "encoded_answers": {<all 10 fields, numeric>},
                "base_features": {<5 Kaggle-compatible features>},
                "additional_features": {<5 custom features>},
                "wellness_prediction": {   # or None
                    "risk_label": "Moderate risk",
                    "risk_probability": 0.48,
                    "risk_level": 1,
                },
            }

    Example
    -------
    >>> record = process_survey(
    ...     raw_answers={
    ...         "sleep_duration": "4",
    ...         "energy_level": "Moderate",
    ...         "academic_pressure": "Often",
    ...         "study_motivation": "Motivated",
    ...         "concentration_difficulty": "Moderately difficult",
    ...         "morning_mood": "Neutral",
    ...         "emotional_low": "Sometimes",
    ...         "anxiety_level": "Sometimes",
    ...         "social_support": "Moderately",
    ...         "financial_stress": "Moderate",
    ...     },
    ...     user_id=42,
    ... )
    >>> sorted(record["base_features"].keys())
    ['academic_pressure', 'concentration_difficulty', 'financial_stress', 'sleep_duration', 'study_motivation']
    """
    # 1. Encode
    encoded = encode_survey(raw_answers)

    # 2. Split
    split = split_features(encoded)

    # 3. Score (optional)
    prediction = None
    if scorer is None and model_path is not None:
        scorer = WellnessScorer(model_path)
    if scorer is not None:
        prediction = scorer.predict(split["base_features"])

    # 4. Assemble DB-ready record
    return {
        "user_id":              user_id,
        "raw_answers":          raw_answers,
        "encoded_answers":      encoded,
        "base_features":        split["base_features"],
        "additional_features":  split["additional_features"],
        "wellness_prediction":  prediction,
    }
