"""
wellness – Hybrid ML module for student mental wellness tracking.

Submodules
----------
mappings        Global text → numeric encoding dictionaries
encoders        Functions to encode individual answers & full surveys
features        Feature splitting (base-model vs. custom)
scorer          Wellness score prediction using RF (Kaggle-compatible features)
retrainer       Future-retraining scaffolding (all custom features)
"""

from .mappings import (
    FREQUENCY_SCALE,
    INTENSITY_SCALE,
    SENTIMENT_SCALE,
    SUPPORT_SCALE,
    MOTIVATION_SCALE,
    CONCENTRATION_SCALE,
    FINANCIAL_SCALE,
    SLEEP_DURATION_MAP,
    FIELD_SCALE_REGISTRY,
)
from .encoders import (
    encode_answer,
    encode_sleep_duration,
    encode_survey,
)
from .features import (
    BASE_MODEL_FEATURES,
    ADDITIONAL_FEATURES,
    ALL_FEATURES,
    split_features,
)
from .scorer import WellnessScorer
from .retrainer import WellnessRetrainer

__all__ = [
    # mappings
    "FREQUENCY_SCALE",
    "INTENSITY_SCALE",
    "SENTIMENT_SCALE",
    "SUPPORT_SCALE",
    "MOTIVATION_SCALE",
    "CONCENTRATION_SCALE",
    "FINANCIAL_SCALE",
    "SLEEP_DURATION_MAP",
    "FIELD_SCALE_REGISTRY",
    # encoders
    "encode_answer",
    "encode_sleep_duration",
    "encode_survey",
    # features
    "BASE_MODEL_FEATURES",
    "ADDITIONAL_FEATURES",
    "ALL_FEATURES",
    "split_features",
    # scorer / retrainer
    "WellnessScorer",
    "WellnessRetrainer",
]
