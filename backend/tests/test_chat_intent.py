"""Characterization tests for chatbot intent detection.

Locks the current behavior of context-gating and comparison-window detection
in services/chat_intent.py (extracted from the chatbot route in Phase 2).
"""

from datetime import date

import pytest

from app.services.chat_intent import (
    detect_comparison_intent as _detect_comparison_intent,
    should_use_diary_context as _should_use_diary_context,
)

pytestmark = pytest.mark.unit

# Fixed reference date so window math is deterministic.
TODAY = date(2026, 6, 14)


class TestShouldUseDiaryContext:
    def test_casual_message_general_mode_is_false(self):
        assert _should_use_diary_context("hey", "general") is False

    def test_daily_mode_always_true(self):
        assert _should_use_diary_context("hey", "daily") is True

    def test_weekly_mode_always_true(self):
        assert _should_use_diary_context("anything", "weekly") is True

    def test_analysis_phrase_triggers(self):
        assert _should_use_diary_context("can you analyze my week?", "general") is True

    def test_comparison_word_triggers(self):
        assert _should_use_diary_context("let's compare", "general") is True

    def test_memory_hint_word_triggers(self):
        assert _should_use_diary_context("tell me about my diary", "general") is True


class TestDetectComparisonIntent:
    def test_no_comparison_returns_none(self):
        assert _detect_comparison_intent("hello there", TODAY) is None

    def test_yesterday_vs_today(self):
        result = _detect_comparison_intent("yesterday vs today", TODAY)
        assert result is not None
        period_a, period_b = result
        assert period_a == (TODAY, TODAY, "today")
        assert period_b == (date(2026, 6, 13), date(2026, 6, 13), "yesterday")

    def test_compared_to_last_week(self):
        result = _detect_comparison_intent("how was this compared to last week", TODAY)
        assert result is not None
        period_a, period_b = result
        assert period_a == (date(2026, 6, 8), TODAY, "this week")
        assert period_b == (date(2026, 6, 1), date(2026, 6, 7), "last week")

    def test_generic_compare_defaults_to_weekly(self):
        result = _detect_comparison_intent("compare my mood", TODAY)
        assert result is not None
        period_a, period_b = result
        assert period_a[2] == "this week"
        assert period_b[2] == "last week"
