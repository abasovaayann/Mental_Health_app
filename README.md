# MindTrackAi 💚

A full-stack, multilingual mental-health tracking app: daily mood check-ins, voice/text diary entries with AI sentiment & emotion analysis, a diary-aware AI companion, a machine-learning wellness score, and verified, timezone-aware email reminders.

> Languages supported across the experience: **English, Turkish, Russian.**

## 📋 Features

- **Secure accounts** — JWT access/refresh auth, bcrypt hashing, rate limiting, and **mandatory email verification** (a 6-digit code; unverified accounts can't access app data).
- **Password reset** — emailed 6-digit reset code → set a new password.
- **Daily check-ins** — mood / sleep / energy, one per day.
- **Diary** — typed or **spoken** entries (local Whisper speech-to-text), automatically analyzed for sentiment, emotion, and overall mood.
- **AI insights** — a scikit-learn wellness/risk score from your baseline survey, plus trends over time.
- **AI companion** — a diary-aware chatbot powered by Anthropic Claude, with offline fallbacks.
- **Email reminders** — pick a time, timezone, and frequency; reminders are sent only to verified addresses and fire reliably at your chosen time.

## 🏗️ Project Structure

```
Mental_Health_app/
├── src/                       # React frontend (Create React App)
│   ├── api/                   # axios instance + auth service
│   ├── components/            # Reusable components (Login, Register, ReminderSettings, …)
│   ├── pages/                 # AuthPage, VerifyEmail, ForgotPassword, Dashboard, Diary, Settings, …
│   └── App.js                 # Routes
├── public/                    # Static assets
├── package.json               # Frontend dependencies
│
├── backend/
│   ├── app/
│   │   ├── api/routes/        # auth, survey, diary, chatbot, reminders
│   │   ├── api/router.py      # Router wiring (data routers require a verified email)
│   │   ├── services/          # analysis, chat_*, reminder, email, verification
│   │   ├── nlp/               # sentiment, emotion, language detection
│   │   ├── models/            # SQLAlchemy ORM tables
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── utils/             # auth (JWT/bcrypt), dependencies
│   │   ├── config.py          # pydantic-settings config
│   │   └── main.py            # App factory + lifespan (reminder loop, email check)
│   ├── ml/                    # Offline training pipeline, artifacts, charts
│   ├── migrations/            # Alembic schema history
│   ├── tests/                 # pytest suite
│   ├── requirements.txt
│   ├── run.py                 # Dev entrypoint (uvicorn)
│   └── .env.example
│
├── scripts/                   # Helper scripts (e.g. test_reminders.py)
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- **Node.js** 16+ and npm
- **Python** 3.10+
- **PostgreSQL** 13+
- **ffmpeg** — bundled via `imageio-ffmpeg`, no manual install needed

### Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows PowerShell
# source venv/bin/activate        # macOS/Linux

pip install -r requirements.txt

copy .env.example .env            # then edit .env (see Configuration)

alembic upgrade head              # create/upgrade the database schema
python run.py                     # start the API on http://localhost:8000
```

API docs (Swagger UI): `http://localhost:8000/docs`

> **First run on an existing DB?** If tables already exist but Alembic was never initialized,
> stamp the current revision before upgrading: `alembic stamp head`.

### Frontend

```bash
# from the project root, in a second terminal
npm install
npm start                         # opens http://localhost:3000
```

Both servers must run together — the frontend (`:3000`) talks to the backend (`:8000`).

## ⚙️ Configuration

Create `backend/.env` (copied from `.env.example`):

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/mindtrackai_db

# Auth
SECRET_KEY=change-me-to-a-long-random-string

# Email (Gmail SMTP) — used for verification, password reset, and reminders
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-16-char-gmail-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Speech-to-text
WHISPER_MODEL=base                # tiny | base | small | medium | large

# Chatbot (optional; offline fallbacks used if unset)
ANTHROPIC_API_KEY=sk-ant-...

ENVIRONMENT=development
```

> `.env` is gitignored — **never commit real credentials.**

## 📧 Email Setup (verification, reset & reminders)

Email powers three things: account verification, password reset, and check-in reminders. All three need valid Gmail SMTP credentials.

1. **Enable 2-Step Verification** on the Gmail account.
2. **Create an App Password:** https://myaccount.google.com/apppasswords → copy the **16-character** code.
3. Put it in `backend/.env` as `EMAIL_PASSWORD` (spaces are stripped automatically) and set `EMAIL_FROM`.
4. **Restart the backend.** On startup it logs whether SMTP credentials authenticate — look for `[email] SMTP credentials authenticated…`.
5. In the app: **Settings → Email Reminders** → toggle on, pick a time/timezone, save.

Quick credential/reminder check:
```bash
python scripts/test_reminders.py
```

## 📚 API Endpoints (selected)

### Authentication (`/api/auth`) — open
- `POST /register` — create account (rejects undeliverable email domains; emails a verification code)
- `POST /login` — obtain access + refresh tokens
- `POST /refresh` — rotate tokens
- `POST /verify-email` — confirm the 6-digit code
- `POST /resend-verification` — re-send a verification code
- `POST /forgot-password` — email a reset code
- `POST /reset-password` — set a new password using the code
- `GET /me`, `PUT /profile`, `PUT /change-password`, `GET /export-data`, `DELETE /account`

### Data endpoints — **require a verified email**
- `survey` (`/api/survey`) — baseline survey + wellness score
- `diary` (`/api/diary`) — entries CRUD + `POST /diary/speech-to-text`
- `chatbot` (`/api/chatbot`) — chat sessions & messages
- `reminders` (`/api/reminders/preferences`) — GET / PUT / DELETE reminder settings

## 🗄️ Database & Migrations

Schema is owned by **Alembic** (the app does not create tables at import time).

```bash
alembic upgrade head            # apply latest
alembic revision -m "message"   # create a new migration
alembic downgrade -1            # roll back one
```

## 🔒 Security

- bcrypt password hashing; JWT access + refresh with full claim validation (exp/iat/nbf/iss/aud/jti).
- Refresh-token rotation + replay protection.
- In-memory rate limiting on auth, verification, and reset endpoints.
- **Mandatory email verification** — data routers reject unverified users (403).
- **Deliverability check** — registration rejects domains that can't receive mail (MX lookup).
- CORS restricted to configured origins; secrets only via environment; response models never leak password hashes.

## 🧪 Testing

```bash
# Backend
cd backend && pytest

# Frontend
npm test
```

## 🛠️ Tech Stack

**Frontend:** React 18 · React Router v6 · Axios · Tailwind CSS 3 · Jest/RTL · MediaRecorder & SpeechRecognition Web APIs

**Backend:** FastAPI · Uvicorn · SQLAlchemy 2.0 · PostgreSQL · Alembic · Pydantic v2 · python-jose (JWT) · passlib/bcrypt · pytz · email-validator + dnspython

**AI/ML/NLP:** Hugging Face Transformers (multilingual sentiment + emotion) · scikit-learn (Random Forest wellness model) · OpenAI Whisper (local STT) · Anthropic Claude (`claude-sonnet-4-6`)

## 💡 Troubleshooting

**Backend won't start**
- Is PostgreSQL running and `DATABASE_URL` correct?
- Did you run `alembic upgrade head`?
- Re-run `pip install -r requirements.txt`.

**Frontend can't reach backend**
- Backend running on `http://localhost:8000`?
- Check the browser console for CORS errors.

**Email (verification / reset / reminders) not sending**
- Use a valid **16-character Gmail App Password** with 2-Step Verification enabled.
- Watch the backend startup log: `[email] …` tells you if SMTP auth failed.
- Reminders only send to **verified** addresses, and only while the backend is running.

## 📝 License

Private project. All rights reserved.

---
**Built with ❤️ for mental health awareness**
