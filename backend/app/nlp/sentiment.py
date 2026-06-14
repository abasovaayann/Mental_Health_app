"""
Multilingual sentiment classifier (positive / neutral / negative) backed by
the cardiffnlp XLM-RoBERTa model trained on Twitter data in 8+ languages
(English, Turkish, Russian, Spanish, French, Arabic, Hindi, Portuguese).

The first call lazily downloads the weights to ~/.cache/huggingface and
keeps the pipeline in memory. Subsequent calls run on CPU in ~80-120 ms
for short diary entries.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypedDict

_MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_MAX_INPUT_CHARS = 1500


class SentimentResult(TypedDict):
    label: str  # "positive" | "neutral" | "negative"
    score: float  # 0.0 - 1.0


@lru_cache(maxsize=1)
def _get_pipeline():
    from transformers import pipeline

    return pipeline("sentiment-analysis", model=_MODEL_NAME)


def predict_sentiment(text: str) -> SentimentResult:
    """Return the dominant sentiment label and its confidence."""
    if not text or not text.strip():
        return {"label": "neutral", "score": 0.0}

    truncated = text.strip()[:_MAX_INPUT_CHARS]
    raw = _get_pipeline()(truncated, truncation=True)[0]

    return {
        "label": raw["label"].lower(),
        "score": float(raw["score"]),
    }
