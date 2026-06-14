"""Lightweight, dependency-free language detection for chat messages.

Heuristic detector that picks Turkish / Russian / English from a single
message. Extracted from the chatbot route so the rules can be reused and
unit-tested in isolation.
"""

import re

# Human-readable names keyed by the detector's language codes.
LANG_NAMES = {"tr": "Turkish", "ru": "Russian", "en": "English"}


def _normalize_message(message: str) -> str:
    return " ".join((message or "").strip().lower().split())


# Suffix patterns that are extremely Turkish-specific. Catches "yapıyor",
# "yapmış", "yapsın", "yapmalı", "yapacak", "yapardı", "yapıyorum", etc.
_TURKISH_SUFFIX_PATTERN = re.compile(
    r"\b\w{2,}(yor|yorum|yorsun|yoruz|yorlar|miş|mış|muş|müş|"
    r"sın|sin|sun|sün|larım|lerim|larımız|lerimiz|"
    r"malı|meli|acak|ecek|ardı|erdi|ydi|ydi|yse|"
    r"den|dan|ten|tan|nin|nın|nun|nün)\b",
    re.IGNORECASE,
)

# High-confidence Turkish words that almost never appear in English/Russian
# casual text. Used in OR with the suffix pattern and Turkish-specific chars.
_TURKISH_HINT_WORDS = {
    # Greetings / common
    "merhaba", "selam", "selamlar", "naber", "iyiyim", "kötüyüm",
    # Yes/no/agreement
    "evet", "hayır", "hayir", "tamam", "olur", "olmaz",
    # Question words
    "nasıl", "nasil", "nedir", "neden", "niye", "niçin", "nicin",
    "hangi", "kime", "kimi", "nereye", "nerede", "neresi",
    # Time words
    "bugün", "bugun", "dün", "dun", "yarın", "yarin",
    "şimdi", "simdi", "haftaya", "geçen", "gecen",
    "gün", "gun", "hafta", "haftalık", "haftalik",
    # Modifiers / fillers
    "peki", "ama", "fakat", "yine", "hala", "halen", "biraz",
    "çok", "cok", "daha", "kadar", "için", "icin",
    "gibi", "ile", "şu", "su", "bu", "şunlar", "sunlar",
    # Personal
    "ben", "sen", "biz", "siz", "onlar",
    "benim", "senin", "bizim", "sizin", "onların",
    "bana", "sana", "bize", "size",
    # Diary / mental
    "günlük", "gunluk", "günlüğüm", "gunlugum",
    "yazıyorum", "yaziyorum", "yazdığım", "yazdigim",
    "yazdıklarım", "yazdiklarim", "yazılar", "yazilar",
    # Analysis / advice
    "analiz", "özet", "ozet", "özetle", "ozetle",
    "tavsiye", "tavsiyen", "öneri", "oneri", "önerin", "onerin",
    "öner", "oner", "yardım", "yardim", "bak", "bakar",
    "söyle", "soyle", "anlat", "düşün", "dusun",
    # Mood/feeling
    "hissediyorum", "hissettim", "iyi", "kötü", "kotu",
    "mutlu", "üzgün", "uzgun", "yorgun", "stresli",
}


def is_turkish_message(message: str) -> bool:
    # 1. Turkish-specific diacritics → definitely Turkish
    if any(char in message for char in "çğıöşüÇĞİÖŞÜ"):
        return True

    normalized = _normalize_message(message)

    # 2. Explicit hint words → very likely Turkish
    words = set(
        normalized.replace("?", " ").replace("!", " ").replace(",", " ").split()
    )
    if words & _TURKISH_HINT_WORDS:
        return True

    # 3. Turkish-specific suffix patterns ("yapıyor", "edersin", "yapmalı"…)
    if _TURKISH_SUFFIX_PATTERN.search(normalized):
        return True

    return False


def is_russian_message(message: str) -> bool:
    """True if message contains any Cyrillic letters."""
    return any("Ѐ" <= ch <= "ӿ" for ch in message)


def detect_language(message: str) -> str:
    """Return 'ru', 'tr' or 'en' based on the user's message."""
    if is_russian_message(message):
        return "ru"
    if is_turkish_message(message):
        return "tr"
    return "en"
