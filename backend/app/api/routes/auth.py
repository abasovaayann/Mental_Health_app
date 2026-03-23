import json
import time
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, UserUpdate, PasswordChange, UserPreferences, RefreshTokenRequest
from app.utils.auth import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_refresh_token
from app.utils.dependencies import get_current_user
from app.config import settings

router = APIRouter()

AUTH_RATE_STATE = {}
REFRESH_TOKEN_REPLAY_STATE = {}


def _rate_limit_key(scope: str, request: Request, identifier: str = "") -> str:
    client_ip = request.client.host if request.client else "unknown"
    suffix = f":{identifier}" if identifier else ""
    return f"{scope}:{client_ip}{suffix}"


def _check_rate_limit(key: str):
    now = int(time.time())
    state = AUTH_RATE_STATE.get(key)
    if not state:
        return

    blocked_until = state.get("blocked_until", 0)
    if blocked_until > now:
        retry_after = blocked_until - now
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Try again in {retry_after} seconds",
            headers={"Retry-After": str(retry_after)},
        )

    window_start = state.get("window_start", now)
    if now - window_start > settings.AUTH_RATE_LIMIT_WINDOW_SECONDS:
        AUTH_RATE_STATE.pop(key, None)


def _record_rate_failure(key: str):
    now = int(time.time())
    state = AUTH_RATE_STATE.get(key)

    if not state or now - state.get("window_start", now) > settings.AUTH_RATE_LIMIT_WINDOW_SECONDS:
        AUTH_RATE_STATE[key] = {
            "count": 1,
            "window_start": now,
            "blocked_until": 0,
        }
        return

    state["count"] = state.get("count", 0) + 1
    if state["count"] >= settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS:
        state["blocked_until"] = now + settings.AUTH_RATE_LIMIT_BLOCK_SECONDS


def _clear_rate_limit(key: str):
    AUTH_RATE_STATE.pop(key, None)


def _cleanup_refresh_replay_state(now_ts: int):
    expired = [jti for jti, exp in REFRESH_TOKEN_REPLAY_STATE.items() if exp <= now_ts]
    for jti in expired:
        REFRESH_TOKEN_REPLAY_STATE.pop(jti, None)


DEFAULT_PREFERENCES = {
    "notifications": {
        "dailyCheckin": True,
        "weeklyReport": True,
        "aiRecommendations": True,
        "diaryReminder": False,
        "reminderTime": "20:00",
        "channelEmail": False,
        "channelInApp": True,
    },
    "privacy": {
        "biometricLock": False,
        "anonymousResearch": False,
        "sessionTimeout": 30,
    },
    "appearance": {
        "theme": "system",
        "language": "en",
        "fontSize": 16,
        "reduceAnimations": False,
    },
    "diary": {
        "inputMode": "text",
        "aiMoodAnalysis": True,
        "autoSave": True,
        "weeklyReportInclude": True,
    },
    "voice": {
        "micSensitivity": 50,
        "transcriptionLang": "en",
        "recordingQuality": "standard",
    },
}


def _merged_preferences(raw_json: str | None):
    base = json.loads(json.dumps(DEFAULT_PREFERENCES))
    if not raw_json:
        return base

    try:
        stored = json.loads(raw_json)
        if isinstance(stored, dict):
            for section, values in stored.items():
                if section in base and isinstance(values, dict):
                    base[section].update(values)
    except Exception:
        return base

    return base


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new user."""
    email_key = _rate_limit_key("register", request, user_data.email.lower())
    ip_key = _rate_limit_key("register", request)
    _check_rate_limit(email_key)
    _check_rate_limit(ip_key)
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        _record_rate_failure(email_key)
        _record_rate_failure(ip_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        age=user_data.age,
        gender=user_data.gender,
        degree=user_data.degree,
        university=user_data.university,
        city=user_data.city,
        country=user_data.country
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    _clear_rate_limit(email_key)
    _clear_rate_limit(ip_key)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(subject=db_user.email)
    
    return {
        "message": "User created successfully",
        "token": access_token,
        "refreshToken": refresh_token,
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "firstName": db_user.first_name,
            "lastName": db_user.last_name,
            "isActive": db_user.is_active,
            "isVerified": db_user.is_verified,
            "baselineCompleted": db_user.baseline_completed,
            "baselineCompletedAt": db_user.baseline_completed_at
        }
    }


@router.post("/login", response_model=dict)
def login(user_credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login user and return JWT token."""
    email_key = _rate_limit_key("login", request, user_credentials.email.lower())
    ip_key = _rate_limit_key("login", request)
    _check_rate_limit(email_key)
    _check_rate_limit(ip_key)
    
    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user:
        _record_rate_failure(email_key)
        _record_rate_failure(ip_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user_credentials.password, user.hashed_password):
        _record_rate_failure(email_key)
        _record_rate_failure(ip_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        _record_rate_failure(email_key)
        _record_rate_failure(ip_key)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    _clear_rate_limit(email_key)
    _clear_rate_limit(ip_key)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(subject=user.email)
    
    return {
        "message": "Login successful",
        "token": access_token,
        "refreshToken": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "isActive": user.is_active,
            "isVerified": user.is_verified,
            "baselineCompleted": user.baseline_completed,
            "baselineCompletedAt": user.baseline_completed_at
        }
    }


