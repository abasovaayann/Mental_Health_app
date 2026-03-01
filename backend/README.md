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

4. Run the server:
```bash
python run.py
```

API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

## Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info
