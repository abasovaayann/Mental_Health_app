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
- Reply in the SAME LANGUAGE the user wrote in (Turkish, English, Russian, etc.).
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
  can be wrong. Reference them gently, like "looking at the past few entries,
  things felt heavier on Tuesday" — not "your dominant emotion is sadness".
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
"""

_ANALYSIS_HINT_WORDS = {
    "analyze",
    "analyse",
    "analysis",
    "summarize",
    "summarise",
    "summary",
    "pattern",
    "patterns",
    "trend",
    "trends",
    "theme",
    "themes",
    "insight",
    "insights",
    "recommend",
    "recommendation",
    "trigger",
    "triggers",
}

_MEMORY_HINT_WORDS = {
    "diary",
    "journal",
    "entry",
    "entries",
    "reflection",
    "reflections",
    "week",
    "weekly",
    "history",
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
)

CHAT_HISTORY_TURNS = 8  # how many prior user+assistant messages to send to Gemini


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
    return bool(words & _ANALYSIS_HINT_WORDS) and bool(words & _MEMORY_HINT_WORDS)


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


def _build_prompt(message: str, context: Optional[str]) -> str:
    if context:
        return f"{context}\n\nUser message: {message}"
    return (
        "Diary context for this turn: NONE.\n"
        "Do not mention diary entries, notes, reflections, saved history, mood trends, or analysis.\n"
        "Reply like a normal supportive chatbot.\n\n"
        f"User message: {message}"
    )


def _load_chat_history(
    db: Session, *, user_id: int, session_id: int, limit: int
) -> list[dict]:
    """Build a Gemini-compatible history list from the last N messages.

    Gemini expects alternating user/model turns. We exclude the just-saved
    user message (it goes in send_message), and we drop the latest turn
    if it would leave history ending on a user role.
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

    if rows and rows[-1].role == "user":
        rows = rows[:-1]

    history: list[dict] = []
    for row in rows:
        role = "user" if row.role == "user" else "model"
        text = (row.content or "").strip()
        if not text:
            continue
        history.append({"role": role, "parts": [text]})

    return history


def _is_turkish_message(message: str) -> bool:
    normalized = _normalize_message(message)
    turkish_hints = {
        "merhaba",
        "selam",
        "gunluk",
        "günlük",
        "yazilar",
        "yazılar",
        "hafta",
        "ozet",
        "özet",
        "oner",
        "öner",
        "yardim",
        "yardım",
        "bak",
    }
    return any(char in message for char in "çğıöşüİ") or any(
        hint in normalized for hint in turkish_hints
    )


def _pick_top_label(counts: dict[str, int]) -> Optional[str]:
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _build_lifestyle_suggestion(
    dominant_mood: Optional[str],
    dominant_emotion: Optional[str],
    turkish: bool,
) -> str:
    mood = (dominant_mood or "").lower()
    emotion = (dominant_emotion or "").lower()

    if mood in {"low", "sad"} or emotion in {"sadness", "fear"}:
        return (
            "Nazik bir baslangic icin her gun tek bir kucuk sabit aliskanlik dene: "
            "10 dakikalik yuruyus, erken uyku rutini ya da kisa nefes molasi."
            if turkish
            else "A gentle lifestyle change to try is one small anchor habit each day, "
            "like a 10-minute walk, a calmer wind-down routine, or a short breathing break."
        )
    if mood in {"medium", "neutral"} or emotion == "neutral":
        return (
            "Dengenin korundugu gorunuyor; bunu guclendirmek icin gunun ayni saatine "
            "kisa bir reset rutini eklemek iyi olabilir."
            if turkish
            else "You seem to have some steadiness to build on, so adding a short reset "
            "routine at the same time each day could help keep that balance."
        )
    if mood in {"high", "positive"} or emotion in {"joy", "surprise"}:
        return (
            "Sana iyi gelen seyleri korumaya odaklan: enerji veren rutinleri bilerek tekrar etmek faydali olabilir."
            if turkish
            else "A good next step is protecting what is already helping by repeating the routines that give you energy and clarity."
        )
    return (
        "Ozellikle stres birikiyorsa, gun icinde tek bir oongorulebilir sakinlesme noktasi olusturmak faydali olabilir."
        if turkish
        else "If stress feels scattered, try creating one predictable calming point in the day, such as a short walk or screen-free pause."
    )


