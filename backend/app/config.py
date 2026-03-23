from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    JWT_ISSUER: str = "mindtrackai-api"
    JWT_AUDIENCE: str = "mindtrackai-client"

    # Security defaults
    PASSWORD_MIN_LENGTH: int = 8
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 300
    AUTH_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_BLOCK_SECONDS: int = 600
    
    # API
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "MindTrackAi"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
