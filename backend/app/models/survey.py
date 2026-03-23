from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, UniqueConstraint
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


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkins_user_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    checkin_date = Column(Date, nullable=False, index=True)
    mood_level = Column(Integer, nullable=False)
    sleep_quality = Column(Integer, nullable=False)
    energy_level = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
