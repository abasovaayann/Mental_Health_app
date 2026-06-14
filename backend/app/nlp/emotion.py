"""
Multilingual emotion classifier backed by MilaNLProc/xlm-emo-t — an
XLM-T model fine-tuned on the multilingual XLM-EMO dataset.

Output label is one of:
    joy, sadness, anger, fear

The label set is intentionally smaller than the English-only GoEmotions
model, but the trade-off is real multilingual coverage (Turkish, Russian,
English, etc.) instead of garbled output for non-English diary entries.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypedDict

_MODEL_NAME = "MilaNLProc/xlm-emo-t"
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
    best = raw[0][0] if isinstance(raw[0], list) else raw[0]

    return {
        "label": best["label"].lower(),
        "score": float(best["score"]),
    }
