StudyMate AI – Smart Study Generator Agent
==========================================

Stage 1: Flask + PostgreSQL + Auth + Dashboard
-----------------------------------------------

## Prerequisites
- Python 3.10+
- PostgreSQL 14+

## Setup Instructions

### 1. Create and activate a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the project root (copy from `.env.example`):
```
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/studymate_db
FLASK_ENV=development
```

### 4. Create PostgreSQL database
```sql
-- In psql:
CREATE DATABASE studymate_db;
```

### 5. Initialize database tables
```bash
python init_db.py
```

### 6. Run the application
```bash
python run.py
```

Open http://localhost:5000 in your browser.

## Project Structure
```
Studyplanner/
├── app/
│   ├── __init__.py          # Flask app factory + extensions
│   ├── models.py            # SQLAlchemy models (User, Document, StudyPlan, etc.)
│   ├── auth/
│   │   ├── __init__.py      # Auth blueprint
│   │   ├── forms.py         # WTForms (RegistrationForm, LoginForm)
│   │   └── routes.py        # /auth/register, /auth/login, /auth/logout
│   ├── main/
│   │   ├── __init__.py      # Main blueprint
│   │   └── routes.py        # Dashboard, Documents, Study Plans, Progress, Profile
│   ├── static/
│   │   ├── css/style.css    # Custom stylesheet (Blue & Purple theme)
│   │   └── js/main.js       # Client-side utilities
│   └── templates/
│       ├── base.html         # Master layout with navbar + flash messages
│       ├── auth/
│       │   ├── login.html
│       │   └── register.html
│       └── main/
│           ├── index.html    # Landing page
│           ├── dashboard.html
│           ├── documents.html
│           ├── study_plans.html
│           ├── progress.html
│           └── profile.html
├── config.py                # Configuration classes
├── init_db.py               # Database initializer
├── run.py                   # Application entry point
├── requirements.txt
└── .env.example
```

## Features (Stage 1)
- [x] User registration with validation
- [x] Secure login/logout with Flask-Login + Bcrypt
- [x] CSRF protection on all forms
- [x] PostgreSQL database with 8 models
- [x] Student dashboard with stats & charts
- [x] Document upload (PDF/TXT) with file validation
- [x] Study plan creation & management
- [x] Learning progress tracking
- [x] User profile page
- [x] Responsive design (Bootstrap 5, Blue & Purple theme)
- [x] Landing page

## Stage 2 (AI Features — coming next)
- IBM watsonx AI integration
- AI-powered document summarization
- Quiz generation from uploaded materials
- Flashcard creation
- RAG-based chat with notes (IBM Langflow)
- Personalized study plan generation
