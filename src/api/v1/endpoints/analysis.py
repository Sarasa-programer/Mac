import shutil
import os
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from src.api.schemas.api_models import (
    TranscriptionResponse,
    SummarizeRequest, SummarizeResponse,
    DifferentialDxRequest, DifferentialDxResponse,
    NelsonSearchRequest, NelsonSearchResponse,
    PubMedSearchRequest, PubMedSearchResponse, PubMedArticle,
    KeywordsRequest, KeywordsResponse
)

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload-audio")
async def upload_audio_endpoint(file: UploadFile = File(...)):
    """
    Upload and store audio file.
    Returns the file path and file ID.
    """
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    return {
        "filename": file.filename,
        "file_path": file_location,
        "size": os.path.getsize(file_location),
        "content_type": file.content_type
    }

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Convert audio to text (Mock Whisper).
    """
    # Mock response
    time.sleep(1) # Simulate processing
    return TranscriptionResponse(
        text="This is a 5-year-old male presenting with 5 days of high grade fever, bilateral conjunctivitis, and strawberry tongue.",
        language="en",
        duration=12.5
    )

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_case(request: SummarizeRequest):
    """
    Summarize case text.
    """
    # Mock response
    return SummarizeResponse(
        summary="5yo male with features suggestive of Kawasaki Disease.",
        chief_complaint="Persistent high-grade fever for 5 days.",
        history="Fever up to 104F, bilateral conjunctivitis, cracked lips, strawberry tongue. No cough or rhinorrhea.",
        vitals="T: 39.5C, HR: 130, RR: 24, BP: 90/60"
    )

@router.post("/differential-dx", response_model=DifferentialDxResponse)
async def get_differential_diagnosis(request: DifferentialDxRequest):
    """
    Extract differential diagnoses.
    """
    return DifferentialDxResponse(
        diagnoses=["Kawasaki Disease", "Adenovirus", "Scarlet Fever", "Systemic JIA", "Measles"]
    )

@router.post("/nelson-section", response_model=NelsonSearchResponse)
async def search_nelson(request: NelsonSearchRequest):
    """
    Find Nelson textbook section.
    """
    return NelsonSearchResponse(
        content="Kawasaki disease is an acute systemic vasculitis of unknown cause that primarily affects children younger than 5 years. Diagnosis is clinical, based on fever > 5 days and at least 4 of 5 principal clinical features.",
        source="Nelson Textbook of Pediatrics, 21st Edition, Chapter 167"
    )

@router.post("/pubmed-search", response_model=PubMedSearchResponse)
async def search_pubmed(request: PubMedSearchRequest):
    """
    Search PubMed for the most recent articles.
    """
    return PubMedSearchResponse(
        articles=[
            PubMedArticle(
                title="Diagnosis and Management of Kawasaki Disease.",
                url="https://pubmed.ncbi.nlm.nih.gov/mock1",
                snippet="Review of current guidelines for KD diagnosis...",
                date="2024-01-15"
            ),
            PubMedArticle(
                title="Adenovirus vs Kawasaki Disease: Clinical differentiators.",
                url="https://pubmed.ncbi.nlm.nih.gov/mock2",
                snippet="Comparative study of inflammatory markers...",
                date="2023-11-20"
            )
        ]
    )

@router.post("/keywords", response_model=KeywordsResponse)
async def extract_keywords(request: KeywordsRequest):
    """
    Generate keywords from text.
    """
    return KeywordsResponse(
        keywords=["Fever", "Kawasaki Disease", "Conjunctivitis", "Pediatrics", "Vasculitis"]
    )
