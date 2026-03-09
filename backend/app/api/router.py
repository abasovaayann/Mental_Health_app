from fastapi import APIRouter
from app.api.routes import auth, survey

api_router = APIRouter()

# Include authentication routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Include survey routes
api_router.include_router(
    survey.router,
    prefix="/survey",
    tags=["survey"]
)
