import os
import asyncio
import datetime
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.database import init_db
from app.api.endpoints import router as api_router
from app.services.email_service import perform_ingestion, HR_SENDER_EMAIL

load_dotenv()

app = FastAPI(title="Recruit.AI API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# Initialize Database
# init_db() # Moved to startup_event

# Background Ingestion Task
async def auto_ingest_worker():
    """Background worker that polls the AI mailbox every 60 seconds."""
    print(f"Starting background ingestion worker... Monitoring {HR_SENDER_EMAIL}")
    while True:
        try:
            await perform_ingestion()
        except Exception as e:
            print(f"Background Ingestion Error: {e}")
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    print("Initializing Database...")
    try:
        init_db()
    except Exception as e:
        print(f"Database Initialization Failed: {e}")
        
    # Start the background worker
    print("Starting background worker...")
    asyncio.create_task(auto_ingest_worker())

# Include API Routes
app.include_router(api_router, prefix="/api")

# Templates and Static Files
templates = Jinja2Templates(directory="templates")

if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

@app.get("/")
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    # If the path starts with api, it should have been caught by the api routes
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="API route not found")
    
    # Check if file exists in dist
    file_path = Path("dist") / full_path
    if file_path.is_file():
        from fastapi.responses import FileResponse
        return FileResponse(file_path)
        
    # Fallback to Jinja2 index for SPA behavior
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    print("Starting Recruit.AI Python Backend on port 3000...")
    try:
        uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
    except Exception as e:
        print(f"Server failed to start: {e}")
