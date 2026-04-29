"""API endpoints for managing email reminders."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.dependencies import get_current_user
from services.reminder_service import ReminderService

router = APIRouter()


# Pydantic schemas
class ReminderPreferencesResponse(BaseModel):
    enabled: bool
    reminder_time: str  # HH:MM
    reminder_timezone: str
    frequency: str

    class Config:
        from_attributes = True


class ReminderPreferencesUpdate(BaseModel):
    enabled: bool = Field(None, description="Enable/disable reminders")
    reminder_time: str = Field(None, pattern=r"^\d{2}:\d{2}$", description="HH:MM format")
    reminder_timezone: str = Field(None, description="e.g., Europe/Istanbul, America/New_York")
    frequency: str = Field(None, description="daily or weekly")


# Routes
@router.get("/preferences", response_model=ReminderPreferencesResponse)
def get_reminder_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's reminder preferences."""
    reminder = ReminderService.get_or_create_reminder(current_user.id, db)
    return ReminderPreferencesResponse(
        enabled=reminder.enabled,
        reminder_time=reminder.reminder_time,
        reminder_timezone=reminder.reminder_timezone,
        frequency=reminder.frequency,
    )


@router.put("/preferences", response_model=ReminderPreferencesResponse)
def update_reminder_preferences(
    payload: ReminderPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user's reminder preferences."""
    
    # Validate timezone if provided
    if payload.reminder_timezone:
        try:
            import pytz
            pytz.timezone(payload.reminder_timezone)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timezone: {payload.reminder_timezone}",
            )
    
    reminder = ReminderService.update_reminder(
        user_id=current_user.id,
        enabled=payload.enabled,
        reminder_time=payload.reminder_time,
        reminder_timezone=payload.reminder_timezone,
        frequency=payload.frequency,
        db=db,
    )
    
    return ReminderPreferencesResponse(
        enabled=reminder.enabled,
        reminder_time=reminder.reminder_time,
        reminder_timezone=reminder.reminder_timezone,
        frequency=reminder.frequency,
    )


@router.delete("/preferences", status_code=status.HTTP_204_NO_CONTENT)
def disable_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable all reminders for user."""
    ReminderService.update_reminder(
        user_id=current_user.id,
        enabled=False,
        db=db,
    )
