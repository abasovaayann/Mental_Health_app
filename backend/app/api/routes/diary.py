from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diary import DiaryEntry
from app.models.user import User
from app.schemas.diary import (
    DiaryEntryCreate,
    DiaryEntryUpdate,
    DiaryEntryResponse,
    DiaryStatsResponse,
    SpeechToTextResponse,
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


@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio_file: UploadFile = File(...),
    language_code: str = Form("en-US"),
    current_user: User = Depends(get_current_user),
):
    del current_user

    allowed_languages = {"en-US", "ru-RU"}
    if language_code not in allowed_languages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported language")

    raw_audio = await audio_file.read()
    if not raw_audio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")

    max_audio_bytes = 10 * 1024 * 1024
    if len(raw_audio) > max_audio_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file is too large")

    try:
        from google.cloud import speech
        from google.auth.exceptions import DefaultCredentialsError
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Speech dependency is not installed",
        ) from exc

    content_type = (audio_file.content_type or "").lower()
    encoding = speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
    if "webm" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    elif "ogg" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS
    elif "wav" in content_type or "wave" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16

    config = speech.RecognitionConfig(
        encoding=encoding,
        language_code=language_code,
        enable_automatic_punctuation=True,
        model="latest_long",
    )
    audio = speech.RecognitionAudio(content=raw_audio)

    try:
        client = speech.SpeechClient()
        response = client.recognize(config=config, audio=audio)
    except DefaultCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google credentials are missing. Set GOOGLE_APPLICATION_CREDENTIALS "
                "to your service-account JSON path and restart backend."
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speech recognition request failed",
        ) from exc

    transcript_parts = []
    for result in response.results:
        if result.alternatives:
            transcript_parts.append(result.alternatives[0].transcript.strip())

    transcript = " ".join(part for part in transcript_parts if part).strip()
    return {"transcript": transcript}
