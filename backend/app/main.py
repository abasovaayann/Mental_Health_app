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
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

REMINDER_INTERVAL_SECONDS = 3600


async def _check_reminders_periodically() -> None:
    """Send any pending reminders once per hour until cancelled."""
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and cleanly stop the background reminder task."""
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
