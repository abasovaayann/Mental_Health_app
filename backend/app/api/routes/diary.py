from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diary import DiaryEntry
from app.models.user import User
from app.schemas.diary import (
    DiaryEntryCreate,
    DiaryEntryUpdate,
    DiaryEntryResponse,
    DiaryStatsResponse,
)
from app.utils.dependencies import get_current_user

router = APIRouter()


def _serialize_tags(csv_value: str) -> list[str]:
    if not csv_value:
        return []
    return [tag for tag in csv_value.split(",") if tag]


def _serialize_entry(entry: DiaryEntry) -> DiaryEntryResponse:
    return DiaryEntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        entry_date=entry.entry_date,
        title=entry.title,
        content=entry.content,
        mood=entry.mood,
        tags=_serialize_tags(entry.tags_csv),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("/entries", response_model=list[DiaryEntryResponse])
def list_entries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.user_id == current_user.id)
        .order_by(DiaryEntry.entry_date.desc(), DiaryEntry.created_at.desc())
        .all()
    )
    return [_serialize_entry(entry) for entry in entries]


@router.post("/entries", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: DiaryEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clean_tags = [tag.strip().replace("#", "") for tag in payload.tags if tag.strip()]

    entry = DiaryEntry(
        user_id=current_user.id,
        entry_date=payload.entry_date,
        title=payload.title,
        content=payload.content,
        mood=payload.mood,
        tags_csv=",".join(clean_tags),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return _serialize_entry(entry)


@router.put("/entries/{entry_id}", response_model=DiaryEntryResponse)
def update_entry(
    entry_id: int,
    payload: DiaryEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.id == entry_id, DiaryEntry.user_id == current_user.id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    clean_tags = [tag.strip().replace("#", "") for tag in payload.tags if tag.strip()]

    entry.entry_date = payload.entry_date
    entry.title = payload.title
    entry.content = payload.content
    entry.mood = payload.mood
    entry.tags_csv = ",".join(clean_tags)
    entry.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(entry)

    return _serialize_entry(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.id == entry_id, DiaryEntry.user_id == current_user.id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    db.delete(entry)
    db.commit()


@router.get("/stats", response_model=DiaryStatsResponse)
def get_diary_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(DiaryEntry.created_at)
        .filter(DiaryEntry.user_id == current_user.id)
        .order_by(DiaryEntry.created_at.desc())
        .all()
    )

    timestamps = [row[0] for row in rows if row[0] is not None]

    return {
        "total_entries": len(timestamps),
        "last_entry_at": timestamps[0] if timestamps else None,
    }
