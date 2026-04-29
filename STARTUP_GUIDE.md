# MindTrackAi - Startup Guide

## Quick Start

### Option 1: Automated Start (Easiest)
Double-click: `start_all.bat`
- This will clean cache, start backend, and start frontend in separate windows

### Option 2: Manual Start

**Terminal 1 - Backend:**
```cmd
cd backend
python run.py
```
Expected output: Server running on `http://localhost:8000`

**Terminal 2 - Frontend:**
```cmd
npm start
```
Expected output: App running on `http://localhost:3000`

---

## Access Points

- **Frontend App**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Prerequisites

✅ **Already Verified:**
- Python 3.11+ with all requirements installed
- Node.js/npm with all dependencies installed
- PostgreSQL database configured in `.env`
- JWT secrets configured
- Google Gemini API key configured

## Database

The app uses PostgreSQL with connection string from `.env`:
- Host: localhost
- Port: 5432
- Database: mindtrackai_db
- User: postgres
- Password: data

Make sure PostgreSQL is running before starting the backend.

## Features

- **Authentication**: JWT-based user auth
- **Diary**: Daily mental health tracking entries
- **AI Chat**: Integration with Google Gemini
- **Speech-to-Text**: Whisper model for audio input
- **Dashboard**: User insights and analytics
- **Settings**: User preferences

## Troubleshooting

### Backend won't start
1. Check PostgreSQL is running
2. Verify `.env` file exists with DATABASE_URL set
3. Run: `pip install -r backend/requirements.txt`

### Frontend won't start
1. Check Node.js is installed: `node --version`
2. Reinstall dependencies: `npm install`
3. Clear npm cache: `npm cache clean --force`

### Port already in use
- Backend (8000): `netstat -ano | findstr :8000`
- Frontend (3000): `netstat -ano | findstr :3000`
- Kill process: `taskkill /PID <PID> /F`
