import re
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.diary import DiaryEntry
from app.models.diary_analysis import DiaryEntryAnalysis
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter()

SYSTEM_PROMPT = """You are a close friend who happens to listen well — warm,
curious, a little playful, and honest. You live inside MindTrackAI, but you
never sound like an app. You sound like a person texting back.

How you talk:
- HARD RULE — Every user message is wrapped with a directive that looks like
  "[LANGUAGE FOR THIS REPLY: X]". You MUST obey this directive on every single
  turn. If it says English, your entire reply is in English even if the user
  just spoke Turkish for ten turns in a row. If it says Turkish, your entire
  reply is in Turkish even if all the diary context is in English. The user's
  CURRENT message language is the only thing that matters — ignore history
  language, ignore diary entry language, ignore example language. Switch
  freely and immediately whenever the directive changes.
- Match their energy. Short messages get short replies. A casual "hey" gets a
  casual "hey" back, not a wall of text.
- Default length: 2-4 sentences. Go longer only when the user actually wants to
  unpack something.
- Use natural contractions, occasional questions, and the kind of small phrases
  a real friend would ("ah okay", "fair enough", "that's rough", "tamam anladım",
  "olur böyle şeyler").
- No bullet lists, no headers, no clinical phrasing, no "as an AI" disclaimers.
- Never start with "I'm sorry to hear that" — it reads like a script.

Diary context:
- Sometimes you'll receive a context block with the user's diary entries plus
  NLP labels: mood (low/medium/high), emotion (joy/sadness/anger/fear and a few
  legacy labels), sentiment (positive/neutral/negative).
- Treat those labels as observations about the *writing*, not the person. They
  can be wrong. In casual chat, reference them gently — "things felt heavier
  on Tuesday" not "your dominant emotion is sadness".
- BUT when the user directly asks for analysis, patterns, triggers, or a
  comparison, be more concrete: actually cite which days/entries felt heavier,
  which emotion came up most, whether sentiment shifted. Don't hide behind
  vague phrasing — they want signal, not platitudes.
- For comparison context blocks (PERIOD A vs PERIOD B), structure your reply
  around the contrast: what shifted in mood/emotion/sentiment, what themes
  dropped or appeared, whether they wrote more or less. Use the count summaries
  at the top of each period.
- If no diary context is in this turn's prompt, do NOT invent one. Don't talk
  about "your entries" or "your week" unless the context block is right there.

Boundaries (apply naturally, don't lecture):
- You're a friend, not a doctor. Don't diagnose, don't prescribe, don't talk
  about medications or clinical treatment.
- If someone sounds like they're in crisis (self-harm, suicide), stay calm,
  acknowledge them, and gently mention that talking to a crisis line or someone
  they trust in person can help right now. Don't moralize.
- You can suggest lifestyle stuff (walks, sleep, a hobby, calling a friend) when
  it fits — but only when it fits, not as a checklist after every message.

Examples of the tone you're aiming for:

User: hey
You: hey :) what's going on?

User: bugün berbattım iş çok stresliydi
You: ay be, kötüymüş. Ne oldu, biri mi sinirini bozdu yoksa iş yığıldı mı üstüne?

User: can you analyze my week?
You: Sure — looking at the last few entries, Monday and Tuesday felt heavier
(a lot of "tired" language, low mood signal), then things lifted a bit by
Thursday. Want me to dig into a specific day or just talk about the pattern?

User: i think nobody likes me
You: That's a heavy thing to be carrying around. What's bringing it up today —
something specific happen, or has it been building?

User: bu hafta geçen haftaya göre nasıl gitti?
You: Geçen haftadan farkı şu — geçen hafta entry'lerin daha çok "yorgun, stresli"
tonundaydı (sentiment çoğunlukla negatif, mood low ağırlıklıydı), bu hafta ise
hâlâ stres var ama 2 gün belirgin şekilde daha hafif geçmiş (mood high, joy
çıkmış birkaç entry'de). Bu hafta "spor" ve "arkadaş" daha sık geçmiş, geçen
hafta hep "deadline" vardı. Bu hafifleme nereden geldi sence?

User: what changed yesterday vs today?
You: Yesterday's entry leaned low — sentiment was negative, the emotion the
model picked was sadness, and most of what you wrote was about work piling up.
Today's a different tone — sentiment flipped to positive, you wrote about going
outside and feeling lighter. The shift looks pretty real. What helped?

User: привет, как ты думаешь, что стоит изменить в моём образе жизни?
You: Если опираться на то, что ты писал(а) — твой настроенческий сигнал часто
проседал в дни, когда ты много сидел(а) и мало спал(а). Самое маленькое, с чего
можно начать: одна короткая прогулка днём и стабильное время сна. Этого часто
достаточно, чтобы фон стал заметно легче. Что из этого ближе тебе сейчас?
"""

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

