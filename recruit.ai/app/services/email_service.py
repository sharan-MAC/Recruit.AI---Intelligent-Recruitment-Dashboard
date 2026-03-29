import os
import datetime
import smtplib
import asyncio
try:
    from imap_tools import MailBox, AND
    IMAP_AVAILABLE = True
except ImportError:
    IMAP_AVAILABLE = False
    print("imap-tools package not found.")

from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from app.services.resume_processor import process_resume_logic

RESUMES_RAW_DIR = Path("resumes_raw")
RESUMES_RAW_DIR.mkdir(exist_ok=True)

HR_SENDER_EMAIL = os.getenv("HR_EMAIL", "sharanrh297@gmail.com")


def _is_gmail_app_password(passwd: str) -> bool:
    if not passwd:
        return False
    clean = passwd.replace(" ", "")
    # Gmail app password is 16 characters (letters/numbers) and no @
    return len(clean) == 16 and "@" not in clean


def _validate_email_password():
    email_host = os.getenv("EMAIL_HOST", "imap.gmail.com")
    email_pass = os.getenv("EMAIL_PASS", "")
    if email_host.startswith("imap.gmail") or email_host.endswith("gmail.com"):
        if not _is_gmail_app_password(email_pass):
            raise ValueError("EMAIL_PASS must be a Gmail app-specific password (16-char app password).")


async def send_notification_email(subject: str, body: str):
    """Sends an email notification using SMTP."""
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    
    if not email_user or not email_pass:
        print("SMTP credentials not set, skipping notification email.")
        return
    try:
        _validate_email_password()
    except Exception as e:
        print(f"Invalid email password: {e}")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = HR_SENDER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        print(f"Notification email sent: {subject}")
    except Exception as e:
        print(f"Failed to send notification email: {e}")

executor = ThreadPoolExecutor(max_workers=3)

def _record_ingestion_event(processed_files: int, success: bool, message: str = ""):
    from app.database import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ingestion_events (hr_email, processed_files, success, message, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        HR_SENDER_EMAIL,
        processed_files,
        1 if success else 0,
        message,
        datetime.datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def _sync_ingest():
    if not IMAP_AVAILABLE:
        _record_ingestion_event(0, False, "IMAP service unavailable")
        return {"success": False, "message": "IMAP service unavailable"}
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    email_host = os.getenv("EMAIL_HOST", "imap.gmail.com")
    
    if not email_user or not email_pass:
        _record_ingestion_event(0, False, "Email credentials not set")
        return {"success": False, "message": "Email credentials not set"}
    try:
        _validate_email_password()
    except Exception as e:
        _record_ingestion_event(0, False, f"Invalid email password: {e}")
        return {"success": False, "message": str(e)}

    processed_count = 0
    try:
        with MailBox(email_host).login(email_user, email_pass) as mailbox:
            # Only fetch unread emails from the specific HR sender
            for msg in mailbox.fetch(AND(seen=False, from_=HR_SENDER_EMAIL)):
                for att in msg.attachments:
                    ext = Path(att.filename).suffix.lower()
                    if ext in [".pdf", ".docx"]:
                        filename = f"email_{Path(att.filename).stem}_{int(datetime.datetime.now().timestamp())}{ext}"
                        filepath = RESUMES_RAW_DIR / filename
                        with open(filepath, "wb") as f:
                            f.write(att.payload)
                        
                        processed_count += 1
                        from app.services.resume_processor import process_resume_logic_sync
                        process_resume_logic_sync(filepath, att.payload, ext)
                mailbox.flag(msg.uid, "\\Seen", True)
        if processed_count > 0:
            _record_ingestion_event(processed_count, True, "Ingestion complete")
            return {"success": True, "processedCount": processed_count}
        else:
            return {"success": True, "processedCount": 0, "message": "No new HR resumes found"}
    except Exception as e:
        print(f"Ingestion Error: {e}")
        _record_ingestion_event(0, False, str(e))
        return {"success": False, "error": str(e)}

async def perform_ingestion():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_ingest)
