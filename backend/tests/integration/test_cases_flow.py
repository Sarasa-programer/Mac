import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.models.case import Case
from app.schemas.case import CaseStatus 
from app.db.session import get_db
import openai

client = TestClient(app)
from app.api.v1.endpoints.auth import get_current_user 

def test_analyze_case_flow_success_openai():
    # 1. Setup
    mock_case = MagicMock()
    mock_case.id = 1
    mock_case.status = "UPLOADED"
    mock_case.audio_path = "test.mp3"
    mock_case.transcript = None
    mock_case.summary = None
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_case
    
    # Override Auth
    mock_user = MagicMock()
    mock_user.id = 1
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    # Mock the service calls
    with patch("app.api.v1.endpoints.cases.openai_ai.analyze_audio_case", new_callable=AsyncMock) as mock_analyze, \
         patch("app.api.v1.endpoints.cases.openai_ai.find_pubmed_articles", new_callable=AsyncMock) as mock_pubmed, \
         patch("app.api.v1.endpoints.cases.cache.get") as mock_cache_get, \
         patch("app.api.v1.endpoints.cases.cache.set") as mock_cache_set:
         
        mock_analyze.return_value = {
            "title": "Analyzed Case",
            "transcript": "Fever detected.",
            "summary": {},
            "differentialDiagnosis": [],
            "keywords": ["fever"]
        }
        mock_pubmed.return_value = []
        mock_cache_get.return_value = None
        
        # Act
        response = client.post("/api/v1/cases/1/analyze")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["provider"] == "openai"
        
        app.dependency_overrides = {}

def test_analyze_case_fallback_gemini():
    # 1. Setup
    mock_case = MagicMock()
    mock_case.id = 2
    mock_case.status = "UPLOADED"
    mock_case.audio_path = "test.mp3"
    mock_case.transcript = None
    mock_case.summary = None
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_case
    
    mock_user = MagicMock()
    mock_user.id = 1
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    # Mock OpenAI to fail, Gemini to succeed
    with patch("app.api.v1.endpoints.cases.openai_ai.analyze_audio_case", new_callable=AsyncMock) as mock_openai_analyze, \
         patch("app.api.v1.endpoints.cases.gemini_ai.analyze_audio_case", new_callable=AsyncMock) as mock_gemini_analyze, \
         patch("app.api.v1.endpoints.cases.gemini_ai.find_pubmed_articles", new_callable=AsyncMock) as mock_gemini_pubmed, \
         patch("app.api.v1.endpoints.cases.cache.get") as mock_cache_get, \
         patch("app.api.v1.endpoints.cases.cache.set") as mock_cache_set:
         
        # Simulate RateLimitError
        mock_openai_analyze.side_effect = openai.RateLimitError(
            message="Rate limit exceeded", 
            response=MagicMock(), 
            body={}
        )
        
        mock_gemini_analyze.return_value = {
            "title": "Gemini Analyzed",
            "transcript": "Gemini transcript",
            "summary": {},
            "differentialDiagnosis": [],
            "keywords": ["gemini"]
        }
        mock_gemini_pubmed.return_value = []
        mock_cache_get.return_value = None
        
        # Act
        response = client.post("/api/v1/cases/2/analyze")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["provider"] == "gemini"
        
        # Verify calls
        mock_openai_analyze.assert_called_once()
        mock_gemini_analyze.assert_called_once()
        
        app.dependency_overrides = {}
