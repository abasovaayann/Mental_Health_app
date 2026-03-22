from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Text
from sqlalchemy.sql import func
from app.database import Base


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    mood = Column(String, nullable=False)
    tags_csv = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
