"""Application entry point.

Database schema and data migrations are owned by Alembic (see ``migrations/``);
run ``alembic upgrade head`` before starting the app on a new or upgraded
database. The app no longer creates tables or patches columns at import time.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.database import SessionLocal
from app.services.email_service import get_email_service
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

# Check every 5 minutes. This must stay <= the ±5-min send window in
# ReminderService.should_send_reminder, otherwise a user's chosen reminder
# time can fall between two checks and be missed for the day. Duplicate sends
# are prevented by the 23h/6d min-gap guard on UserReminder.last_sent_at.
REMINDER_INTERVAL_SECONDS = 300


async def _check_reminders_periodically() -> None:
    """Send any pending reminders every few minutes until cancelled."""
    while True:
        try:
            db = SessionLocal()
            try:
                ReminderService.send_pending_reminders(db)
            finally:
                db.close()
        except Exception:  # noqa: BLE001 — background loop must keep running
            logger.exception("Error while sending pending reminders")

        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)


async def _verify_email_credentials_on_startup() -> None:
    """Log a loud, clear message about whether reminder emails can be sent.

    Runs off the event loop so a slow SMTP handshake doesn't block startup.
    Never raises — email is an optional feature and must not stop the app.
    """
    email_service = get_email_service()
    if not email_service.is_configured():
        logger.warning(
            "[email] Reminder emails are DISABLED: EMAIL_FROM/EMAIL_PASSWORD "
            "are not configured in the environment."
        )
        return

    ok, detail = await asyncio.to_thread(email_service.verify_credentials)
    if ok:
        logger.info("[email] %s", detail)
    else:
        logger.error("[email] Reminder emails will NOT be sent: %s", detail)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and cleanly stop the background reminder task."""
    await _verify_email_credentials_on_startup()
    reminder_task = asyncio.create_task(_check_reminders_periodically())
    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Mental Health Tracking API with AI Integration",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    def root():
        """Root endpoint."""
        return {
            "message": "Welcome to MindTrackAi API",
            "version": "1.0.0",
            "docs": "/docs",
        }

    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()
