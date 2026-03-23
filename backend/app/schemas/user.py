import re
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
from app.config import settings


def _validate_password_strength(value: str) -> str:
    if len(value) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must include at least one uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must include at least one lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must include at least one number")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must include at least one special character")
    return value


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str


class UserCreate(UserBase):
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None
    degree: Optional[str] = None
    university: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        return _validate_password_strength(value)


class UserResponse(UserBase):
    id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    degree: Optional[str] = None
    university: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_active: bool
    is_verified: bool
    baseline_completed: bool
    baseline_completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    degree: Optional[str] = None
    university: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str):
        return _validate_password_strength(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class NotificationPreferences(BaseModel):
    dailyCheckin: bool
    weeklyReport: bool
    aiRecommendations: bool
    diaryReminder: bool
    reminderTime: str
    channelEmail: bool
    channelInApp: bool


class PrivacyPreferences(BaseModel):
    biometricLock: bool
    anonymousResearch: bool
    sessionTimeout: int


class AppearancePreferences(BaseModel):
    theme: str
    language: str
    fontSize: int
    reduceAnimations: bool


class DiaryPreferences(BaseModel):
    inputMode: str
    aiMoodAnalysis: bool
    autoSave: bool
    weeklyReportInclude: bool


class VoicePreferences(BaseModel):
    micSensitivity: int
    transcriptionLang: str
    recordingQuality: str


class UserPreferences(BaseModel):
    notifications: NotificationPreferences
    privacy: PrivacyPreferences
    appearance: AppearancePreferences
    diary: DiaryPreferences
    voice: VoicePreferences
