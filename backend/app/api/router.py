from fastapi import APIRouter
from app.api.routes import auth, survey, diary, chatbot, reminders

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(survey.router, prefix="/survey", tags=["survey"])
api_router.include_router(diary.router, prefix="/diary", tags=["diary"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["reminders"])
