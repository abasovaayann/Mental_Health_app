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

SYSTEM_PROMPT = """You are a supportive lifestyle companion integrated into MindTrackAI, a personal diary app.

Each diary entry shown to you has been pre-analyzed by a local NLP pipeline. Each line carries:
- mood = low | medium | high   (a normalized wellness bucket)
- emotion = joy | sadness | anger | fear | disgust | surprise | neutral
- sentiment = positive | negative
Treat these signals as factual observations about the user's writing. Do NOT re-classify or contradict them — your job is to weave them into a warm, human response.

Your role:
- Observe recurring themes, emotions, and patterns across entries
- Suggest hobbies, activities, and lifestyle ideas grounded in what the user writes about
- Offer encouragement and reflect positive moments back to the user
- Produce summaries like "This week your mood trended {high/low} with {emotion} showing up most"

STRICT BOUNDARIES:
- You are NOT a doctor, therapist, or medical professional
- Do NOT provide medical advice, diagnoses, or treatment recommendations
- Do NOT suggest medications or clinical interventions
- Focus ONLY on lifestyle, hobbies, activities, daily habits, and observable patterns
- Be warm, curious, and non-judgmental
- Keep responses concise (3-5 sentences) unless the user asks for more detail
- Always respond in the SAME LANGUAGE as the user's message — Turkish if Turkish, Russian if Russian, English if English
- If no entries exist for the period, kindly let the user know there is nothing to analyze yet"""


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
            lines.append(
                f"[{entry.entry_date}] mood={analysis.mood} | "
                f"emotion={analysis.emotion} ({analysis.emotion_score:.2f}) | "
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


@router.post("/sessions", response_model=ChatSessionListItem, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id, ChatMessage.session_id == session_id)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id, ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured.",
        )

    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

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

    entry_ids = [e.id for e in entries]
    analyses: dict[int, DiaryEntryAnalysis] = {}
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
        .filter(ChatMessage.user_id == current_user.id, ChatMessage.session_id == payload.session_id)
        .count()
    )
    if existing_messages == 0 and (chat_session.title == "New Chat" or chat_session.title == "Legacy conversation"):
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

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        result = model.generate_content(
            f"{context}\n\nUser message: {payload.message}"
        )
        ai_text = result.text

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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable. Please try again later.",
        ) from exc
