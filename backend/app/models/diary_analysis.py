from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class DiaryEntryAnalysis(Base):
    """
    Local-NLP analysis cache for a single DiaryEntry.

    Populated synchronously from the diary create/update endpoints so the
    chatbot can include sentiment/emotion/mood as memory context without
    re-running inference on every chat turn.
    """

    __tablename__ = "diary_entry_analyses"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(
        Integer,
        ForeignKey("diary_entries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)

    sentiment = Column(String, nullable=True)
    sentiment_score = Column(Float, nullable=True)

    emotion = Column(String, nullable=True)
    emotion_score = Column(Float, nullable=True)

    mood = Column(String, nullable=True)  # "low" | "medium" | "high"

    analyzed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
