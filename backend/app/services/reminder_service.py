"""Service for managing check-in reminders."""

from datetime import datetime, time, timedelta
import pytz
from sqlalchemy.orm import Session
from app.models.reminder import UserReminder
from app.models.user import User
from app.services.email_service import get_email_service
import logging

logger = logging.getLogger(__name__)

# Minimum gap between two sends for the same reminder, by frequency.
# Daily reminders use 23h (not 24h) so a slightly-early check the next day
# still fires; weekly uses 6 days for the same reason.
_MIN_GAP_BY_FREQUENCY = {
    "daily": timedelta(hours=23),
    "weekly": timedelta(days=6),
}


class ReminderService:
    """Manage user reminders and send check-in emails."""

    @staticmethod
    def get_or_create_reminder(user_id: int, db: Session) -> UserReminder:
        """Get existing reminder or create default one."""
        reminder = db.query(UserReminder).filter(UserReminder.user_id == user_id).first()
        
        if not reminder:
            reminder = UserReminder(
                user_id=user_id,
                enabled=True,
                reminder_time="09:00",
                reminder_timezone="UTC",
                frequency="daily",
            )
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
        
        return reminder

    @staticmethod
    def update_reminder(
        user_id: int,
        enabled: bool = None,
        reminder_time: str = None,
        reminder_timezone: str = None,
        frequency: str = None,
        db: Session = None,
    ) -> UserReminder:
        """Update user's reminder preferences."""
        reminder = ReminderService.get_or_create_reminder(user_id, db)
        
        if enabled is not None:
            reminder.enabled = enabled
        if reminder_time is not None:
            reminder.reminder_time = reminder_time
        if reminder_timezone is not None:
            reminder.reminder_timezone = reminder_timezone
        if frequency is not None:
            reminder.frequency = frequency
        
        db.commit()
        db.refresh(reminder)
        logger.info(f"✓ Updated reminder for user {user_id}")
        return reminder

    @staticmethod
    def should_send_reminder(user_reminder: UserReminder) -> bool:
        """Check if it's time to send reminder to this user."""

        if not user_reminder.enabled:
            return False

        # Suppress duplicate firings within the same period — the ±5 min match
        # window otherwise lets a single reminder qualify across multiple checks.
        if user_reminder.last_sent_at is not None:
            min_gap = _MIN_GAP_BY_FREQUENCY.get(
                user_reminder.frequency, timedelta(hours=23)
            )
            if datetime.utcnow() - user_reminder.last_sent_at < min_gap:
                return False

        try:
            # Parse reminder time (HH:MM format)
            reminder_hour, reminder_minute = map(int, user_reminder.reminder_time.split(":"))
            reminder_time_obj = time(hour=reminder_hour, minute=reminder_minute)

            # Get user's timezone
            tz = pytz.timezone(user_reminder.reminder_timezone)

            # Get current time in user's timezone
            now_utc = datetime.now(pytz.UTC)
            now_user_tz = now_utc.astimezone(tz)

            # Check if current time is within 5 minutes of reminder time
            # (allows some flexibility for when the job runs)
            current_time = now_user_tz.time()
            time_diff = abs(
                (datetime.combine(datetime.today(), current_time).timestamp() -
                 datetime.combine(datetime.today(), reminder_time_obj).timestamp())
            )

            # Send if within 5 minutes of scheduled time
            return time_diff <= 300  # 300 seconds = 5 minutes

        except Exception as e:
            logger.error(f"Error checking reminder time for user {user_reminder.user_id}: {e}")
            return False

    @staticmethod
    def send_pending_reminders(db: Session) -> dict:
        """Check all users and send pending reminders."""
        
        # Get all active reminders. Unverified emails are skipped so reminders
        # never go to an address the user hasn't proven they own.
        active_reminders = (
            db.query(UserReminder)
            .join(User)
            .filter(
                UserReminder.enabled == True,
                User.is_active == True,
                User.is_verified == True,
            )
            .all()
        )
        
        email_service = get_email_service()
        sent_count = 0
        failed_count = 0
        
        for reminder in active_reminders:
            if ReminderService.should_send_reminder(reminder):
                user = reminder.user

                # Send email
                success = email_service.send_reminder_email(
                    recipient_email=user.email,
                    user_name=user.first_name,
                    check_in_link="http://localhost:3000/diary",  # TODO: Use config URL
                )

                if success:
                    sent_count += 1
                    reminder.last_sent_at = datetime.utcnow()
                else:
                    failed_count += 1

        if sent_count:
            db.commit()
        
        logger.info(f"Reminder check complete: {sent_count} sent, {failed_count} failed")
        return {
            "sent": sent_count,
            "failed": failed_count,
            "checked": len(active_reminders),
        }
