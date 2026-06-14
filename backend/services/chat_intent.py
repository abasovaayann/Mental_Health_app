"""Chat intent detection.

Decides (a) whether a chat turn should pull diary context and (b) whether the
user is asking to compare two time periods. Extracted from the chatbot route
so the keyword/phrase heuristics can be unit-tested in isolation.
"""

from datetime import date, timedelta
from typing import Optional

_ANALYSIS_HINT_WORDS = {
    # English — analysis / summary / patterns
    "analyze", "analyse", "analysis", "summarize", "summarise", "summary",
    "pattern", "patterns", "trend", "trends", "theme", "themes",
    "insight", "insights", "trigger", "triggers", "triggering",
    # English — advice / recommendations / lifestyle
    "recommend", "recommendation", "recommendations", "suggest", "suggestion",
    "suggestions", "advice", "tip", "tips", "advise", "guidance",
    "lifestyle", "habit", "habits", "routine", "routines",
    # Turkish
    "analiz", "ozet", "özet", "özetle", "ozetle",
    "tavsiye", "tavsiyen", "öneri", "oneri", "önerin", "onerin",
    "öner", "oner", "önerisin", "onerirsin",
    "alışkanlık", "aliskanlik", "rutin", "yaşam", "yasam",
    "pattern", "tema", "temalar",
    # Russian
    "анализ", "проанализируй", "сводка", "тренд", "паттерн", "паттерны",
    "тема", "темы", "триггер", "триггеры",
    "совет", "совета", "посоветуй", "рекомендация", "рекомендации",
    "образ", "привычка", "привычки",
}

_MEMORY_HINT_WORDS = {
    # English
    "diary", "journal", "entry", "entries", "reflection", "reflections",
    "week", "weekly", "history", "month", "monthly",
    # Turkish
    "günlük", "gunluk", "günlüğüm", "gunlugum", "günlügüm",
    "yazdığım", "yazdigim", "yazdıklarım", "yazdiklarim",
    "hafta", "haftalık", "haftalik", "ay", "aylık", "ayrlik",
    # Russian
    "дневник", "дневнике", "дневника", "записи", "запись",
    "неделя", "неделе", "недели", "недель", "месяц", "месяце",
}

_ANALYSIS_HINT_PHRASES = (
    "based on my diary",
    "based on my entries",
    "looking at my diary",
    "looking at my entries",
    "looking at recent entries",
    "from my diary",
    "from my entries",
    "recent entries",
    "this week",
    "last week",
    "my week",
    # comparison phrases (English)
    "compared to",
    "compare to",
    "compare with",
    "vs last",
    "vs this",
    "versus last",
    "yesterday vs today",
    "today vs yesterday",
    "this week vs last week",
    "last week vs this week",
    # comparison phrases (Turkish)
    "geçen hafta",
    "gecen hafta",
    "geçen haftaya",
    "gecen haftaya",
    "geçen haftayla",
    "gecen haftayla",
    "bu hafta ile geçen",
    "bu hafta ile gecen",
    "dünden bugüne",
    "dunden bugune",
    "dün ile bugün",
    "dun ile bugun",
    "dünkü",
    "dunku",
    "bu hafta",
    "günlüğüme bak",
    "gunlugume bak",
    "yazdıklarıma bak",
    "yazdiklarima bak",
    "son entry",
    "son entryler",
    # comparison phrases (Russian)
    "на этой неделе",
    "на прошлой неделе",
    "по сравнению с прошлой",
    "по сравнению с прошлым",
    "вчера и сегодня",
    "вчера vs сегодня",
    "посмотри мой дневник",
    "из моего дневника",
    "мои записи",
    "за последнюю неделю",
)

