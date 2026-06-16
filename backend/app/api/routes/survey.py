from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.survey import BaselineSurvey, DailyCheckin
from app.schemas.survey import (
    BaselineSurveyCreate,
    BaselineSurveyResponse,
    BaselineCompleteResponse,
    DailyCheckinUpsert,
    DailyCheckinResponse,
)
from app.utils.dependencies import get_current_user
from ml.predict import predict_wellness

router = APIRouter()


def _survey_raw_answers(survey: BaselineSurvey) -> dict:
    """Map a BaselineSurvey row to the raw answers dict the ML model expects."""
    return {
        "sleep_duration":            survey.sleep_duration,
        "energy_level":              survey.energy_level,
        "academic_pressure":         survey.academic_pressure,
        "study_motivation":          survey.study_motivation,
        "concentration_difficulty":  survey.concentration_difficulty,
        "morning_mood":              survey.morning_mood,
        "emotional_low":             survey.emotional_low,
        "anxiety_level":             survey.anxiety_level,
        "social_support":            survey.social_support,
        "financial_stress":          survey.financial_stress,
    }


@router.get("/daily-checkins", response_model=list[DailyCheckinResponse])
async def list_daily_checkins(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(DailyCheckin)
        .filter(DailyCheckin.user_id == current_user.id)
        .order_by(DailyCheckin.checkin_date.desc())
        .all()
    )
    return rows


@router.put("/daily-checkin", response_model=DailyCheckinResponse)
async def upsert_daily_checkin(
    payload: DailyCheckinUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = (
        db.query(DailyCheckin)
        .filter(
            DailyCheckin.user_id == current_user.id,
            DailyCheckin.checkin_date == payload.checkin_date,
        )
        .first()
    )

    if existing:
        # Daily check-in is intentionally one-shot per day. Once saved, the
        # row is immutable until the next calendar day.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Daily check-in for this date has already been saved.",
        )

    row = DailyCheckin(
        user_id=current_user.id,
        checkin_date=payload.checkin_date,
        mood_level=payload.mood_level,
        sleep_quality=payload.sleep_quality,
        energy_level=payload.energy_level,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/baseline", response_model=BaselineSurveyResponse, status_code=status.HTTP_201_CREATED)
async def submit_baseline_survey(
    survey_data: BaselineSurveyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a survey. Users may take the survey more than once; each submission
    is stored as a new row so the dashboard can show a full history of results.
    """
    # Create new survey
    new_survey = BaselineSurvey(
        user_id=current_user.id,
        **survey_data.model_dump()
    )
    
    db.add(new_survey)
    db.commit()
    db.refresh(new_survey)
    
    return new_survey


@router.post("/complete-baseline", response_model=BaselineCompleteResponse)
async def complete_baseline(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark user's baseline as completed
    """
    # Verify survey exists
    survey = db.query(BaselineSurvey).filter(
        BaselineSurvey.user_id == current_user.id
    ).first()
    
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Please submit baseline survey first"
        )
    
    # Update user's baseline status
    current_user.baseline_completed = True
    current_user.baseline_completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Baseline assessment completed successfully",
        "baseline_completed": current_user.baseline_completed,
        "baseline_completed_at": current_user.baseline_completed_at
    }


@router.get("/baseline", response_model=BaselineSurveyResponse)
async def get_baseline_survey(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's most recent survey.
    """
    survey = (
        db.query(BaselineSurvey)
        .filter(BaselineSurvey.user_id == current_user.id)
        .order_by(BaselineSurvey.created_at.desc(), BaselineSurvey.id.desc())
        .first()
    )

    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline survey not found"
        )

    return survey


@router.get("/history")
async def get_survey_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Return every survey the user has taken (newest first), each with its
    computed wellness prediction, so the dashboard can show current and past
    results together.
    """
    surveys = (
        db.query(BaselineSurvey)
        .filter(BaselineSurvey.user_id == current_user.id)
        .order_by(BaselineSurvey.created_at.desc(), BaselineSurvey.id.desc())
        .all()
    )

    history = []
    for survey in surveys:
        try:
            prediction = predict_wellness(_survey_raw_answers(survey))
        except Exception:  # noqa: BLE001 — a bad row must not break the list
            prediction = None
        history.append({
            "id": survey.id,
            "created_at": survey.created_at,
            "answers": _survey_raw_answers(survey),
            "prediction": prediction,
        })

    return {"count": len(history), "surveys": history}


@router.get("/wellness-score")
async def get_wellness_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the ML-based wellness score for the current user.
    Uses the baseline survey answers + trained Random Forest model.
    """
    survey = (
        db.query(BaselineSurvey)
        .filter(BaselineSurvey.user_id == current_user.id)
        .order_by(BaselineSurvey.created_at.desc(), BaselineSurvey.id.desc())
        .first()
    )

    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline survey not found. Please complete the assessment first."
        )

    # Build the raw answers dict from the latest survey record
    raw_answers = _survey_raw_answers(survey)

    prediction = predict_wellness(raw_answers)

    return {
        "user_id":    current_user.id,
        "prediction": prediction,
    }


@router.get("/activity-stats")
async def get_activity_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Return lightweight dashboard activity metrics.
    """
    rows = db.query(BaselineSurvey.created_at).filter(
        BaselineSurvey.user_id == current_user.id
    ).order_by(BaselineSurvey.created_at.desc()).all()

    timestamps = [row[0] for row in rows if row[0] is not None]
    unique_dates = sorted({stamp.date() for stamp in timestamps}, reverse=True)

    current_streak = 0
    if unique_dates:
        today = datetime.utcnow().date()
        expected_day = today if unique_dates[0] == today else unique_dates[0]

        for day in unique_dates:
            if day == expected_day:
                current_streak += 1
                expected_day = expected_day - timedelta(days=1)
            elif day < expected_day:
                break

    return {
        "total_entries": len(timestamps),
        "current_streak": current_streak,
        "last_entry_at": timestamps[0] if timestamps else None,
    }
