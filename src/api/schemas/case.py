from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class CaseStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ERROR = "ERROR"

# --- Submission Schemas ---
class SubmissionBase(BaseModel):
    answer_text: str

class SubmissionCreate(SubmissionBase):
    case_id: int

class SubmissionUpdate(BaseModel):
    score: Optional[int] = None
    feedback: Optional[str] = None

class SubmissionResponse(SubmissionBase):
    id: int
    case_id: int
    user_id: int
    score: Optional[int] = None
    feedback: Optional[str] = None
    submitted_at: datetime
    
    class Config:
        from_attributes = True

# --- Case Schemas ---
class CaseBase(BaseModel):
    title: str
    description: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    difficulty_level: Optional[str] = "medium"
    category: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    difficulty_level: Optional[str] = None
    category: Optional[str] = None
    status: Optional[CaseStatus] = None
    audio_path: Optional[str] = None
    transcript: Optional[str] = None
    nelson_context: Optional[str] = None

class CaseSummaryBase(BaseModel):
    chief_complaint: Optional[str] = None
    history: Optional[str] = None
    vitals: Optional[str] = None
    
    class Config:
        from_attributes = True

class DifferentialDiagnosisBase(BaseModel):
    condition: str
    probability: Optional[str] = None
    reasoning: Optional[str] = None
    
    class Config:
        from_attributes = True

class PubMedArticleBase(BaseModel):
    title: str
    url: str
    summary: Optional[str] = None
    
    class Config:
        from_attributes = True

class CaseResponse(CaseBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    date: datetime
    status: CaseStatus = CaseStatus.UPLOADED
    audio_path: Optional[str] = None
    transcript: Optional[str] = None
    nelson_context: Optional[str] = None
    
    summary: Optional[CaseSummaryBase] = None
    differential_diagnoses: List[DifferentialDiagnosisBase] = []
    pubmed_articles: List[PubMedArticleBase] = []
    
    class Config:
        from_attributes = True

class AnalysisResponse(BaseModel):
    case_id: int
    analysis: Any
    generated_at: datetime

# --- Canonical Case Schema (Unified Flow) ---
class NelsonItem(BaseModel):
    title: str
    chapter: Optional[str] = None
    recommendation: Optional[str] = None

class PubMedItem(BaseModel):
    title: Optional[str] = "Untitled Article"
    pmid: Optional[str] = None
    link: Optional[str] = None
    summary: Optional[str] = None

class DifferentialItem(BaseModel):
    disease: str
    reasoning: Optional[str] = None

class SummaryItem(BaseModel):
    chief_complaint: Optional[str] = None
    dashboard_chief_complaint: Optional[str] = None
    hpi: Optional[str] = None
    vitals: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None

class CaseCreateFull(BaseModel):
    source: str # "realtime" | "upload"
    transcript: str
    summary: SummaryItem
    differential_dx: Optional[List[DifferentialItem]] = []
    nelson: Optional[List[NelsonItem]] = []
    pubmed: Optional[List[PubMedItem]] = []
    created_at: Optional[datetime] = None
