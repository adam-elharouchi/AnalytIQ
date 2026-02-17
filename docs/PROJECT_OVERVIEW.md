# AnalytIQ Project Overview

## 📖 Introduction
AnalytIQ is an AI-powered educational platform designed to enhance the learning experience for students and professors in the field of coding and analytics. The platform provides interactive tools, real-time feedback, and comprehensive metrics to track progress.

## 🏗️ Architecture & Tech Stack

### Backend
The backend is built with **Python** using the **Flask** framework, providing a robust and scalable API.
- **Framework**: Flask (3.0.0)
- **Database**: PostgreSQL (via Supabase) with connection pooling (Psycopg2)
- **AI Engine**: Google Gemini API (gemini-1.5-flash/pro) via `google-generativeai`
- **Async Tasks**: Celery with Redis for background processing
- **Authentication**: JWT (JSON Web Tokens) with `PyJWT`
- **Security**: Flask-Limiter (Rate Limiting), Flask-WTF (CSRF), Bcrypt (Password Hashing)
- **Monitoring**: Sentry for error tracking

### Frontend
The frontend is built using standard web technologies, ensuring compatibility and performance.
- **Languages**: HTML5, CSS3, JavaScript (Vanilla ES6+)
- **Styling**: Custom CSS with responsive design
- **State Management**: `localStorage` for user sessions and caching
- **API Interaction**: Custom `api-helper.js` with authenticated fetch wrapper and caching

### Infrastructure
- **Deployment**: Render (Web Service + Redis)
- **Storage**: Supabase Storage for file uploads (PDFs, etc.)
- **Version Control**: Git & GitHub

## 📂 Key File Structure

### Root Directory
- `app.py`: The main entry point for the Flask application. Contains API routes, database connection logic, and authentication handlers.
- `config.py`: Centralized configuration file handling environment variables, database settings, and feature flags.
- `requirements.txt`: List of Python dependencies.
- `Procfile`: Command to run the application on Render/Heroku (`gunicorn app:app`).
- `start_server.sh`: Shell script to start the local development server.

### Source Directories
- **`js/`**: Contains frontend JavaScript logic.
  - `api-helper.js`: Core utility for API requests, caching, and authentication.
  - `auth.js`: Handles login, signup, and session management.
  - `code-assistant.js`: Logic for the AI code assistant and chat interface.
  - `student-*.js`: Logic specific to student views.
  - `professor-*.js`: Logic specific to professor views.
- **`css/`**: Global and page-specific stylesheets.
- **`python/`**: Helper Python modules (e.g., PDF processing, exercise generation).
- **`docs/`**: Project documentation files.

### HTML Templates (Root)
- `index.html`: Landing page and marketing site.
- `login.html`: Login page; `reset-password.html`: Password reset flow.
- `student-classes.html`: Student class list; `student-class.html`: Individual class view with chapters and exercises.
- `professor-dashboard.html`: Professor overview and class management; `professor-class.html`: Per-class management, analytics, and leaderboard.
- `practice-playground.html`: Interactive coding exercise environment with AI hint assistant.
- `code-assistant.html`: Free-form AI coding assistant with conversation history.
- `upload-assistant.html`: PDF chapter upload flow for professors.
- `chapter-view.html`: In-browser PDF viewer for students.
- `modules.html`: Course module browser.
- `profile.html`: User profile and preferences.
- `resources.html`: Supplementary resources page.
- `contact.html`: Contact form.

## 🌐 Website Features

### Student Portal
- **Dashboard**: View enrolled classes, recent activity, and progress.
- **Class View**: Access course materials, assignments, and grades.
- **Practice Playground**: Interactive coding environment with real-time AI assistance.

### Professor Portal
- **Dashboard**: Manage classes, view student analytics, and track performance.
- **Class Management**: Upload resources (PDFs), create assignments, and monitor student engagement.
- **AI Tools**: Generate exercises and quizzes from course content automatically.

### General
- **AI Assistant**: Context-aware chat for coding help and concept explanation.
- **Profile Management**: Update user details and preferences.
- **Responsive Design**: Optimized for desktop and tablet usage.
