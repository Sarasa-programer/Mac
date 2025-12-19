from typing import List, Optional
from pydantic import BaseModel

class TranscriptionResponse(BaseModel):
    text: str
    language: str = "en"
    duration: float

class SummarizeRequest(BaseModel):
    text: str

class SummarizeResponse(BaseModel):
    summary: str
    chief_complaint: str
    history: str
    vitals: str

class DifferentialDxRequest(BaseModel):
    text: str

class DifferentialDxResponse(BaseModel):
    diagnoses: List[str]

class NelsonSearchRequest(BaseModel):
    keywords: List[str]

class NelsonSearchResponse(BaseModel):
    content: str
    source: str = "Nelson Textbook of Pediatrics"

class PubMedSearchRequest(BaseModel):
    keywords: List[str]

class PubMedArticle(BaseModel):
    title: str
    url: str
    snippet: str
    date: str

class PubMedSearchResponse(BaseModel):
    articles: List[PubMedArticle]

class KeywordsRequest(BaseModel):
    text: str

class KeywordsResponse(BaseModel):
    keywords: List[str]

class HealthCheck(BaseModel):
    status: str
    version: str
