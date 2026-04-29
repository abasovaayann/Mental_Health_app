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

SYSTEM_PROMPT = """You are a supportive lifestyle companion integrated into MindTrackAI.

Sometimes you will receive diary-entry context gathered from the app. When that
context is provided, it may include local NLP labels:
- mood = low | medium | high
- emotion = joy | sadness | anger | fear | disgust | surprise | neutral
- sentiment = positive | negative

Important behavior:
- If diary context is provided, use it carefully and treat those labels as
  factual observations about the user's writing.
- If diary context is NOT provided, behave like a normal supportive chatbot and
  do NOT bring up diary entries on your own.
- Never pretend you analyzed entries if no diary context was supplied for this
  turn.

Your role:
- Be warm, curious, supportive, and non-judgmental
- Answer normal conversation naturally when the user is chatting casually
- When diary context is present, you may observe recurring themes, emotions,
  and patterns across entries
- Suggest hobbies, activities, and daily-habit ideas grounded in what the user
  shares

STRICT BOUNDARIES:
- You are NOT a doctor, therapist, or medical professional
- Do NOT provide medical advice, diagnoses, or treatment recommendations
- Do NOT suggest medications or clinical interventions
- Focus on supportive conversation, lifestyle ideas, habits, and observable
  patterns
- Keep responses concise (3-5 sentences) unless the user asks for more detail
- Always respond in the SAME LANGUAGE as the user's message
- If the user asks for diary analysis but no entries exist for the requested
  period, kindly say there is nothing to analyze yet"""

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

_GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "hey there",
    "hiya",
    "merhaba",
    "selam",
    "selamlar",
    "привет",
    "здравствуй",
    "здравствуйте",
    "добрый день",
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
    return bool(words & _ANALYSIS_HINT_WORDS) and bool(words & _MEMORY_HINT_WORDS)


def _normalize_message(message: str) -> str:
    return " ".join((message or "").strip().lower().split())


def _is_greeting_message(message: str) -> bool:
    normalized = _normalize_message(message)
    if not normalized:
        return False

    if normalized in _GREETING_WORDS:
        return True

    words = normalized.replace("!", " ").replace("?", " ").replace(",", " ").split()
    return len(words) <= 4 and bool(words) and (
        " ".join(words) in _GREETING_WORDS or words[0] in _GREETING_WORDS
    )


def _build_greeting_response(message: str) -> str:
    normalized = _normalize_message(message)

    if any(token in normalized for token in ("merhaba", "selam")):
        return "Merhaba! Buradayım. İstersen sadece sohbet edebiliriz ya da aklındaki bir konuda sana yardımcı olabilirim."

    if any(token in normalized for token in ("привет", "здравствуй", "здравствуйте", "добрый")):
        return "Привет! Я рядом. Можем просто поговорить, или ты можешь написать, с чем хочешь помочь."

    return "Hi! I'm here with you. We can just chat, or you can tell me what you'd like help with."


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


def _build_diary_fallback_response(
    message: str,
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> str:
    turkish = _is_turkish_message(message)

    if not entries:
        return (
            "Bu donem icin analiz edebilecegim bir diary entry bulamadim. Birkac entry eklendikten sonra sana ozet ve pattern cikarmaya yardimci olabilirim."
            if turkish
            else "I do not have any diary entries for that period yet, so there is nothing to summarize right now. Once you add a few entries, I can help spot patterns."
        )

    mood_counts: dict[str, int] = {}
    emotion_counts: dict[str, int] = {}
    sentiment_counts: dict[str, int] = {}

    for entry in entries:
        analysis = analyses.get(entry.id)
        mood_value = (analysis.mood if analysis and analysis.mood else entry.mood or "").strip().lower()
        emotion_value = (analysis.emotion if analysis and analysis.emotion else "").strip().lower()
        sentiment_value = (analysis.sentiment if analysis and analysis.sentiment else "").strip().lower()

        if mood_value:
            mood_counts[mood_value] = mood_counts.get(mood_value, 0) + 1
        if emotion_value:
            emotion_counts[emotion_value] = emotion_counts.get(emotion_value, 0) + 1
        if sentiment_value:
            sentiment_counts[sentiment_value] = sentiment_counts.get(sentiment_value, 0) + 1

    dominant_mood = _pick_top_label(mood_counts)
    dominant_emotion = _pick_top_label(emotion_counts)
    dominant_sentiment = _pick_top_label(sentiment_counts)
    recent_titles = [entry.title or "Untitled" for entry in entries[:2]]
    suggestion = _build_lifestyle_suggestion(dominant_mood, dominant_emotion, turkish)

    if turkish:
        parts = [
            f"Son {len(entries)} entry'ye gore genel olarak tekrar eden bir tema gorunuyor."
        ]
        if dominant_mood:
            parts.append(f"En baskin mood: {dominant_mood}.")
        if dominant_emotion:
            parts.append(f"En sik emotion: {dominant_emotion}.")
        if dominant_sentiment:
            parts.append(f"Genel sentiment daha cok {dominant_sentiment} tarafinda.")
        if recent_titles:
            parts.append(f"One cikan basliklar: {', '.join(recent_titles)}.")
        parts.append(suggestion)
        return " ".join(parts)

    parts = [f"Looking across your last {len(entries)} entries, there is a recurring pattern in how you have been feeling."]
    if dominant_mood:
        parts.append(f"The strongest mood signal is {dominant_mood}.")
    if dominant_emotion:
        parts.append(f"The most frequent emotion label is {dominant_emotion}.")
    if dominant_sentiment:
        parts.append(f"Overall sentiment leans more {dominant_sentiment}.")
    if recent_titles:
        parts.append(f"Recent entries like {', '.join(recent_titles)} help reinforce that pattern.")
    parts.append(suggestion)
    return " ".join(parts)


def _build_general_fallback_response(message: str) -> str:
    if _is_turkish_message(message):
        return "Su anda AI servisine ulasamiyorum ama buradayim. Istersen kisa ve net yaz; ben de elimden geldigi kadar destek olayim."
    return "I cannot reach the AI service right now, but I am still here with you. If you want, send a shorter message and I will do my best to help."


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
        if not include_diary_context and _is_greeting_message(payload.message):
            ai_text = _build_greeting_response(payload.message)
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
            return ChatResponse(response=ai_text, used_analysis_memory=False)

        import google.generativeai as genai

        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        result = model.generate_content(
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
