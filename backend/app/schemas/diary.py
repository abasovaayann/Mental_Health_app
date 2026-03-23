from datetime import date, datetime
from typing import List
from pydantic import BaseModel, Field


class DiaryEntryCreate(BaseModel):
    entry_date: date
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    mood: str
    tags: List[str] = []


class DiaryEntryUpdate(BaseModel):
    entry_date: date
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    mood: str
    tags: List[str] = []


class DiaryEntryResponse(BaseModel):
    id: int
    user_id: int
    entry_date: date
    title: str
    content: str
    mood: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class DiaryStatsResponse(BaseModel):
    total_entries: int
    last_entry_at: datetime | None


class SpeechToTextResponse(BaseModel):
    transcript: str
