from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(String, nullable=False)   # "user" | "assistant"
    content = Column(Text, nullable=False)
    mode = Column(String, nullable=False, default="general")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
