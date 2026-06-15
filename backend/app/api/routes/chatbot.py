"""Chatbot routes: chat sessions and the diary-aware chat endpoint.

This module is intentionally thin. The heavy lifting lives in dedicated,
independently testable modules:
  - nlp.language          → language detection
  - services.chat_intent  → diary-context gating + comparison detection
  - services.chat_context → diary context block builders
  - services.chat_llm     → Claude call, prompt assembly, history, fallbacks
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.diary import DiaryEntry
from app.models.diary_analysis import DiaryEntryAnalysis
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionListItem,
    ChatSessionListResponse,
)
from app.utils.dependencies import get_current_user
from app.services.chat_context import build_comparison_context, build_context
from app.services.chat_intent import detect_comparison_intent, should_use_diary_context
from app.services.chat_llm import (
    CHAT_HISTORY_TURNS,
    build_diary_fallback_response,
    build_general_fallback_response,
    build_prompt,
    call_claude,
    load_chat_history,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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


def _load_analyses(
    db: Session, entries: list[DiaryEntry]
) -> dict[int, DiaryEntryAnalysis]:
    entry_ids = [entry.id for entry in entries]
    if not entry_ids:
        return {}
    rows = (
        db.query(DiaryEntryAnalysis)
        .filter(DiaryEntryAnalysis.entry_id.in_(entry_ids))
        .all()
    )
    return {row.entry_id: row for row in rows}


def _gather_diary_context(
    db: Session, *, user_id: int, message: str, mode: str, target_date: date
) -> tuple[Optional[str], bool, list[DiaryEntry], dict[int, DiaryEntryAnalysis]]:
    """Fetch diary entries + analyses for this turn and build the context block.

    Returns (context, used_memory, entries, analyses). entries/analyses are
    returned so the caller can reuse them for the offline fallback path.
    """
    comparison = detect_comparison_intent(message, target_date)

    if comparison:
        period_a, period_b = comparison
        start_a, end_a, _ = period_a
        start_b, end_b, _ = period_b

        entries_a = (
            db.query(DiaryEntry)
            .filter(
                DiaryEntry.user_id == user_id,
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
                DiaryEntry.user_id == user_id,
                DiaryEntry.entry_date >= start_b,
                DiaryEntry.entry_date <= end_b,
            )
            .order_by(DiaryEntry.entry_date.desc())
            .limit(20)
            .all()
        )
        entries = entries_a + entries_b
        analyses = _load_analyses(db, entries)
        context, used_memory = build_comparison_context(
            period_a, entries_a, period_b, entries_b, analyses
        )
        return context, used_memory, entries, analyses

    query = db.query(DiaryEntry).filter(DiaryEntry.user_id == user_id)
    if mode == "daily":
        query = query.filter(DiaryEntry.entry_date == target_date)
    elif mode == "weekly":
        week_start = target_date - timedelta(days=6)
        query = query.filter(
            DiaryEntry.entry_date >= week_start,
            DiaryEntry.entry_date <= target_date,
        )
    else:
        month_start = target_date - timedelta(days=30)
        query = query.filter(DiaryEntry.entry_date >= month_start)

    entries = query.order_by(DiaryEntry.entry_date.desc()).limit(20).all()
    analyses = _load_analyses(db, entries)
    context, used_memory = build_context(entries, analyses)
    return context, used_memory, entries, analyses


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

    include_diary_context = should_use_diary_context(payload.message, payload.mode)
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

        context, used_memory, entries, analyses = _gather_diary_context(
            db,
            user_id=current_user.id,
            message=payload.message,
            mode=payload.mode,
            target_date=target_date,
        )

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
        history = load_chat_history(
            db,
            user_id=current_user.id,
            session_id=payload.session_id,
            limit=CHAT_HISTORY_TURNS,
        )
        # Build the final user turn with diary context (if any) inlined.
        history.append(
            {"role": "user", "content": build_prompt(payload.message, context)}
        )

        ai_text = call_claude(history)

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
    except Exception:
        logger.exception("Chatbot fallback triggered")
        ai_text = (
            build_diary_fallback_response(payload.message, entries, analyses)
            if include_diary_context
            else build_general_fallback_response(payload.message)
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