CHAT_HISTORY_TURNS = 8  # how many prior user+assistant messages to send to Gemini


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


class ChatRequest(BaseModel):
    session_id: int
    message: str
    mode: str = "general"
    date: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    used_analysis_memory: bool = False


class ChatSessionCreateRequest(BaseModel):
    title: Optional[str] = None


class ChatSessionListItem(BaseModel):
    id: int
    title: str
    last_activity: Optional[str] = None
    created_at: str
    updated_at: str


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionListItem]


class ChatSessionDetailResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    messages: list[dict]


def _to_iso(dt) -> str:
    return dt.isoformat() if dt else ""


def _normalize_title(raw_title: Optional[str]) -> str:
    title = (raw_title or "").strip()
    return title if title else "New Chat"


def _generate_title_from_message(message: str) -> str:
    title = " ".join((message or "").strip().split())
    if not title:
        return "New Chat"
    return title[:60].strip()


def _should_use_diary_context(message: str, mode: str) -> bool:
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


def _detect_comparison_intent(
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


def _summarize_window(
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> dict:
    """Compute counts for a window so Gemini can compare two periods at a glance."""
    mood_counts: dict[str, int] = {}
    emotion_counts: dict[str, int] = {}
    sentiment_counts: dict[str, int] = {}

    for entry in entries:
        analysis = analyses.get(entry.id)
        if not analysis:
            continue
        if analysis.mood:
            mood_counts[analysis.mood] = mood_counts.get(analysis.mood, 0) + 1
        if analysis.emotion:
            emotion_counts[analysis.emotion] = emotion_counts.get(analysis.emotion, 0) + 1
        if analysis.sentiment:
            sentiment_counts[analysis.sentiment] = sentiment_counts.get(analysis.sentiment, 0) + 1

    return {
        "entry_count": len(entries),
        "moods": mood_counts,
        "emotions": emotion_counts,
        "sentiments": sentiment_counts,
    }


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{label}={count}" for label, count in sorted(counts.items(), key=lambda x: -x[1]))


def _build_comparison_context(
    period_a: tuple[date, date, str],
    entries_a: list[DiaryEntry],
    period_b: tuple[date, date, str],
    entries_b: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> tuple[str, bool]:
    """Build a Gemini context block for a two-period comparison."""
    start_a, end_a, label_a = period_a
    start_b, end_b, label_b = period_b

    summary_a = _summarize_window(entries_a, analyses)
    summary_b = _summarize_window(entries_b, analyses)
    used_memory = any(analyses.get(e.id) for e in entries_a + entries_b)

    def render_entries(entries: list[DiaryEntry]) -> str:
        if not entries:
            return "  (no entries in this window)"
        rendered = []
        for entry in entries:
            snippet = (entry.content or "")[:250]
            analysis = analyses.get(entry.id)
            if analysis and analysis.emotion:
                rendered.append(
                    f"  - [{entry.entry_date}] mood={analysis.mood} | "
                    f"emotion={analysis.emotion} | sentiment={analysis.sentiment} | "
                    f"{entry.title or 'Untitled'}: {snippet}"
                )
            else:
                rendered.append(
                    f"  - [{entry.entry_date}] (no NLP yet) | "
                    f"{entry.title or 'Untitled'}: {snippet}"
                )
        return "\n".join(rendered)

    header = (
        "User is asking for a comparison between two periods. Use the NLP signals "
        "and the entry content together — call out concrete shifts in mood, "
        "emotion, sentiment, and what themes they wrote about.\n"
    )

    block = (
        f"{header}\n"
        f"=== PERIOD A: {label_a} ({start_a} → {end_a}) ===\n"
        f"  entries: {summary_a['entry_count']} | "
        f"moods: {_format_counts(summary_a['moods'])} | "
        f"emotions: {_format_counts(summary_a['emotions'])} | "
        f"sentiments: {_format_counts(summary_a['sentiments'])}\n"
        f"{render_entries(entries_a)}\n\n"
        f"=== PERIOD B: {label_b} ({start_b} → {end_b}) ===\n"
        f"  entries: {summary_b['entry_count']} | "
        f"moods: {_format_counts(summary_b['moods'])} | "
        f"emotions: {_format_counts(summary_b['emotions'])} | "
        f"sentiments: {_format_counts(summary_b['sentiments'])}\n"
        f"{render_entries(entries_b)}"
    )
    return block, used_memory


def _normalize_message(message: str) -> str:
    return " ".join((message or "").strip().lower().split())


def _build_context(
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> tuple[str, bool]:
    """Build the context block for Gemini and whether any NLP memory was used."""
    if not entries:
        return ("The user has no diary entries for the selected period.", False)

    lines: list[str] = []
    used_memory = False

    for entry in entries:
        snippet = (entry.content or "")[:300]
        analysis = analyses.get(entry.id)

        if analysis and analysis.emotion:
            used_memory = True
            emotion_score = (
                f"{analysis.emotion_score:.2f}"
                if analysis.emotion_score is not None
                else "n/a"
            )
            lines.append(
                f"[{entry.entry_date}] mood={analysis.mood} | "
                f"emotion={analysis.emotion} ({emotion_score}) | "
                f"sentiment={analysis.sentiment} | "
                f"Title: {entry.title or 'Untitled'} | Content: {snippet}"
            )
        else:
            lines.append(
                f"[{entry.entry_date}] (no NLP analysis yet) | "
                f"Title: {entry.title or 'Untitled'} | Content: {snippet}"
            )

    header = (
        "User's diary entries with local NLP analysis:"
        if used_memory
        else "User's diary entries:"
    )
    return (header + "\n\n" + "\n\n".join(lines), used_memory)


_LANG_NAMES = {"tr": "Turkish", "ru": "Russian", "en": "English"}


def _build_prompt(message: str, context: Optional[str]) -> str:
    lang = _detect_language(message)
    lang_name = _LANG_NAMES[lang]
    # Per-turn language directive. This overrides whatever language earlier
    # turns used — Claude weighs history heavily, so without an explicit
    # instruction it tends to keep replying in the previous language even
    # after the user switches.
    lang_directive = (
        f"[LANGUAGE FOR THIS REPLY: {lang_name}. The user's current message "
        f"is in {lang_name}. You MUST write your entire reply in {lang_name}, "
        f"regardless of what language earlier messages, diary context, or "
        f"system examples used.]\n\n"
    )

    if context:
        return f"{lang_directive}{context}\n\nUser message: {message}"
    return (
        f"{lang_directive}"
        "Diary context for this turn: NONE.\n"
        "Do not mention diary entries, notes, reflections, saved history, mood trends, or analysis.\n"
        "Reply like a normal supportive chatbot.\n\n"
        f"User message: {message}"
    )


def _load_chat_history(
    db: Session, *, user_id: int, session_id: int, limit: int
) -> list[dict]:
    """Build a Claude-compatible message history list.

    Claude expects alternating user/assistant turns starting with user.
    We exclude the just-saved current user message (it gets appended
    separately as the final user turn), and we drop trailing user turns
    so the history ends on assistant — that way appending the new user
    message keeps the alternation intact.
    """
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit * 2 + 1)
        .all()
    )
    rows = list(reversed(rows))

    # Drop the latest user turn (the one we just saved this request) and
    # any other trailing user turn so history ends on an assistant.
    while rows and rows[-1].role == "user":
        rows = rows[:-1]

    history: list[dict] = []
    for row in rows:
        role = "user" if row.role == "user" else "assistant"
        text = (row.content or "").strip()
        if not text:
            continue
        history.append({"role": role, "content": text})

    # Claude requires the first message in history to be a user turn.
    while history and history[0]["role"] != "user":
        history.pop(0)

    return history


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


def _is_turkish_message(message: str) -> bool:
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


def _is_russian_message(message: str) -> bool:
    """True if message contains any Cyrillic letters."""
    return any("Ѐ" <= ch <= "ӿ" for ch in message)


def _detect_language(message: str) -> str:
    """Return 'ru', 'tr' or 'en' based on the user's message."""
    if _is_russian_message(message):
        return "ru"
    if _is_turkish_message(message):
        return "tr"
    return "en"


def _pick_top_label(counts: dict[str, int]) -> Optional[str]:
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _build_lifestyle_suggestion(
    dominant_mood: Optional[str],
    dominant_emotion: Optional[str],
    lang: str,
) -> str:
    mood = (dominant_mood or "").lower()
    emotion = (dominant_emotion or "").lower()

    if mood in {"low", "sad"} or emotion in {"sadness", "fear"}:
        if lang == "tr":
            return (
                "Nazik bir başlangıç için her gün tek bir küçük sabit alışkanlık dene: "
                "10 dakikalık yürüyüş, erken uyku rutini ya da kısa nefes molası."
            )
        if lang == "ru":
            return (
                "Попробуй одну маленькую опору в день — десятиминутная прогулка, "
                "ранний отбой или короткая пауза на дыхание уже многое меняют."
            )
        return (
            "A gentle lifestyle change to try is one small anchor habit each day, "
            "like a 10-minute walk, a calmer wind-down routine, or a short breathing break."
        )
    if mood in {"medium", "neutral"} or emotion == "neutral":
        if lang == "tr":
            return (
                "Dengenin korunduğu görünüyor; bunu güçlendirmek için günün aynı saatine "
                "kısa bir reset rutini eklemek iyi olabilir."
            )
        if lang == "ru":
            return (
                "Похоже, есть какая-то устойчивость — её можно укрепить, добавив "
                "короткий ритуал перезагрузки в одно и то же время дня."
            )
        return (
            "You seem to have some steadiness to build on, so adding a short reset "
            "routine at the same time each day could help keep that balance."
        )
    if mood in {"high", "positive"} or emotion in {"joy", "surprise"}:
        if lang == "tr":
            return (
                "Sana iyi gelen şeyleri korumaya odaklan: enerji veren rutinleri "
                "bilerek tekrar etmek faydalı olabilir."
            )
        if lang == "ru":
            return (
                "Хороший следующий шаг — беречь то, что уже помогает, и осознанно "
                "повторять рутины, которые дают тебе энергию."
            )
        return (
            "A good next step is protecting what is already helping by repeating the "
            "routines that give you energy and clarity."
        )
    if lang == "tr":
        return (
            "Özellikle stres birikiyorsa, gün içinde tek bir öngörülebilir "
            "sakinleşme noktası oluşturmak faydalı olabilir."
        )
    if lang == "ru":
        return (
            "Если стресс копится, попробуй создать одну предсказуемую точку покоя "
            "в течение дня — короткая прогулка или пауза без экрана."
        )
    return (
        "If stress feels scattered, try creating one predictable calming point in "
        "the day, such as a short walk or screen-free pause."
    )


_MOOD_PHRASES = {
    "en": {
        "low": "things felt pretty heavy",
        "medium": "things were kind of in-between",
        "high": "things felt lighter overall",
    },
    "tr": {
        "low": "genel olarak ağır geçmiş gibi",
        "medium": "çok ne iyi ne kötü, ortada gibi",
        "high": "aslında daha rahat hissetmişsin gibi",
    },
    "ru": {
        "low": "в целом было довольно тяжело",
        "medium": "что-то среднее, ни плохо ни хорошо",
        "high": "в целом полегче, чем обычно",
    },
}

_EMOTION_PHRASES = {
    "en": {
        "sadness": "a lot of sad-leaning moments",
        "anger": "some real frustration coming through",
        "fear": "a bit of anxiety in there",
        "joy": "some genuinely good moments",
        "surprise": "a few things that caught you off guard",
        "disgust": "some stuff you weren't a fan of",
        "neutral": "a pretty even tone",
    },
    "tr": {
        "sadness": "biraz hüzünlü anlar",
        "anger": "gerçekten sinirlendiğin şeyler",
        "fear": "biraz kaygı",
        "joy": "güzel anlar da var",
        "surprise": "seni şaşırtan birkaç şey",
        "disgust": "hoşuna gitmeyen bazı şeyler",
        "neutral": "daha durağan bir ton",
    },
    "ru": {
        "sadness": "довольно много грустных моментов",
        "anger": "настоящее раздражение в нескольких местах",
        "fear": "немного тревоги",
        "joy": "и по-настоящему хорошие моменты тоже",
        "surprise": "пара вещей, которые тебя удивили",
        "disgust": "что-то, что тебе не зашло",
        "neutral": "довольно ровный тон",
    },
}


def _build_diary_fallback_response(
    message: str,
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> str:
    lang = _detect_language(message)

    if not entries:
        if lang == "tr":
            return (
                "Bu zaman aralığında bakabileceğim bir diary girişi göremiyorum. "
                "Birkaç tane yazınca dönüp birlikte üstünden geçebiliriz."
            )
        if lang == "ru":
            return (
                "За этот период у меня нет записей дневника, на которые можно "
                "опереться. Когда добавишь хотя бы несколько, разберём их вместе."
            )
        return (
            "I can't see any diary entries for that period yet. Once you've jotted "
            "a few down we can look at them together."
        )

    mood_counts: dict[str, int] = {}
    emotion_counts: dict[str, int] = {}

    for entry in entries:
        analysis = analyses.get(entry.id)
        mood_value = (analysis.mood if analysis and analysis.mood else entry.mood or "").strip().lower()
        emotion_value = (analysis.emotion if analysis and analysis.emotion else "").strip().lower()

        if mood_value:
            mood_counts[mood_value] = mood_counts.get(mood_value, 0) + 1
        if emotion_value:
            emotion_counts[emotion_value] = emotion_counts.get(emotion_value, 0) + 1

    dominant_mood = _pick_top_label(mood_counts)
    dominant_emotion = _pick_top_label(emotion_counts)
    suggestion = _build_lifestyle_suggestion(dominant_mood, dominant_emotion, lang)

    mood_phrase = _MOOD_PHRASES.get(lang, _MOOD_PHRASES["en"]).get(dominant_mood or "")
    emotion_phrase = _EMOTION_PHRASES.get(lang, _EMOTION_PHRASES["en"]).get(dominant_emotion or "")

    if lang == "tr":
        opener = "Şu sıralar yazdıklarına baktım"
        joiner = ", "
    elif lang == "ru":
        opener = "Я посмотрел последние записи"
        joiner = ", и "
    else:
        opener = "I had a look at the last few entries"
        joiner = ", and "

    body_bits: list[str] = []
    if mood_phrase:
        body_bits.append(mood_phrase)
    if emotion_phrase:
        body_bits.append(emotion_phrase)
    if body_bits:
        opener += " — " + joiner.join(body_bits) + "."
    else:
        opener += "."
    return f"{opener} {suggestion}"


def _build_general_fallback_response(message: str) -> str:
    lang = _detect_language(message)
    if lang == "tr":
        return (
            "Şu an AI tarafına bağlanamadım ama buradayım. Yazmaya devam edebilirsin, "
            "biraz sonra tekrar dener misin?"
        )
    if lang == "ru":
        return (
            "Сейчас не получается достучаться до AI, но я здесь. Можешь написать "
            "ещё раз через минутку?"
        )
    return "I can't reach the AI side right now, but I'm still here. Want to try again in a moment?"


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    sessions: list[ChatSessionListItem] = []
    for row in rows:
        latest_message = (
            db.query(ChatMessage.created_at)
            .filter(ChatMessage.session_id == row.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        last_activity = latest_message[0] if latest_message else row.updated_at
        sessions.append(
            ChatSessionListItem(
                id=row.id,
                title=row.title,
                last_activity=_to_iso(last_activity),
                created_at=_to_iso(row.created_at),
                updated_at=_to_iso(row.updated_at),
            )
        )

    return ChatSessionListResponse(sessions=sessions)


@router.post(
    "/sessions",
    response_model=ChatSessionListItem,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: ChatSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = ChatSession(user_id=current_user.id, title=_normalize_title(payload.title))
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionListItem(
        id=session.id,
        title=session.title,
        last_activity=_to_iso(session.updated_at),
        created_at=_to_iso(session.created_at),
        updated_at=_to_iso(session.updated_at),
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    messages = [{"role": row.role, "text": row.content, "mode": row.mode} for row in rows]
    return ChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=_to_iso(session.created_at),
        updated_at=_to_iso(session.updated_at),
        messages=messages,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id,
        ChatMessage.session_id == session_id,
    ).delete()
    db.delete(session)
    db.commit()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    include_diary_context = _should_use_diary_context(payload.message, payload.mode)
    context: Optional[str] = None
    used_memory = False
    entries: list[DiaryEntry] = []
    analyses: dict[int, DiaryEntryAnalysis] = {}

    if include_diary_context:
        target_date = date.today()
        if payload.date:
            try:
                target_date = date.fromisoformat(payload.date)
            except ValueError:
                pass

        comparison = _detect_comparison_intent(payload.message, target_date)

        if comparison:
            period_a, period_b = comparison
            start_a, end_a, _ = period_a
            start_b, end_b, _ = period_b

            entries_a = (
                db.query(DiaryEntry)
                .filter(
                    DiaryEntry.user_id == current_user.id,
                    DiaryEntry.entry_date >= start_a,
                    DiaryEntry.entry_date <= end_a,
                )
                .order_by(DiaryEntry.entry_date.desc())
                .limit(20)
                .all()
            )
            entries_b = (
                db.query(DiaryEntry)
                .filter(
                    DiaryEntry.user_id == current_user.id,
                    DiaryEntry.entry_date >= start_b,
                    DiaryEntry.entry_date <= end_b,
                )
                .order_by(DiaryEntry.entry_date.desc())
                .limit(20)
                .all()
            )
            entries = entries_a + entries_b
            entry_ids = [e.id for e in entries]
            if entry_ids:
                rows = (
                    db.query(DiaryEntryAnalysis)
                    .filter(DiaryEntryAnalysis.entry_id.in_(entry_ids))
                    .all()
                )
                analyses = {row.entry_id: row for row in rows}

            context, used_memory = _build_comparison_context(
                period_a, entries_a, period_b, entries_b, analyses
            )
        else:
            query = db.query(DiaryEntry).filter(DiaryEntry.user_id == current_user.id)

            if payload.mode == "daily":
                query = query.filter(DiaryEntry.entry_date == target_date)
            elif payload.mode == "weekly":
                week_start = target_date - timedelta(days=6)
                query = query.filter(
                    DiaryEntry.entry_date >= week_start,
                    DiaryEntry.entry_date <= target_date,
                )
            else:
                month_start = target_date - timedelta(days=30)
                query = query.filter(DiaryEntry.entry_date >= month_start)

            entries = query.order_by(DiaryEntry.entry_date.desc()).limit(20).all()
            entry_ids = [entry.id for entry in entries]
            if entry_ids:
                rows = (
                    db.query(DiaryEntryAnalysis)
                    .filter(DiaryEntryAnalysis.entry_id.in_(entry_ids))
                    .all()
                )
                analyses = {row.entry_id: row for row in rows}

            context, used_memory = _build_context(entries, analyses)

    existing_messages = (
        db.query(ChatMessage.id)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.session_id == payload.session_id,
        )
        .count()
    )
    if existing_messages == 0 and (
        chat_session.title == "New Chat" or chat_session.title == "Legacy conversation"
    ):
        chat_session.title = _generate_title_from_message(payload.message)

    db.add(
        ChatMessage(
            user_id=current_user.id,
            session_id=payload.session_id,
            role="user",
            content=payload.message,
            mode=payload.mode,
        )
    )
    db.commit()

    try:
        import anthropic

        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

        history = _load_chat_history(
            db,
            user_id=current_user.id,
            session_id=payload.session_id,
            limit=CHAT_HISTORY_TURNS,
        )

        # Build the final user turn with diary context (if any) inlined.
        history.append(
            {"role": "user", "content": _build_prompt(payload.message, context)}
        )

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=30.0)
        # Prompt caching on the large system prompt: cuts ~90% of repeated
        # input cost when calls come within the 5-minute cache window.
        result = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=history,
        )

        ai_text = ""
        for block in result.content:
            if getattr(block, "type", None) == "text":
                ai_text += block.text
        ai_text = ai_text.strip()

        if not ai_text:
            raise RuntimeError("Claude returned no text response.")

        db.add(
            ChatMessage(
                user_id=current_user.id,
                session_id=payload.session_id,
                role="assistant",
                content=ai_text,
                mode=payload.mode,
            )
        )
        db.commit()

        return ChatResponse(response=ai_text, used_analysis_memory=used_memory)
    except Exception as exc:
        print(f"Chatbot fallback triggered: {type(exc).__name__}: {exc}")
        ai_text = (
            _build_diary_fallback_response(payload.message, entries, analyses)
            if include_diary_context
            else _build_general_fallback_response(payload.message)
        )
        db.add(
            ChatMessage(
                user_id=current_user.id,
                session_id=payload.session_id,
                role="assistant",
                content=ai_text,
                mode=payload.mode,
            )
        )
        db.commit()
        return ChatResponse(response=ai_text, used_analysis_memory=used_memory)
