import shutil
import os
import logging
import re
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.infrastructure.db.session import get_db
from src.core.domain.user import User
from src.core.domain.case import Case, CaseSummary, DifferentialDiagnosis, PubMedArticle, Submission
from src.api.schemas.case import (
    CaseCreate, CaseUpdate, CaseResponse, AnalysisResponse, 
    SubmissionCreate, SubmissionResponse, CaseStatus, CaseCreateFull
)
from src.api.v1.endpoints.auth import get_current_user, require_role
import openai
from src.infrastructure.ai.ai_router import ai_router
from src.infrastructure.cache.redis import cache
# from src.infrastructure.ai.ai_pipeline import AIPipeline

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def extract_chief_complaint(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    patterns = [
        r"chief complaint\s*[:\-]\s*(.+)",
        r"presenting complaint\s*[:\-]\s*(.+)",
        r"reason for visit\s*[:\-]\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            complaint = match.group(1).strip()
            complaint = complaint.split("\n")[0].strip()
            if len(complaint) > 300:
                complaint = complaint[:297].rsplit(" ", 1)[0].strip()
            if complaint:
                return complaint
    first_line = text.strip().split("\n", 1)[0].strip()
    if first_line:
        if len(first_line) > 300:
            first_line = first_line[:297].rsplit(" ", 1)[0].strip()
        return first_line
    return None

@router.post("/save", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def save_case(
    case_data: CaseCreateFull,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """
    Unified Endpoint to save a completed case (from Realtime or Upload).
    Persists transcript, summary, differential, nelson, pubmed.
    """
    
    transcript_text = case_data.transcript or ""
    
    # 1. Dashboard Chief Complaint (Short phrase)
    dashboard_cc = ""
    if case_data.summary and case_data.summary.dashboard_chief_complaint:
        dashboard_cc = case_data.summary.dashboard_chief_complaint.strip()
    
    # 2. Summary Chief Complaint (Clinical reformulation)
    summary_cc = ""
    if case_data.summary and case_data.summary.chief_complaint:
        summary_cc = case_data.summary.chief_complaint.strip()

    # Fallback for Dashboard CC
    if not dashboard_cc:
        derived = extract_chief_complaint(transcript_text) or summary_cc
        if derived and len(derived.split()) > 10:
             dashboard_cc = " ".join(derived.split()[:6])
        else:
             dashboard_cc = derived

    title = "Untitled Case"
    if dashboard_cc:
        title = dashboard_cc[:100]
    else:
        title = f"Case from {case_data.source.title()} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    # Serialize Nelson to string (since DB is Text)
    nelson_text = ""
    if case_data.nelson:
        lines = []
        for n in case_data.nelson:
            lines.append(f"Title: {n.title}")
            if n.chapter: lines.append(f"Chapter: {n.chapter}")
            if n.recommendation: lines.append(f"Rec: {n.recommendation}")
            lines.append("---")
        nelson_text = "\n".join(lines)

    # Prepare Description (Assessment + Plan)
    description = ""
    if case_data.summary.assessment:
        description += f"Assessment: {case_data.summary.assessment}\n\n"
    if case_data.summary.plan:
        description += f"Plan: {case_data.summary.plan}"
    
    if not description:
        description = "No assessment provided."

    new_case = Case(
        title=title,
        description=description,
        transcript=transcript_text,
        nelson_context=nelson_text,
        status=CaseStatus.READY.value,
        created_by_id=current_user.id,
        created_at=case_data.created_at or datetime.utcnow(),
        chief_complaint=dashboard_cc,
        difficulty_level="medium",
        category="General",
        audio_path=""
    )
    
    session.add(new_case)
    session.commit()
    session.refresh(new_case)
    
    try:
        summary = CaseSummary(
            case_id=new_case.id,
            chief_complaint=summary_cc or dashboard_cc,
            history=case_data.summary.hpi,
            vitals=case_data.summary.vitals or ""
        )
        session.add(summary)
        
        # 3. Save Differential
        if case_data.differential_dx:
            for dx in case_data.differential_dx:
                new_dx = DifferentialDiagnosis(
                    case_id=new_case.id,
                    condition=dx.disease,
                    reasoning=dx.reasoning,
                    probability="Unknown"
                )
                session.add(new_dx)
            
        # 4. Save PubMed
        if case_data.pubmed:
            for paper in case_data.pubmed:
                new_paper = PubMedArticle(
                    case_id=new_case.id,
                    title=paper.title or "Untitled Article",
                    url=paper.link or (f"https://pubmed.ncbi.nlm.nih.gov/{paper.pmid}/" if paper.pmid else "#"),
                    summary=paper.summary or ""
                )
                session.add(new_paper)
            
        session.commit()
        session.refresh(new_case)
    except Exception as e:
        logger.error(f"Failed to save case details (Summary/Diff/PubMed) for Case {new_case.id}: {e}")
        # Note: We do not rollback the creation of the Case itself, 
        # as we want to preserve the partial record. 
        # But we should rollback the failed transaction for details.
        session.rollback()
        # We can choose to raise an error or just return the case with what we have.
        # Returning partial case is better UX than 500 error after 200 creation.
    
    return new_case

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    current_user: User = Depends(require_role("professor")), 
    session: Session = Depends(get_db)
):
    """Create a new case - Teachers only"""
    
    new_case = Case(
        title=case_data.title,
        description=case_data.description,
        patient_age=case_data.patient_age,
        patient_gender=case_data.patient_gender,
        chief_complaint=case_data.chief_complaint,
        diagnosis=case_data.diagnosis,
        difficulty_level=case_data.difficulty_level,
        category=case_data.category,
        created_by_id=current_user.id,
        created_at=datetime.utcnow(),
        status=CaseStatus.UPLOADED.value
    )
    
    session.add(new_case)
    session.commit()
    session.refresh(new_case)
    
    return new_case

@router.post("/upload", response_model=CaseResponse)
def upload_audio_case(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    """Upload audio for a case"""
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    # Create initial case entry
    new_case = Case(
        title=file.filename or "Untitled",
        description="Audio uploaded case", # Default description
        audio_path=file_location,
        status=CaseStatus.UPLOADED.value,
        created_by_id=current_user.id
    )
    session.add(new_case)
    session.commit()
    session.refresh(new_case)
    return new_case

@router.get("/", response_model=List[CaseResponse])
async def get_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Get list of cases"""
    
    query = session.query(Case)
    
    # Filter by category
    if category:
        query = query.filter(Case.category == category)
    
    # Filter by difficulty
    if difficulty:
        query = query.filter(Case.difficulty_level == difficulty)
    
    cases = query.order_by(desc(Case.created_at)).offset(skip).limit(limit).all()
    return cases

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Get case details"""
    
    case = session.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    return case

@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_data: CaseUpdate,
    current_user: User = Depends(require_role("professor")),
    session: Session = Depends(get_db)
):
    """Update case - Teachers only"""
    
    case = session.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Update fields
    update_data = case_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'status' and value:
             setattr(case, field, value.value) # Handle Enum
        else:
             setattr(case, field, value)
    
    case.updated_at = datetime.utcnow()
    
    session.add(case)
    session.commit()
    session.refresh(case)
    
    return case

@router.delete("/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_cases(
    current_user: User = Depends(require_role("professor")),
    session: Session = Depends(get_db)
):
    cases = session.query(Case).all()
    if not cases:
        return None
    audio_files = [c.audio_path for c in cases if c.audio_path]
    for case in cases:
        session.delete(case)
    session.commit()
    for path in audio_files:
        if not path:
            continue
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
    return None


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    current_user: User = Depends(require_role("professor")),
    session: Session = Depends(get_db)
):
    """Delete case - Teachers only"""
    
    case = session.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    session.delete(case)
    session.commit()
    
    return None

@router.post("/{case_id}/analyze")
async def analyze_case(
    case_id: int,
    provider: str = Query("openai", regex="^(openai|gemini|groq)$"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Analyze case with Cloud AI (OpenAI or Gemini)"""
    
    case = session.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if not case.audio_path:
         raise HTTPException(status_code=400, detail="Case has no audio to analyze")

    # Optimization: Check Redis Cache first
    cache_key = f"case_analysis:{case_id}:{provider}"
    cached_result = cache.get(cache_key)
    if cached_result:
        # If we have a cached result, we might want to ensure the DB is consistent, 
        # but for now, we trust the cache or assume DB is already updated if cache exists.
        # However, if this is a "retry" on a case that failed DB save but cached (unlikely), 
        # we might want to proceed.
        # Simplest approach: If cache exists, return it.
        return cached_result

    # Optimization: Cache Check (DB Status)
    # If case is already analyzed (READY) and has transcript, return existing data to save cost.
    if case.status == CaseStatus.READY.value and case.transcript:
         # Re-fetch related data to return full object if needed, 
         # but this endpoint returns a status summary usually.
         # For this "Action", we just return success immediately.
         return {
            "status": "success", 
            "case_id": case.id,
            "transcript_preview": case.transcript[:100],
            "keywords": [] # Retrieve from DB if stored, or just empty list for cache hit
        }

    case.status = CaseStatus.PROCESSING.value
    session.commit()
    
    try:
        # 1. Analyze with AI (Fallback Logic via Router)
        # Determine mime type based on extension
        mime_type = "audio/mp3"
        if case.audio_path.endswith(".wav"):
            mime_type = "audio/wav"
        elif case.audio_path.endswith(".m4a"):
            mime_type = "audio/x-m4a"
        elif case.audio_path.endswith(".mp4"):
            mime_type = "video/mp4"
            
        try:
            print(f"Attempting analysis via AI Router (Preferred: {provider.upper()}) for case {case.id}...")
            analysis_result = await ai_router.analyze_case(case.audio_path, mime_type, preferred_provider=provider)
            used_provider = analysis_result.get("provider", provider)
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            msg = str(e)
            if "Authentication failed" in msg or "invalid api key" in msg.lower():
                raise HTTPException(status_code=401, detail="Invalid API credentials for AI provider. Please verify GROQ_API_KEY/OPENAI_API_KEY/GOOGLE_API_KEY.")
            rate_limited = ("quota" in msg.lower() or "rate limit" in msg.lower())
            raise HTTPException(
                status_code=429 if rate_limited else 500,
                detail=f"Analysis failed. {'Rate limited' if rate_limited else 'Provider error'}: {msg}"
            )

        case.title = analysis_result.get("title", case.title)
        transcript_text = analysis_result.get("transcript", "") or case.transcript or ""
        case.transcript = transcript_text
        case.nelson_context = analysis_result.get("nelsonContext", "")
        case.status = CaseStatus.READY.value
        
        summary_data = analysis_result.get("summary", {}) or {}
        
        # 1. Dashboard CC (Short phrase)
        dashboard_cc = summary_data.get("dashboardChiefComplaint") or summary_data.get("dashboard_chief_complaint")
        
        # 2. Summary CC (Clinical reformulation)
        summary_cc = summary_data.get("chiefComplaint") or summary_data.get("chief_complaint") or ""
        
        # Fallback for Dashboard CC if AI missed it
        if not dashboard_cc:
             derived = extract_chief_complaint(transcript_text) or summary_cc
             # Force truncate if derived is too long
             if derived and len(derived.split()) > 10:
                 dashboard_cc = " ".join(derived.split()[:6])
             else:
                 dashboard_cc = derived

        case.chief_complaint = (dashboard_cc or "").strip()
        
        if case.summary:
            case.summary.chief_complaint = (summary_cc or dashboard_cc or "").strip()
            case.summary.history = summary_data.get("history", "")
            case.summary.vitals = summary_data.get("vitals", "")
        else:
            summary = CaseSummary(
                case_id=case.id,
                chief_complaint=(summary_cc or dashboard_cc or "").strip(),
                history=summary_data.get("history", ""),
                vitals=summary_data.get("vitals", "")
            )
            session.add(summary)
            
        # 4. Update Differential Diagnosis
        # Clear existing
        session.query(DifferentialDiagnosis).filter(DifferentialDiagnosis.case_id == case.id).delete()
        
        dx_list = analysis_result.get("differentialDiagnosis", [])
        for dx in dx_list:
            # simple string or object? Schema says string in Gemini prompt
            new_dx = DifferentialDiagnosis(
                case_id=case.id,
                condition=dx,
                probability="Unknown", # AI didn't return probability
                reasoning=""
            )
            session.add(new_dx)

        # 5. Search Papers
        keywords = analysis_result.get("keywords", [])
        try:
            papers = await ai_router.find_pubmed_articles(keywords, preferred_provider=used_provider)
        except Exception as e:
            print(f"⚠️ Paper search failed: {e}")
            papers = []
        
        # Clear existing papers
        session.query(PubMedArticle).filter(PubMedArticle.case_id == case.id).delete()
        
        for paper in papers:
            new_article = PubMedArticle(
                case_id=case.id,
                title=paper["title"],
                url=paper["url"],
                summary=paper.get("snippet", "")
            )
            session.add(new_article)
            
        session.commit()
        session.refresh(case)
        
        result = {
            "status": "success", 
            "case_id": case.id,
            "transcript_preview": case.transcript[:100] if case.transcript else "",
            "keywords": keywords,
            "provider": used_provider
        }
        
        # Cache the result
        cache.set(cache_key, result, ttl=3600 * 24) # Cache for 24 hours
        
        return result
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        case.status = CaseStatus.ERROR.value
        session.commit()
        raise he
    except Exception as e:
        case.status = CaseStatus.ERROR.value
        session.commit()
        # Log the full error for debugging
        print(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# --- Submission Endpoints ---

@router.post("/{case_id}/submit", response_model=SubmissionResponse)
async def submit_case_answer(
    case_id: int,
    submission_data: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Submit an answer for a case"""
    # Check if case exists
    case = session.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Check if user already submitted? (Optional rule, allowing multiple for now)
    
    new_submission = Submission(
        case_id=case_id,
        user_id=current_user.id,
        answer_text=submission_data.answer_text,
        submitted_at=datetime.utcnow()
    )
    
    session.add(new_submission)
    session.commit()
    session.refresh(new_submission)
    
    return new_submission

@router.get("/{case_id}/submissions", response_model=List[SubmissionResponse])
async def get_case_submissions(
    case_id: int,
    current_user: User = Depends(require_role("professor")),
    session: Session = Depends(get_db)
):
    """Get all submissions for a specific case (Professor only)"""
    submissions = session.query(Submission).filter(Submission.case_id == case_id).all()
    return submissions

@router.get("/submissions/me", response_model=List[SubmissionResponse])
async def get_my_submissions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Get current user's submissions"""
    submissions = session.query(Submission).filter(Submission.user_id == current_user.id).all()
    return submissions