@router.post("/refresh", response_model=dict)
def refresh_tokens(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)):
    refresh_key = _rate_limit_key("refresh", request)
    _check_rate_limit(refresh_key)

    refresh_payload = decode_refresh_token(payload.refresh_token)
    if refresh_payload is None:
        _record_rate_failure(refresh_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    now_ts = int(time.time())
    _cleanup_refresh_replay_state(now_ts)

    refresh_jti = refresh_payload.get("jti")
    refresh_exp = refresh_payload.get("exp")
    if not refresh_jti or not refresh_exp:
        _record_rate_failure(refresh_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token claims")

    if refresh_jti in REFRESH_TOKEN_REPLAY_STATE:
        _record_rate_failure(refresh_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token already used")

    email = refresh_payload.get("sub")
    if not email:
        _record_rate_failure(refresh_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token subject")

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        _record_rate_failure(refresh_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not eligible for refresh")

    REFRESH_TOKEN_REPLAY_STATE[refresh_jti] = int(refresh_exp)

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = create_refresh_token(subject=user.email)
    _clear_rate_limit(refresh_key)

    return {
        "message": "Token refreshed",
        "token": access_token,
        "refreshToken": new_refresh_token,
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user


@router.put("/profile", response_model=dict)
def update_profile(
    profile_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile."""
    update_fields = profile_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return {
        "message": "Profile updated successfully",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "firstName": current_user.first_name,
            "lastName": current_user.last_name,
            "age": current_user.age,
            "gender": current_user.gender,
            "degree": current_user.degree,
            "university": current_user.university,
            "city": current_user.city,
            "country": current_user.country,
        }
    }


@router.put("/change-password", response_model=dict)
def change_password(
    password_data: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change current user's password."""
    user_key = _rate_limit_key("change-password", request, str(current_user.id))
    ip_key = _rate_limit_key("change-password", request)
    _check_rate_limit(user_key)
    _check_rate_limit(ip_key)

    if not verify_password(password_data.current_password, current_user.hashed_password):
        _record_rate_failure(user_key)
        _record_rate_failure(ip_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    _clear_rate_limit(user_key)
    _clear_rate_limit(ip_key)
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.delete("/account", response_model=dict)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete current user's account and all associated data."""
    from app.models.survey import BaselineSurvey
    from app.models.diary import DiaryEntry
    db.query(BaselineSurvey).filter(BaselineSurvey.user_id == current_user.id).delete()
    db.query(DiaryEntry).filter(DiaryEntry.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully"}


@router.get("/export-data", response_model=dict)
def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all user data as JSON."""
    from app.models.survey import BaselineSurvey
    from app.models.diary import DiaryEntry
    survey = db.query(BaselineSurvey).filter(
        BaselineSurvey.user_id == current_user.id
    ).first()

    survey_data = None
    if survey:
        survey_data = {
            "sleep_duration": survey.sleep_duration,
            "energy_level": survey.energy_level,
            "academic_pressure": survey.academic_pressure,
            "study_motivation": survey.study_motivation,
            "concentration_difficulty": survey.concentration_difficulty,
            "morning_mood": survey.morning_mood,
            "emotional_low": survey.emotional_low,
            "anxiety_level": survey.anxiety_level,
            "social_support": survey.social_support,
            "financial_stress": survey.financial_stress,
            "created_at": str(survey.created_at),
        }

    return {
        "profile": {
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "age": current_user.age,
            "gender": current_user.gender,
            "degree": current_user.degree,
            "university": current_user.university,
            "city": current_user.city,
            "country": current_user.country,
            "created_at": str(current_user.created_at),
        },
        "baseline_survey": survey_data,
        "diary_entries": [
            {
                "id": entry.id,
                "entry_date": str(entry.entry_date),
                "title": entry.title,
                "content": entry.content,
                "mood": entry.mood,
                "tags": [tag for tag in (entry.tags_csv or "").split(",") if tag],
                "created_at": str(entry.created_at),
                "updated_at": str(entry.updated_at),
            }
            for entry in db.query(DiaryEntry)
            .filter(DiaryEntry.user_id == current_user.id)
            .order_by(DiaryEntry.entry_date.desc(), DiaryEntry.created_at.desc())
            .all()
        ],
    }


@router.get("/preferences", response_model=UserPreferences)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prefs = _merged_preferences(current_user.preferences_json)
    return prefs


@router.put("/preferences", response_model=UserPreferences)
def update_preferences(
    payload: UserPreferences,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prefs = payload.model_dump()
    current_user.preferences_json = json.dumps(prefs)
    db.commit()
    db.refresh(current_user)
    return prefs
