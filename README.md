# MindTrackAi 💚

A full-stack mental health tracking application with mood monitoring, email reminders, and AI-powered insights.

## 📋 Project Overview

MindTrackAi helps users track their mental health through daily mood check-ins, journal entries, and automated reminders. The app features:

- **User Authentication** - Secure login with JWT tokens
- **Daily Mood Tracking** - Log mood and emotional states
- **Email Reminders** - Configurable daily reminders for check-ins
- **Journal Entries** - Write and store mental health reflections
- **AI Insights** - Machine learning analysis of mood patterns
- **Responsive UI** - Works on desktop and mobile devices

## 🏗️ Project Structure

```
Mental_Health_app/
├── frontend/               # React application
│   ├── src/
│   │   ├── components/    # Reusable React components
│   │   ├── pages/         # Page components
│   │   └── App.js         # Main app component
│   ├── public/            # Static assets
│   └── package.json       # Frontend dependencies
│
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # Database models
│   │   ├── config.py     # Configuration
│   │   └── main.py       # FastAPI app setup
│   ├── services/         # Business logic
│   ├── ml/               # Machine learning models
│   ├── nlp/              # Natural language processing
│   ├── requirements.txt  # Backend dependencies
│   ├── run.py           # Start the backend server
│   └── .env             # Environment variables
│
├── test_reminders.py     # Email reminder system tests
├── verify_setup.py       # Feature verification checklist
└── README.md            # This file
```

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v14+) and npm
- **Python** (v3.8+)
- **PostgreSQL** (optional - for production)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
# Copy the example file and update with your settings
copy .env.example .env
# Edit .env with your database and email credentials
```

5. Start the backend server:
```bash
python run.py
```

The API will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs` (Swagger UI)

### Frontend Setup

1. In a new terminal, navigate to the project root:
```bash
cd Mental_Health_app
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The app will open at: `http://localhost:3000`

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/mindtrackai_db

# JWT
SECRET_KEY=your-secret-key-here

# Email Reminders
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Whisper (Speech-to-Text)
WHISPER_MODEL=base  # tiny, base, small, medium, large

# Environment
ENVIRONMENT=development
```

## 📧 Email Reminders Setup

The app includes an automated email reminder system for daily mood check-ins.

### To Enable Email Reminders:

1. **Get Gmail App Password:**
   - Go to https://myaccount.google.com/apppasswords
   - Enable 2FA first if needed
   - Generate a 16-character app password
   - Copy it to `backend/.env` as `EMAIL_PASSWORD`

2. **Update Configuration:**
   - Set `EMAIL_FROM` in `.env`
   - Set `EMAIL_PASSWORD` with the app password from step 1

3. **Restart Backend:**
```bash
python backend/run.py
```

4. **Test the Setup:**
```bash
# Run verification checklist
python verify_setup.py

# Run reminder system tests
python test_reminders.py
```

5. **Configure in App:**
   - Open app at `http://localhost:3000`
   - Go to Settings → Email Reminders
   - Toggle ON, select preferred time, and Save

## 📚 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### Reminders
- `GET /api/reminders/preferences` - Get user reminder settings
- `PUT /api/reminders/preferences` - Update reminder settings
- `DELETE /api/reminders/preferences` - Disable reminders

### Mood Check-ins
- `GET /api/checkins` - Get user check-ins
- `POST /api/checkins` - Create new check-in
- `GET /api/checkins/{id}` - Get check-in details

### Journal
- `GET /api/journal` - Get journal entries
- `POST /api/journal` - Create entry
- `GET /api/journal/{id}` - Get entry details

## 🧪 Testing

### Test Email Reminders
```bash
python test_reminders.py
```
This validates the complete reminder system without needing real Gmail credentials.

### Verify Setup
```bash
python verify_setup.py
```
This checks that all required files are in place and shows the quick start guide.

### Frontend Tests
```bash
npm test
```

## 🛠️ Tech Stack

**Frontend:**
- React 18
- React Router v6
- Axios (HTTP client)
- Tailwind CSS (styling)

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- PyJWT (authentication)
- python-jose (JWT tokens)
- pytz (timezone support)

**ML/NLP:**
- Whisper (speech-to-text)
- NLTK (natural language processing)
- scikit-learn (machine learning)

## 📖 Documentation

Additional documentation is available in:
- `backend/README.md` - Backend-specific setup and endpoints
- `EMAIL_REMINDERS_SETUP.md` - Detailed email reminders configuration
- `REMINDER_SYSTEM_SUMMARY.md` - Feature overview and architecture

## 🔒 Security

- User passwords are hashed with bcrypt
- API uses JWT authentication tokens
- Environment variables store sensitive data (never commit `.env`)
- HTTPS recommended for production

## 🤝 Contributing

To contribute to this project:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📝 License

This project is private. All rights reserved.

## 💡 Troubleshooting

**Backend won't start:**
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Run `pip install -r requirements.txt` again

**Frontend won't connect to backend:**
- Verify backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Ensure `.env` has correct API base URL

**Email reminders not working:**
- Run `python verify_setup.py` to check setup
- Verify Gmail app password is correct
- Check backend logs for SMTP errors
- Allow less secure apps: https://myaccount.google.com/lesssecureapps


**Built with ❤️ for mental health awareness**
