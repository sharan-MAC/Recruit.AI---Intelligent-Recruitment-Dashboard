# Recruit.AI - Intelligent Recruitment Dashboard

A professional, AI-powered recruitment tool for automated resume ingestion, extraction, and candidate ranking.

## Features

- **Automated Ingestion**: Monitors your email for unread resumes (PDF/DOCX).
- **AI Extraction**: Uses Gemini AI to extract skills, experience, and education from resumes.
- **Smart Ranking**: Automatically ranks candidates against job descriptions using AI.
- **Modern UI**: A clean, technical dashboard built with React, Tailwind CSS, and Framer Motion.

## Tech Stack

- **Backend & Frontend**: Python 3.x, FastAPI, Jinja2 Templates.
- **Styling**: Tailwind CSS (CDN).
- **Interactivity**: Alpine.js (CDN).
- **Icons**: Lucide Icons (CDN).
- **Database**: SQLite.
- **AI**: Google Gemini AI (Python SDK).
- **Email**: imap-tools.
- **File Processing**: pypdf, mammoth.

## Getting Started (Local Development)

1. **Clone the repository**.
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables**:
   Create a `.env` file based on `.env.example`.
   ```env
   GEMINI_API_KEY=your_api_key
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_gmail_app_password  # must be Gmail app-specific password (16 chars)
   ```
4. **Run the application**:
   ```bash
   python3 main.py
   ```
5. **Open the app**:
   Navigate to `http://localhost:3000`.

## Deploying to Render

1. Create a new Web Service on Render from this GitHub repo.
2. Use the service type **Python**.
3. Set the build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Set the start command:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Add the required environment variables:
   - `GEMINI_API_KEY`
   - `EMAIL_USER`
   - `EMAIL_PASS` (Gmail app-specific password)
   - `EMAIL_HOST=imap.gmail.com`
   - `EMAIL_PORT=993`
   - `SMTP_HOST=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `HR_EMAIL`
   - `DATABASE_URL=sqlite:///./recruitment.db`
6. Deploy and visit the Render URL.

## Project Structure

- `main.py`: Main FastAPI server entry point (Python).
- `templates/index.html`: The entire frontend UI (HTML/JS).
- `requirements.txt`: Python dependencies.
- `recruitment.db`: SQLite database file.
