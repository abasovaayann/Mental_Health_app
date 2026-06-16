from fastapi import APIRouter, Depends
from app.api.routes import auth, survey, diary, chatbot, reminders
from app.utils.dependencies import require_verified_user

api_router = APIRouter()

# Data routers require a verified email; auth stays open so users can log in,
# verify, resend codes, and reset passwords.
verified = [Depends(require_verified_user)]

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(survey.router, prefix="/survey", tags=["survey"], dependencies=verified)
api_router.include_router(diary.router, prefix="/diary", tags=["diary"], dependencies=verified)
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"], dependencies=verified)
api_router.include_router(reminders.router, prefix="/reminders", tags=["reminders"], dependencies=verified)