# Generic comparison/diff keywords. Used in BOTH context-fetch trigger and
# comparison-intent detection.
_COMPARISON_WORDS = {
    # English
    "compare", "comparison", "vs", "versus", "differ", "different",
    "difference", "differences", "changed", "shift", "shifted",
    # Turkish (with and without diacritics)
    "kıyas", "kiyas", "kıyasla", "kiyasla", "fark", "farkı",
    "değişmiş", "degismis", "değişti", "degisti", "farklı", "farkli",
    # Russian
    "сравни", "сравнить", "сравнение", "разница", "разницу",
    "отличается", "отличие", "изменилось", "изменения", "разница",
}


def should_use_diary_context(message: str, mode: str) -> bool:
    normalized = " ".join((message or "").lower().split())
    if mode in {"daily", "weekly"}:
        return True
    if any(phrase in normalized for phrase in _ANALYSIS_HINT_PHRASES):
        return True

    words = set(
        normalized.replace("?", " ").replace("!", " ").replace(",", " ").split()
    )
    if words & _COMPARISON_WORDS:
        return True
    # Any explicit reference to the diary/entries OR any analysis/advice verb
    # is enough on its own. Previously we required BOTH; that was too strict
    # and missed phrases like "give me a lifestyle recommendation" or
    # "посоветуй что-нибудь" where only one bucket matches.
    return bool(words & _MEMORY_HINT_WORDS) or bool(words & _ANALYSIS_HINT_WORDS)


def detect_comparison_intent(
    message: str, today: date
) -> Optional[tuple[tuple[date, date, str], tuple[date, date, str]]]:
    """Detect comparison intent and return two date windows with labels.

    Returns ((start_a, end_a, label_a), (start_b, end_b, label_b)) for
    period A (the more recent/current one) and period B (the older one).
    Returns None if no comparison intent is detected.
    """
    normalized = " ".join((message or "").lower().split())

    yesterday = today - timedelta(days=1)
    this_week_start = today - timedelta(days=6)
    last_week_end = this_week_start - timedelta(days=1)
    last_week_start = last_week_end - timedelta(days=6)

    # Yesterday vs today
    yesterday_today_phrases = (
        "yesterday vs today", "today vs yesterday", "yesterday compared to today",
        "today compared to yesterday",
        "dün ile bugün", "dun ile bugun", "dünden bugüne", "dunden bugune",
        "dün ve bugün", "dun ve bugun", "dünkü ile bugünkü", "dunku ile bugunku",
        "bugünle dün", "bugunle dun",
        "вчера и сегодня", "вчера vs сегодня",
        "сегодня и вчера", "вчера по сравнению с сегодня",
        "разница между вчера и сегодня",
    )
    if any(p in normalized for p in yesterday_today_phrases):
        return (
            (today, today, "today"),
            (yesterday, yesterday, "yesterday"),
        )

    # This week vs last week
    this_last_week_phrases = (
        "this week vs last week", "last week vs this week",
        "this week compared to last week", "compared to last week",
        "geçen haftaya göre", "gecen haftaya gore",
        "geçen haftaya kıyasla", "gecen haftaya kiyasla",
        "geçen hafta ile", "gecen hafta ile",
        "geçen haftayla", "gecen haftayla",
        "bu hafta ile geçen", "bu hafta ile gecen",
        "bu haftayla geçen", "bu haftayla gecen",
        "по сравнению с прошлой неделей", "по сравнению с прошлой",
        "эта неделя и прошлая", "эту неделю и прошлую",
        "прошлая неделя и эта", "разница между этой и прошлой неделей",
    )
    if any(p in normalized for p in this_last_week_phrases):
        return (
            (this_week_start, today, "this week"),
            (last_week_start, last_week_end, "last week"),
        )

    # Generic comparison verb without a specific period → default to weekly compare
    words = set(
        normalized.replace("?", " ").replace("!", " ").replace(",", " ").split()
    )
    if words & _COMPARISON_WORDS:
        return (
            (this_week_start, today, "this week"),
            (last_week_start, last_week_end, "last week"),
        )

    return None
