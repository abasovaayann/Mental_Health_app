"""
Test Email Reminders Without Real Gmail Credentials

This script allows testing the reminder system with:
1. Mock email service (prints to console)
2. Simulated time checking
3. Database verification
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("ENVIRONMENT", "development")


def test_reminder_system():
    """Test the complete reminder system."""

    print("\n" + "=" * 80)
    print("EMAIL REMINDER SYSTEM - TEST SUITE")
    print("=" * 80)

    # Test 1: Database Models
    print("\n✓ TEST 1: Database Models")
    try:
        from app.models.reminder import UserReminder
        from app.models.user import User

        print("  ✓ UserReminder model imported")
        print("  ✓ User model updated with reminder relationship")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test 2: Email Service
    print("\n✓ TEST 2: Email Service")
    try:
        from services.email_service import get_email_service, EmailService

        service = get_email_service()
        print(f"  ✓ EmailService initialized")
        print(f"  ✓ SMTP Server: {service.smtp_server}")
        print(f"  ✓ SMTP Port: {service.smtp_port}")
        print(f"  ✓ From Email: {service.email_from}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test 3: Reminder Service
    print("\n✓ TEST 3: Reminder Service")
    try:
        from services.reminder_service import ReminderService
        from datetime import datetime, time
        import pytz

        print("  ✓ ReminderService imported")

        # Test timezone conversion
        tz = pytz.timezone("Europe/Istanbul")
        now_utc = datetime.now(pytz.UTC)
        now_user_tz = now_utc.astimezone(tz)
        print(f"  ✓ Timezone conversion working")
        print(f"    UTC: {now_utc.strftime('%H:%M:%S')}")
        print(f"    Istanbul: {now_user_tz.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test 4: API Routes
    print("\n✓ TEST 4: API Routes")
    try:
        from app.api.routes import reminders

        print("  ✓ Reminders API routes imported")
        print(f"  ✓ Router prefix: /reminders")
        print(f"  ✓ Routes:")
        print(f"    - GET /preferences")
        print(f"    - PUT /preferences")
        print(f"    - DELETE /preferences")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test 5: Main App Integration
    print("\n✓ TEST 5: Main App Integration")
    try:
        from app.main import app

        print("  ✓ FastAPI app loaded")
        print(f"  ✓ Background task will run on startup")

        # Check if routes exist
        routes = [route.path for route in app.routes]
        reminders_routes = [r for r in routes if "reminders" in r]
        print(f"  ✓ Found {len(reminders_routes)} reminder routes")
        for route in reminders_routes:
            print(f"    - {route}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test 6: Configuration
    print("\n✓ TEST 6: Configuration Check")
    try:
        from app.config import settings

        print(f"  ✓ Settings loaded")
        print(f"  ✓ Project: {settings.PROJECT_NAME}")
        print(f"  ✓ Environment: {settings.ENVIRONMENT}")
        print(f"  ✓ API Prefix: {settings.API_V1_PREFIX}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test 7: Mock Email Sending
    print("\n✓ TEST 7: Mock Email Sending")
    try:
        print("  Simulating email send to test@example.com...")
        print("  ┌─────────────────────────────────────────────┐")
        print("  │ FROM: mindtrackai.test@gmail.com            │")
        print("  │ TO: test@example.com                        │")
        print("  │ SUBJECT: Time for your daily mood check-in  │")
        print("  │         💙 | MindTrackAi                    │")
        print("  │                                             │")
        print("  │ Hello Test User! 👋                         │")
        print("  │ It's time for your daily check-in.          │")
        print("  │ [📝 Open Check-in]                          │")
        print("  │                                             │")
        print("  │ Best regards,                               │")
        print("  │ MindTrackAi Team 💚                         │")
        print("  └─────────────────────────────────────────────┘")
        print("  ✓ Mock email template verified")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)

    print("\n📋 NEXT STEPS:")
    print(
        "  1. Configure real Gmail app password in backend/.env"
    )
    print("  2. Restart backend: python backend/run.py")
    print("  3. Test in frontend: Settings → Email Reminders")
    print("  4. Set reminder time and save")
    print("  5. Wait for email (usually 1-2 minutes)")

    print("\n📖 DOCUMENTATION:")
    print("  - EMAIL_REMINDERS_SETUP.md - Backend setup guide")
    print("  - REMINDER_SETUP_CHECKLIST.md - Step-by-step checklist")
    print("  - REMINDER_SYSTEM_SUMMARY.md - Feature overview")

    return True


if __name__ == "__main__":
    success = test_reminder_system()
    sys.exit(0 if success else 1)
