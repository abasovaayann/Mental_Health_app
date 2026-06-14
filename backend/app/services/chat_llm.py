"""LLM call, prompt assembly, history loading, and offline fallbacks.

This is the only chat module that talks to Anthropic. When the API is
unreachable or unconfigured, the fallback builders produce a friendly,
locally-generated reply from the diary signals instead.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.chat_message import ChatMessage
from app.models.diary import DiaryEntry
from app.models.diary_analysis import DiaryEntryAnalysis
from app.nlp.language import LANG_NAMES, detect_language

CHAT_HISTORY_TURNS = 8  # how many prior user+assistant messages to send to Claude

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


def build_prompt(message: str, context: Optional[str]) -> str:
    lang = detect_language(message)
    lang_name = LANG_NAMES[lang]
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


def load_chat_history(
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


def call_claude(messages: list[dict]) -> str:
    """Send the message history to Claude and return the text reply.

    Raises RuntimeError if the API key is missing or the model returns no text.
    """
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

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
        messages=messages,
    )

    ai_text = ""
    for block in result.content:
        if getattr(block, "type", None) == "text":
            ai_text += block.text
    ai_text = ai_text.strip()

    if not ai_text:
        raise RuntimeError("Claude returned no text response.")
    return ai_text


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


def build_diary_fallback_response(
    message: str,
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> str:
    lang = detect_language(message)

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


def build_general_fallback_response(message: str) -> str:
    lang = detect_language(message)
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
