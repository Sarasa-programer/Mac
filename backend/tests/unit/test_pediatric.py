import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.routers.pediatric import analyze_pediatric_case, PediatricInput, CaseMetadata, PediatricOutput
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_input_validation_failure():
    # Setup
    input_data = PediatricInput(
        case_id="test_1",
        language="fa",
        transcript="too short",
        metadata=CaseMetadata(source="upload")
    )
    
    # Act
    result = await analyze_pediatric_case(input_data)
    
    # Assert
    assert result.status == "FAILED_INPUT"
    assert "length < 50" in result.debug.failure_reason

@pytest.mark.asyncio
async def test_successful_analysis():
    # Setup
    input_data = PediatricInput(
        case_id="test_2",
        language="en",
        transcript="This is a long transcript containing clinical information such as fever and cough in a 3-year-old child. This text must be over 50 characters to pass the first check.",
        metadata=CaseMetadata(source="upload")
    )
    
    mock_response = {
        "schema_version": "1.0",
        "status": "COMPLETED",
        "case_id": "test_2",
        "summary": "3-year-old boy with fever and cough. Possible diagnosis: Viral infection. This summary text needs to be at least 100 characters long to pass the quality check. So I am adding more sentences to reach the desired length.",
        "differential": [
            {"diagnosis": "Viral Infection", "reasoning": "Mild symptoms and low grade fever suggest viral etiology. This explanation needs to be over 50 characters to be valid."},
            {"diagnosis": "Pneumonia", "reasoning": "If high fever persists, pneumonia should be considered. This explanation also needs to be sufficient in length."}
        ],
        "nelson_reference": "Chapter 123: Viral Infections",
        "urgency_flag": "ROUTINE",
        "debug": {
            "analysis_started": True,
            "transcript_length": 100,
            "transcript_language_detected": "en",
            "declared_language": "en",
            "language_mismatch": False,
            "clinical_signal_detected": True,
            "clinical_signals_found": ["fever"],
            "pediatric_scope_verified": True,
            "patient_age_mentioned": "3 years",
            "multiple_patients_detected": False,
            "ambiguous_data_detected": False,
            "quality_checks_passed": True,
            "processing_time_ms": 100,
            "model_confidence": "high",
            "failure_reason": None
        }
    }
    
    import json
    
    # Mock UnifiedLLMService
    with patch("app.routers.pediatric.UnifiedLLMService") as MockService:
        mock_instance = MockService.return_value
        # Mock groq client being present
        mock_instance.groq_client = MagicMock()
        mock_instance._call_groq = AsyncMock(return_value=json.dumps(mock_response))
        
        # Act
        result = await analyze_pediatric_case(input_data)
        
        # Assert
        assert result.status == "COMPLETED"
        assert result.summary == mock_response["summary"]
        assert len(result.differential) == 2

@pytest.mark.asyncio
async def test_quality_check_failure():
    # Setup
    input_data = PediatricInput(
        case_id="test_3",
        language="en",
        transcript="This is a long transcript containing clinical information and needs to be checked.",
        metadata=CaseMetadata(source="upload")
    )
    
    # Mock response with missing summary
    mock_response = {
        "status": "COMPLETED",
        "case_id": "test_3",
        "summary": "Too short", # Invalid length
        "differential": [], # Invalid count
        "nelson_reference": None,
        "urgency_flag": "ROUTINE",
        "debug": {}
    }
    
    import json
    
    with patch("app.routers.pediatric.UnifiedLLMService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.groq_client = MagicMock()
        mock_instance._call_groq = AsyncMock(return_value=json.dumps(mock_response))
        
        # Act
        result = await analyze_pediatric_case(input_data)
        
        # Assert
        assert result.status == "FAILED_QUALITY"
        assert result.debug.quality_checks_passed == False
