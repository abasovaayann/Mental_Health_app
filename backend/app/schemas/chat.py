"""Pydantic request/response models for the chatbot routes."""

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: int
    message: str
    mode: str = "general"
    date: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    used_analysis_memory: bool = False


class ChatSessionCreateRequest(BaseModel):
    title: Optional[str] = None


class ChatSessionListItem(BaseModel):
    id: int
    title: str
    last_activity: Optional[str] = None
    created_at: str
    updated_at: str


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionListItem]


class ChatSessionDetailResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    messages: list[dict]
