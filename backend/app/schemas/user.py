from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


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


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
