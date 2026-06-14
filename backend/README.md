# MindTrackAi Backend

FastAPI backend with PostgreSQL database for the MindTrackAi mental health tracking application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database:
- Install PostgreSQL
- Create database: `mindtrackai_db`
- Update `.env` file with your database credentials

4. Apply database migrations:
```bash
alembic upgrade head
```
- This creates/updates all tables. Run it on every fresh database and after pulling changes that add migrations.
- The app no longer creates tables at startup — migrations are the single source of truth for the schema.

5. Configure local Whisper speech-to-text:
- Optional: set `WHISPER_MODEL` in `.env` to `tiny`, `base`, `small`, `medium`, or `large`.
- The default model is `base`.

6. Run the server:
```bash
python run.py
```

API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

## Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info
