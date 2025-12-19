import shutil
import os
import uuid
import asyncio
from typing import Optional, Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from src.infrastructure.ai.factory import TranscriptionProviderFactory
from src.core.use_cases.analyze_case import process_case_pipeline
from src.services.groq_pipeline_service import GroqPipelineService

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# In-memory job store (replace with Redis/DB in production)
job_store: Dict[str, Dict] = {}

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    provider: str = Form("groq"),
    language: str = Form("fa")
):
    """
    Transcribe audio file using the selected AI provider.
    """
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_location = f"{UPLOAD_DIR}/{unique_filename}"
    
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        transcription_service = TranscriptionProviderFactory.get_provider(provider)
        text = await transcription_service.transcribe(file_location, language)
        
        return {
            "status": "success",
            "text": text,
            "provider": provider,
            "file_id": unique_filename
        }
    except Exception as e:
        print(f"❌ Transcription Endpoint Error: {e}")
        error_msg = str(e)
        if "400" in error_msg or "invalid_request_error" in error_msg:
             raise HTTPException(status_code=400, detail=f"Invalid media file: {error_msg}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_analysis_job(job_id: str, file_path: str, mime_type: str):
    """Background task wrapper"""
    try:
        job_store[job_id]["status"] = "processing"
        result = await process_case_pipeline(file_path, mime_type)
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["result"] = result
    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)

@router.post("/analyze")
async def analyze_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Submit an audio file for full analysis (Async).
    Returns a Job ID to check status.
    """
    file_ext = os.path.splitext(file.filename)[1]
    job_id = str(uuid.uuid4())
    unique_filename = f"{job_id}{file_ext}"
    file_location = f"{UPLOAD_DIR}/{unique_filename}"
    
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        # Initialize job
        job_store[job_id] = {
            "id": job_id,
            "status": "pending",
            "submitted_at": str(asyncio.get_event_loop().time()) # simple timestamp
        }
        
        # Start background task
        background_tasks.add_task(run_analysis_job, job_id, file_location, file.content_type or "audio/mp3")
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Analysis started in background. Check /jobs/{id} for results."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of an analysis job."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/process-stream")
async def process_audio_stream(
    file: UploadFile = File(...)
):
    """
    Uploads audio, processes it in chunks using Groq (Whisper + Llama), 
    and streams back JSON results (NDJSON).
    """
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"stream_{uuid.uuid4()}{file_ext}"
    file_location = f"{UPLOAD_DIR}/{unique_filename}"
    
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        service = GroqPipelineService()
        
        return StreamingResponse(
            service.process_stream(file_location),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        # Note: In a streaming response, once the stream starts, we can't easily change the status code.
        # But if it fails before starting, we can raise HTTP exception.
        raise HTTPException(status_code=500, detail=str(e))

