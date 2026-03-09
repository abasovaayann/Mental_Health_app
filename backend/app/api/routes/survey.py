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
