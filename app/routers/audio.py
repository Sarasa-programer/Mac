from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.services.audio_service import audio_service, AudioProcessingError
from app.services.llm_service import UnifiedLLMService
from app.models.schemas import SuccessResponse, ErrorResponse
from app.routers.pediatric import PediatricInput, CaseMetadata, SYSTEM_PROMPT
from typing import Dict, Any, Literal, Optional
from pydantic import BaseModel
import uuid
import io
import json

router = APIRouter(prefix="/api/audio", tags=["audio"])

# In-memory job store
jobs: Dict[str, Dict[str, Any]] = {}

class JobResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

async def run_analysis_job(job_id: str, audio_bytes: bytes, filename: str):
    jobs[job_id]["status"] = "processing"
    try:
        # 1. Transcribe
        file_obj = io.BytesIO(audio_bytes)
        transcribe_result = await audio_service.transcribe_audio(file_obj, filename)
        transcript = transcribe_result["text"]
        
        # 2. Analyze
        llm = UnifiedLLMService()
        input_data = PediatricInput(
            case_id=job_id,
            language="mixed",
            transcript=transcript,
            metadata=CaseMetadata(source="upload", audio_duration_sec=None)
        )
        
        # Use Groq with the robust Pediatric Prompt
        # Note: We duplicate some logic from pediatric.py here for simplicity, 
        # but reusing the prompt ensures consistency.
        user_message = input_data.model_dump_json()
        
        # Try Groq first
        if llm.groq_client:
            response_str = await llm._call_groq(SYSTEM_PROMPT, user_message, json_mode=True)
        else:
            # Fallback to summarize/differential individual calls? No, stick to prompt.
            # Use execute_pipeline generic wrapper which has fallbacks
            response_str = await llm.execute_pipeline(SYSTEM_PROMPT, user_message, "pediatric_agent", json_mode=True)
            
        result_data = json.loads(response_str)
        
        # Ensure result has transcript
        result_data["transcript"] = transcript
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result_data
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

@router.post("/analyze", response_model=JobResponse)
async def analyze_audio_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Start an asynchronous audio analysis job.
    1. Transcribe Audio
    2. Analyze using Pediatric Agent
    """
    try:
        content = await file.read()
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "pending"}
        
        background_tasks.add_task(run_analysis_job, job_id, content, file.filename)
        
        return {"job_id": job_id, "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job.get("result"),
        "error": job.get("error")
    }

@router.post("/transcribe", response_model=SuccessResponse | ErrorResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Groq-First Transcription Endpoint.
    - Model: whisper-large-v3-turbo
    - Language: Mixed (Persian/English)
    """
    try:
        # Validate File
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded")
            
        # Execute Transcription
        # We pass the file-like object directly
        result = await audio_service.transcribe_audio(file.file, file.filename)
        
        return SuccessResponse(status="success", result=result)
        
    except AudioProcessingError as e:
        return ErrorResponse(status="error", message=str(e))
    except Exception as e:
        return ErrorResponse(status="error", message=f"System Error: {str(e)}")
