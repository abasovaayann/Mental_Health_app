from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.survey import BaselineSurvey
from app.schemas.survey import (
    BaselineSurveyCreate,
    BaselineSurveyResponse,
    BaselineCompleteResponse
)
from app.utils.dependencies import get_current_user
from ml.predict import predict_wellness

router = APIRouter()


@router.post("/baseline", response_model=BaselineSurveyResponse, status_code=status.HTTP_201_CREATED)
async def submit_baseline_survey(
    survey_data: BaselineSurveyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit baseline survey responses
    """
    # Check if user already has a baseline survey
    existing_survey = db.query(BaselineSurvey).filter(
        BaselineSurvey.user_id == current_user.id
    ).first()
    
    if existing_survey:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baseline survey already submitted"
        )
    
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
    Get user's baseline survey data
    """
    survey = db.query(BaselineSurvey).filter(
        BaselineSurvey.user_id == current_user.id
    ).first()
    
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline survey not found"
        )
    
    return survey


@router.get("/wellness-score")
async def get_wellness_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the ML-based wellness score for the current user.
    Uses the baseline survey answers + trained Random Forest model.
    """
    survey = db.query(BaselineSurvey).filter(
        BaselineSurvey.user_id == current_user.id
    ).first()

    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline survey not found. Please complete the assessment first."
        )

    # Build the raw answers dict from the DB record
    raw_answers = {
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

    prediction = predict_wellness(raw_answers)

    return {
        "user_id":    current_user.id,
        "prediction": prediction,
    }