_MOOD_PHRASES_EN = {
    "low": "things felt pretty heavy",
    "medium": "things were kind of in-between",
    "high": "things felt lighter overall",
}

_MOOD_PHRASES_TR = {
    "low": "genel olarak ağır geçmiş gibi",
    "medium": "çok ne iyi ne kötü, ortada gibi",
    "high": "aslında daha rahat hissetmişsin gibi",
}

_EMOTION_PHRASES_EN = {
    "sadness": "a lot of sad-leaning moments",
    "anger": "some real frustration coming through",
    "fear": "a bit of anxiety in there",
    "joy": "some genuinely good moments",
    "surprise": "a few things that caught you off guard",
    "disgust": "some stuff you weren't a fan of",
    "neutral": "a pretty even tone",
}

_EMOTION_PHRASES_TR = {
    "sadness": "biraz hüzünlü anlar",
    "anger": "gerçekten sinirlendiğin şeyler",
    "fear": "biraz kaygı",
    "joy": "güzel anlar da var",
    "surprise": "seni şaşırtan birkaç şey",
    "disgust": "hoşuna gitmeyen bazı şeyler",
    "neutral": "daha durağan bir ton",
}


def _build_diary_fallback_response(
    message: str,
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> str:
    turkish = _is_turkish_message(message)

    if not entries:
        return (
            "Bu zaman aralığında bakabileceğim bir diary girişi göremiyorum. Birkaç tane yazınca dönüp birlikte üstünden geçebiliriz."
            if turkish
            else "I can't see any diary entries for that period yet. Once you've jotted a few down we can look at them together."
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
    suggestion = _build_lifestyle_suggestion(dominant_mood, dominant_emotion, turkish)

    mood_phrase = (
        (_MOOD_PHRASES_TR if turkish else _MOOD_PHRASES_EN).get(dominant_mood or "")
    )
    emotion_phrase = (
        (_EMOTION_PHRASES_TR if turkish else _EMOTION_PHRASES_EN).get(dominant_emotion or "")
    )

    if turkish:
        opener = f"Şu sıralar yazdıklarına baktım"
        body_bits: list[str] = []
        if mood_phrase:
            body_bits.append(mood_phrase)
        if emotion_phrase:
            body_bits.append(emotion_phrase)
        if body_bits:
            opener += " — " + ", ".join(body_bits) + "."
        else:
            opener += "."
        return f"{opener} {suggestion}"

    opener = "I had a look at the last few entries"
    body_bits = []
    if mood_phrase:
        body_bits.append(mood_phrase)
    if emotion_phrase:
        body_bits.append(emotion_phrase)
    if body_bits:
        opener += " — " + ", and ".join(body_bits) + "."
    else:
        opener += "."
    return f"{opener} {suggestion}"


def _build_general_fallback_response(message: str) -> str:
    if _is_turkish_message(message):
        return "Şu an AI tarafına bağlanamadım ama buradayım. Yazmaya devam edebilirsin, biraz sonra tekrar dener misin?"
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
        import google.generativeai as genai

        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        history = _load_chat_history(
            db,
            user_id=current_user.id,
            session_id=payload.session_id,
            limit=CHAT_HISTORY_TURNS,
        )

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        chat_session_obj = model.start_chat(history=history)
        result = chat_session_obj.send_message(
            _build_prompt(payload.message, context),
            request_options={"timeout": 30},
        )
        try:
            ai_text = (result.text or "").strip()
        except Exception:
            ai_text = ""

        if not ai_text:
            raise RuntimeError("Gemini returned no text response.")

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
