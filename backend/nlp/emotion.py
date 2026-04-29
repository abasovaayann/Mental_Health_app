"""
Multi-class emotion classifier backed by DistilRoBERTa fine-tuned on the
GoEmotions-derived dataset published by j-hartmann.

Output label is one of:
    joy, sadness, anger, fear, disgust, surprise, neutral
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypedDict

_MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"
_MAX_INPUT_CHARS = 1500


class EmotionResult(TypedDict):
    label: str
    score: float


@lru_cache(maxsize=1)
def _get_pipeline():
    from transformers import pipeline

    return pipeline("text-classification", model=_MODEL_NAME, top_k=1)


def predict_emotion(text: str) -> EmotionResult:
    """Return the highest-scoring emotion label and its confidence."""
    if not text or not text.strip():
        return {"label": "neutral", "score": 0.0}

    truncated = text.strip()[:_MAX_INPUT_CHARS]
    raw = _get_pipeline()(truncated, truncation=True)
    # `top_k=1` → output shape is [[{label, score}]] for a single input
    best = raw[0][0] if isinstance(raw[0], list) else raw[0]

    return {
        "label": best["label"].lower(),
        "score": float(best["score"]),
    }
