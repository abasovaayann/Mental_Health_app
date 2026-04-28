import json
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.chat_message import ChatMessage
from app.models.diary import DiaryEntry
from app.models.diary_analysis import DiaryEntryAnalysis
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter()

SYSTEM_PROMPT = """You are a supportive lifestyle companion integrated into MindTrackAI, a personal diary app.

Your role is to analyze the user's diary entries and provide:
- Observations about recurring themes, emotions, topics, and patterns in their writing
- Hobby, activity, and lifestyle suggestions based on what they write about
- Encouragement and positive reinforcement
- Summaries like "This week you wrote mostly about X" or "Today Y seemed to influence you most"

STRICT BOUNDARIES:
- You are NOT a doctor, therapist, or medical professional
- Do NOT provide medical advice, diagnoses, or treatment recommendations
- Do NOT suggest medications or clinical interventions
- Focus ONLY on lifestyle, hobbies, activities, daily habits, and observable patterns in writing
- Be warm, curious, and non-judgmental
- Keep responses concise (3-5 sentences) unless the user asks for more detail
- Always respond in the SAME LANGUAGE as the user's message — Turkish if the message is in Turkish, Russian if Russian, English if English
- If no entries exist for the period, kindly let the user know there is nothing to analyze yet"""


class ChatRequest(BaseModel):
    message: str
    mode: str = "general"
    date: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    used_analysis_memory: bool = False


class HistoryResponse(BaseModel):
    messages: list[dict]


def _build_context_from_analyses(
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> tuple[str, bool]:
    analyzed_count = sum(1 for e in entries if e.id in analyses)
    use_memory = analyzed_count > 0

    lines = []
    for entry in entries:
        analysis = analyses.get(entry.id)
        if analysis and analysis.summary:
            themes = []
            if analysis.key_themes_json:
                try:
                    themes = json.loads(analysis.key_themes_json)
                except Exception:
                    pass
            themes_str = ", ".join(themes) if themes else "none"
            lines.append(
                f"[{entry.entry_date}] Mood: {analysis.mood_detected or entry.mood} | "
                f"Themes: {themes_str} | Summary: {analysis.summary}"
            )
        else:
            snippet = (entry.content or "")[:300]
            lines.append(
                f"[{entry.entry_date}] Mood: {entry.mood} | "
                f"Title: {entry.title or 'Untitled'} | Content: {snippet}"
            )

    if not lines:
        return "The user has no diary entries for the selected period.", False

    header = "Pre-analyzed diary memory:" if use_memory else "User's diary entries:"
    return header + "\n\n" + "\n\n".join(lines), use_memory


@router.get("/history", response_model=HistoryResponse)
def get_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    messages = [
        {"role": r.role, "text": r.content, "mode": r.mode}
        for r in reversed(rows)
    ]
    return {"messages": messages}


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
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

    context, used_memory = _build_context_from_analyses(entries, analyses)

    # Save user message
    db.add(ChatMessage(user_id=current_user.id, role="user", content=payload.message, mode=payload.mode))
    db.commit()

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        result = model.generate_content(
            f"{context}\n\nUser message: {payload.message}"
        )
        ai_text = result.text

        # Save assistant response
        db.add(ChatMessage(user_id=current_user.id, role="assistant", content=ai_text, mode=payload.mode))
        db.commit()

        return ChatResponse(response=ai_text, used_analysis_memory=used_memory)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable. Please try again later.",
        ) from exc
