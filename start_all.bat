@echo off
REM Start both servers
cd /d "c:\Users\User\OneDrive\Рабочий стол\Mental_Health_app"

REM Clean cache
if exist ".claude" rmdir /s /q ".claude"
if exist ".codex-run-logs" rmdir /s /q ".codex-run-logs"
echo Cache cleaned.

echo.
echo Starting Backend (FastAPI) on port 8000...
echo.
start "Backend - MindTrackAi" cmd /k "cd backend && python run.py"

timeout /t 3 /nobreak

echo.
echo Starting Frontend (React) on port 3000...
echo.
start "Frontend - MindTrackAi" cmd /k "npm start"

echo.
echo Both servers started!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
