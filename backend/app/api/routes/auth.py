from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.utils.auth import verify_password, get_password_hash, create_access_token
from app.utils.dependencies import get_current_user
from app.config import settings

router = APIRouter()


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
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
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    return {
        "message": "User created successfully",
        "token": access_token,
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
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token."""
    
    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "message": "Login successful",
        "token": access_token,
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


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user
