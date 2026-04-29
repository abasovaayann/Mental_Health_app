from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.api.router import api_router
from app.database import engine, Base, SessionLocal
import app.models  # noqa: F401 — registers all models with Base before create_all
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession

# Create database tables
Base.metadata.create_all(bind=engine)


def ensure_schema_compatibility() -> None:
    # Keep older local databases compatible with newer models without manual migration.
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS app_users
                ADD COLUMN IF NOT EXISTS preferences_json TEXT NOT NULL DEFAULT '{}'
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS chat_messages
                ADD COLUMN IF NOT EXISTS session_id INTEGER
                """
            )
        )

    _migrate_legacy_chat_messages()


def _migrate_legacy_chat_messages() -> None:
    """Move old messages into per-user legacy sessions."""
    db = SessionLocal()
    try:
        legacy_user_ids = [
            row[0]
            for row in db.query(ChatMessage.user_id)
            .filter(ChatMessage.session_id.is_(None))
            .distinct()
            .all()
        ]
        for user_id in legacy_user_ids:
            legacy_session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user_id, ChatSession.title == "Legacy conversation")
                .order_by(ChatSession.id.asc())
                .first()
            )
            if not legacy_session:
                legacy_session = ChatSession(user_id=user_id, title="Legacy conversation")
                db.add(legacy_session)
                db.flush()

            (
                db.query(ChatMessage)
                .filter(ChatMessage.user_id == user_id, ChatMessage.session_id.is_(None))
                .update({ChatMessage.session_id: legacy_session.id}, synchronize_session=False)
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


ensure_schema_compatibility()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Mental Health Tracking API with AI Integration",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Welcome to MindTrackAi API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
