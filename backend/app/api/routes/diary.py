import asyncio
import logging
import os
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.diary import DiaryEntry
from app.models.diary_analysis import DiaryEntryAnalysis
from app.models.user import User
from app.schemas.diary import (
    DiaryEntryCreate,
    DiaryEntryUpdate,
    DiaryEntryResponse,
    DiaryStatsResponse,
    SpeechToTextResponse,
)
from app.utils.dependencies import get_current_user
from app.services.analysis_service import analyze_text

logger = logging.getLogger(__name__)

router = APIRouter()
_whisper_model = None
_whisper_model_name = None

LANGUAGE_MAP = {
    "en-US": "en",
    "ru-RU": "ru",
    "tr-TR": "tr",
}


def _get_whisper_model():
    global _whisper_model, _whisper_model_name

    if _whisper_model is not None and _whisper_model_name == settings.WHISPER_MODEL:
        return _whisper_model

    try:
        import whisper
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Whisper is not installed. Install backend requirements and restart the server.",
        ) from exc

    _whisper_model = whisper.load_model(settings.WHISPER_MODEL)
    _whisper_model_name = settings.WHISPER_MODEL
    return _whisper_model


def _audio_suffix(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        return os.path.splitext(filename)[1]

    content_type = (content_type or "").lower()
    if "ogg" in content_type:
        return ".ogg"
    if "wav" in content_type or "wave" in content_type:
        return ".wav"
    if "mp4" in content_type:
        return ".mp4"
    return ".webm"


def _ensure_ffmpeg_on_path():
    try:
        import imageio_ffmpeg
    except Exception:
        return

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_path)

    # On Windows the bundled binary is named ffmpeg-win-*.exe, not ffmpeg.exe.
    # Whisper calls "ffmpeg" by name, so create a ffmpeg.exe copy if needed.
    ffmpeg_alias = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_alias):
        import shutil
        shutil.copy2(ffmpeg_path, ffmpeg_alias)

    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if ffmpeg_dir not in path_parts:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


def _transcribe_audio(path: str, language_code: str) -> str:
    # "auto" → Whisper detects language automatically (requires a multilingual model)
    if language_code == "auto":
        if settings.WHISPER_MODEL.endswith(".en"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auto language detection requires a multilingual model. Set WHISPER_MODEL=base (or small/medium/large).",
            )
        _ensure_ffmpeg_on_path()
        result = _get_whisper_model().transcribe(path, fp16=False)
        return (result.get("text") or "").strip()

    whisper_language = LANGUAGE_MAP.get(language_code)
    if not whisper_language:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported language")

    if settings.WHISPER_MODEL.endswith(".en") and whisper_language != "en":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current Whisper model supports only English. Use tiny/base/small/medium/large for multilingual transcription.",
        )

    _ensure_ffmpeg_on_path()
    result = _get_whisper_model().transcribe(path, language=whisper_language, fp16=False)
    return (result.get("text") or "").strip()


def _serialize_tags(csv_value: str) -> list[str]:
    if not csv_value:
        return []
    return [tag for tag in csv_value.split(",") if tag]


def _save_or_refresh_analysis(db: Session, entry: DiaryEntry) -> None:
    """Run the local NLP pipeline and upsert the entry's analysis row.

    Inference failures are swallowed: a missing analysis is acceptable
    fallback (chatbot will degrade to raw-text context), but a broken
    diary write is not.
    """
    try:
        result = analyze_text(entry.content or "")
    except Exception:  # pragma: no cover — defensive
        logger.exception("[diary-analysis] inference failed for entry %s", entry.id)
        return

    existing = (
        db.query(DiaryEntryAnalysis)
        .filter(DiaryEntryAnalysis.entry_id == entry.id)
        .first()
    )

    if existing:
        existing.sentiment = result["sentiment"]
        existing.sentiment_score = result["sentiment_score"]
        existing.emotion = result["emotion"]
        existing.emotion_score = result["emotion_score"]
        existing.mood = result["mood"]
    else:
        db.add(
            DiaryEntryAnalysis(
                entry_id=entry.id,
                user_id=entry.user_id,
                sentiment=result["sentiment"],
                sentiment_score=result["sentiment_score"],
                emotion=result["emotion"],
                emotion_score=result["emotion_score"],
                mood=result["mood"],
            )
        )

    db.commit()


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

    _save_or_refresh_analysis(db, entry)

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

    content_changed = entry.content != payload.content

    entry.entry_date = payload.entry_date
    entry.title = payload.title
    entry.content = payload.content
    entry.mood = payload.mood
    entry.tags_csv = ",".join(clean_tags)
    entry.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(entry)

    if content_changed:
        _save_or_refresh_analysis(db, entry)

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

    allowed_languages = set(LANGUAGE_MAP.keys()) | {"auto"}
    if language_code not in allowed_languages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported language")

    raw_audio = await audio_file.read()
    if not raw_audio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")

    max_audio_bytes = 25 * 1024 * 1024
    if len(raw_audio) > max_audio_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file is too large")

    temp_path = None
    try:
        suffix = _audio_suffix(audio_file.filename, audio_file.content_type)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(raw_audio)
            temp_path = temp_file.name

        transcript = await asyncio.to_thread(_transcribe_audio, temp_path, language_code)
        return {"transcript": transcript}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Whisper speech recognition failed. Check that ffmpeg is installed and the audio format is supported.",
        ) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
