from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BaselineSurveyCreate(BaseModel):
    """Schema for creating a baseline survey"""
    sleep_duration: str = Field(..., description="Sleep duration (1-5 scale)")
    energy_level: str = Field(..., description="Energy level during the day")
    academic_pressure: str = Field(..., description="Frequency of academic pressure")
    study_motivation: str = Field(..., description="Motivation level to study")
    concentration_difficulty: str = Field(..., description="Difficulty concentrating")
    morning_mood: str = Field(..., description="Mood when waking up")
    emotional_low: str = Field(..., description="Frequency of feeling emotionally low")
    anxiety_level: str = Field(..., description="Frequency of anxiety or worry")
    social_support: str = Field(..., description="Level of social support")
    financial_stress: str = Field(..., description="Level of financial stress")

    class Config:
        json_schema_extra = {
            "example": {
                "sleep_duration": "4",
                "energy_level": "Moderate",
                "academic_pressure": "Often",
                "study_motivation": "Motivated",
                "concentration_difficulty": "Moderately difficult",
                "morning_mood": "Neutral",
                "emotional_low": "Sometimes",
                "anxiety_level": "Sometimes",
                "social_support": "Moderately",
                "financial_stress": "Moderate"
            }
        }


class BaselineSurveyResponse(BaseModel):
    """Schema for baseline survey response"""
    id: int
    user_id: int
    sleep_duration: str
    energy_level: str
    academic_pressure: str
    study_motivation: str
    concentration_difficulty: str
    morning_mood: str
    emotional_low: str
    anxiety_level: str
    social_support: str
    financial_stress: str
    created_at: datetime

    class Config:
        from_attributes = True


class BaselineSurveyUpdate(BaseModel):
    """Schema for updating a baseline survey"""
    sleep_duration: Optional[str] = None
    energy_level: Optional[str] = None
    academic_pressure: Optional[str] = None
    study_motivation: Optional[str] = None
    concentration_difficulty: Optional[str] = None
    morning_mood: Optional[str] = None
    emotional_low: Optional[str] = None
    anxiety_level: Optional[str] = None
    social_support: Optional[str] = None
    financial_stress: Optional[str] = None


class BaselineCompleteResponse(BaseModel):
    """Schema for baseline completion response"""
    message: str
    baseline_completed: bool
    baseline_completed_at: datetime

    class Config:
        from_attributes = True
