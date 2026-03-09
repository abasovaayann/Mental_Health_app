from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class BaselineSurvey(Base):
    __tablename__ = "baseline_surveys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False)
    
    # Section 1: Sleep & Physical State
    sleep_duration = Column(String, nullable=False)
    energy_level = Column(String, nullable=False)
    
    # Section 2: Academic & Daily Life
    academic_pressure = Column(String, nullable=False)
    study_motivation = Column(String, nullable=False)
    concentration_difficulty = Column(String, nullable=False)
    
    # Section 3: Emotional Well-Being
    morning_mood = Column(String, nullable=False)
    emotional_low = Column(String, nullable=False)
    anxiety_level = Column(String, nullable=False)
    
    # Section 4: Social & External Factors
    social_support = Column(String, nullable=False)
    financial_stress = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
