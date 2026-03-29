import json
import os
import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.database import get_db_conn
from app.models import JobCreate
from app.services.email_service import perform_ingestion, RESUMES_RAW_DIR, send_notification_email
from app.services.resume_processor import process_resume_logic
from app.services.ai_service import get_embedding
from app.services.pinecone_service import query_candidates

router = APIRouter()

@router.get("/search/semantic")
async def semantic_search(query: str):
    embedding = await get_embedding(query)
    if not embedding:
        return []
    
    matches = query_candidates(embedding)
    
    # Enrich with DB data
    conn = get_db_conn()
    cursor = conn.cursor()
    
    results = []
    for m in matches:
        cursor.execute("SELECT * FROM candidates WHERE id = ?", (m.id,))
        candidate = cursor.fetchone()
        if candidate:
            d = dict(candidate)
            d["skills"] = json.loads(d["skills"] or "[]")
            d["match_score"] = m.score
            results.append(d)
    
    conn.close()
    return results

@router.get("/stats")
async def get_stats():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM candidates) as totalCandidates,
            (SELECT COUNT(*) FROM jobs) as activeJobs,
            (SELECT COUNT(*) FROM finalized_candidates) as shortlisted,
            (SELECT COUNT(*) FROM ingestion_events WHERE processed_files > 0) as totalIngestionAttempts,
            (SELECT SUM(processed_files) FROM ingestion_events WHERE processed_files > 0) as totalProcessedResumes
    """)
    row = cursor.fetchone()
    conn.close()
    result = dict(row)
    # SQLite returns None for SUM on no rows, convert to 0
    result["totalProcessedResumes"] = result.get("totalProcessedResumes") or 0
    return result

@router.get("/ingestion/events")
async def get_ingestion_events(limit: int = 5):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingestion_events ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    events = []
    for row in rows:
        d = dict(row)
        events.append(d)
    return events

@router.get("/settings")
async def get_settings():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_attempts, SUM(processed_files) as total_processed FROM ingestion_events WHERE processed_files > 0")
    row = cursor.fetchone()
    conn.close()
    ingestion_summary = dict(row)
    return {
        "email_host": os.getenv("EMAIL_HOST", "imap.gmail.com"),
        "email_user": os.getenv("EMAIL_USER", ""),
        "hr_email": os.getenv("HR_EMAIL", ""),
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", 587)),
        "email_port": int(os.getenv("EMAIL_PORT", 993)),
        "resume_folder": str(RESUMES_RAW_DIR),
        "totalIngestionAttempts": ingestion_summary.get("total_attempts") or 0,
        "totalProcessedResumes": ingestion_summary.get("total_processed") or 0
    }

@router.get("/candidates")
async def get_candidates():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC")
    candidates = cursor.fetchall()
    conn.close()
    result = []
    for c in candidates:
        d = dict(c)
        d["skills"] = json.loads(d["skills"] or "[]")
        d["parsed_json"] = json.loads(d["parsed_json"] or "{}")
        result.append(d)
    return result

@router.get("/jobs")
async def get_jobs():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    jobs = cursor.fetchall()
    conn.close()
    result = []
    for j in jobs:
        d = dict(j)
        d["required_skills"] = json.loads(d["required_skills"] or "[]")
        result.append(d)
    return result

@router.post("/jobs")
async def create_job(job: JobCreate, background_tasks: BackgroundTasks):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (title, description, required_skills, created_at)
        VALUES (?, ?, ?, ?)
    """, (job.title, job.description, json.dumps(job.required_skills), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Send notification
    background_tasks.add_task(
        send_notification_email, 
        f"New Job Posted: {job.title}", 
        f"A new job opening has been created.\n\nTitle: {job.title}\nDescription: {job.description}\nSkills: {', '.join(job.required_skills)}"
    )
    
    return {"success": True}

@router.post("/ingest/email")
async def ingest_emails():
    return await perform_ingestion()

@router.post("/upload")
async def upload_resume(background_tasks: BackgroundTasks, resume: UploadFile = File(...)):
    ext = Path(resume.filename).suffix.lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    filename = f"manual_{Path(resume.filename).stem}_{int(datetime.datetime.now().timestamp())}{ext}"
    filepath = RESUMES_RAW_DIR / filename
    
    content = await resume.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    background_tasks.add_task(process_resume_logic, filepath, content, ext)
    return {"success": True}

@router.get("/rankings/{job_id}")
async def get_rankings(job_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, c.name, c.skills
        FROM rankings r
        JOIN candidates c ON r.candidate_id = c.id
        WHERE r.job_id = ?
        ORDER BY r.match_score DESC
    """, (job_id,))
    rankings = cursor.fetchall()
    conn.close()
    result = []
    for r in rankings:
        d = dict(r)
        d["skills"] = json.loads(d["skills"] or "[]")
        result.append(d)
    return result
