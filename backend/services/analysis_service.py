"""
Diary analysis service.

Combines the local sentiment + emotion classifiers into a single
structured result that downstream consumers (DB, Chatbot) can use.

This module is intentionally LLM-free — Gemini is only called by the
chatbot for natural-language response generation, never for analysis.
"""

from __future__ import annotations

from typing import TypedDict

from nlp.emotion import predict_emotion
from nlp.sentiment import predict_sentiment


class DiaryAnalysis(TypedDict):
    sentiment: str
    sentiment_score: float
    emotion: str
    emotion_score: float
    mood: str  # "low" | "medium" | "high"


# Valence-based emotion → mood mapping. The active multilingual emotion
# model only emits {joy, sadness, anger, fear}; the extra English-model
# labels (surprise/disgust/neutral) are kept for backward compatibility
# with cached rows written before the model switch.
_EMOTION_TO_MOOD = {
    "joy": "high",
    "surprise": "medium",
    "neutral": "medium",
    "sadness": "low",
    "fear": "low",
    "anger": "low",
    "disgust": "low",
}


def _derive_mood(emotion: str, sentiment: str) -> str:
    base = _EMOTION_TO_MOOD.get(emotion, "medium")

    # Sentiment only nudges ambiguous emotions; strong-valence emotions stay put.
    if base == "medium" and sentiment == "positive":
        return "high"
    if base == "medium" and sentiment == "negative":
        return "low"

    return base


def analyze_text(text: str) -> DiaryAnalysis:
    """Run the full local NLP pipeline on a single diary entry."""
    sentiment = predict_sentiment(text)
    emotion = predict_emotion(text)

    return {
        "sentiment": sentiment["label"],
        "sentiment_score": sentiment["score"],
        "emotion": emotion["label"],
        "emotion_score": emotion["score"],
        "mood": _derive_mood(emotion["label"], sentiment["label"]),
    }
