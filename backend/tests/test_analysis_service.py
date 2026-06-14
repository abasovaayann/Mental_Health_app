"""Tests for the diary analysis service.

_derive_mood is pure and fully testable. analyze_text is tested with the two
NLP classifiers monkeypatched, so the suite never downloads transformer
weights or runs a model.
"""

import pytest

from app.services import analysis_service
from app.services.analysis_service import _derive_mood, analyze_text

pytestmark = pytest.mark.unit


class TestDeriveMood:
    def test_joy_is_high(self):
        assert _derive_mood("joy", "positive") == "high"

    def test_sadness_is_low(self):
        assert _derive_mood("sadness", "negative") == "low"

    def test_neutral_emotion_positive_sentiment_nudges_high(self):
        assert _derive_mood("neutral", "positive") == "high"

    def test_neutral_emotion_negative_sentiment_nudges_low(self):
        assert _derive_mood("neutral", "negative") == "low"

    def test_neutral_emotion_neutral_sentiment_stays_medium(self):
        assert _derive_mood("neutral", "neutral") == "medium"

    def test_unknown_emotion_defaults_to_medium(self):
        assert _derive_mood("excitement", "neutral") == "medium"

    def test_strong_emotion_ignores_sentiment(self):
        # sadness has a strong-valence base ("low"); positive sentiment must not lift it.
        assert _derive_mood("sadness", "positive") == "low"


class TestAnalyzeText:
    def test_combines_classifier_outputs(self, monkeypatch):
        monkeypatch.setattr(
            analysis_service,
            "predict_sentiment",
            lambda text: {"label": "positive", "score": 0.91},
        )
        monkeypatch.setattr(
            analysis_service,
            "predict_emotion",
            lambda text: {"label": "joy", "score": 0.88},
        )

        result = analyze_text("had a great day with friends")

        assert result == {
            "sentiment": "positive",
            "sentiment_score": 0.91,
            "emotion": "joy",
            "emotion_score": 0.88,
            "mood": "high",
        }
