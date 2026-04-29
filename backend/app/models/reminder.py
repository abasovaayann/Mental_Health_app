"""User reminder preferences for email notifications."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Time, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class UserReminder(Base):
    """Stores user's email reminder preferences for check-ins."""

    __tablename__ = "user_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), unique=True, nullable=False)
    
    enabled = Column(Boolean, default=True, nullable=False)
    reminder_time = Column(String(5), nullable=False, default="09:00")  # HH:MM format
    reminder_timezone = Column(String(50), nullable=False, default="UTC")  # e.g., "Europe/Istanbul"
    frequency = Column(String(20), nullable=False, default="daily")  # daily, weekly

    # Timestamp of the last successful send — used to suppress duplicate firings
    # within the ±5 min match window (multiple checks would otherwise trigger
    # the same reminder multiple times).
    last_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", back_populates="reminder")

    def __repr__(self):
        return f"<UserReminder(user_id={self.user_id}, time={self.reminder_time}, enabled={self.enabled})>"
