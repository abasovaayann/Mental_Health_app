from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.api.router import api_router
from app.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)


def ensure_schema_compatibility() -> None:
    # Keep older local databases compatible with newer models without manual migration.
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS app_users
                ADD COLUMN IF NOT EXISTS preferences_json TEXT NOT NULL DEFAULT '{}'
                """
            )
        )


ensure_schema_compatibility()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Mental Health Tracking API with AI Integration",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Welcome to MindTrackAi API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
