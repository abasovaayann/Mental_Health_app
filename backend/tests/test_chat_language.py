"""Characterization tests for the chatbot language detector.

These lock the current behavior of the multilingual heuristics in
nlp/language.py (extracted from the chatbot route in Phase 2).
"""

import pytest

from app.nlp.language import (
    detect_language as _detect_language,
    is_russian_message as _is_russian_message,
    is_turkish_message as _is_turkish_message,
)

pytestmark = pytest.mark.unit


class TestDetectLanguage:
    def test_cyrillic_is_russian(self):
        assert _detect_language("привет, как дела?") == "ru"

    def test_turkish_diacritics_is_turkish(self):
        assert _detect_language("bugün çok yorgunum") == "tr"

    def test_turkish_hint_word_without_diacritics_is_turkish(self):
        # "merhaba" / "nasil" are in the hint-word set; no special chars needed.
        assert _detect_language("merhaba nasil gidiyor") == "tr"

    def test_plain_english_is_english(self):
        assert _detect_language("hello how are you doing today") == "en"

    def test_russian_takes_priority_over_latin_text(self):
        # Mixed message containing Cyrillic still resolves to Russian first.
        assert _detect_language("ok привет") == "ru"


class TestIsTurkishMessage:
    def test_diacritic_short_circuits_true(self):
        assert _is_turkish_message("şğıöçü") is True

    def test_suffix_pattern_detects_turkish(self):
        # "yapiyorum" matches the Turkish verb-suffix regex.
        assert _is_turkish_message("ben bunu yapiyorum") is True

    def test_pure_english_is_not_turkish(self):
        assert _is_turkish_message("the quick brown fox") is False


class TestIsRussianMessage:
    def test_cyrillic_true(self):
        assert _is_russian_message("дневник") is True

    def test_latin_false(self):
        assert _is_russian_message("diary") is False
