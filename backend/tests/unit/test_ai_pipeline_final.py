import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.infrastructure.ai.ai_router import ai_router, AIServiceRouter

@pytest.fixture
def mock_groq():
    with patch('src.infrastructure.ai.ai_router.groq_service') as mock:
        mock.transcribe_file = AsyncMock(return_value="Transcribed text from Groq")
        yield mock

@pytest.fixture
def mock_gemini():
    with patch('src.infrastructure.ai.ai_router.gemini_service') as mock:
        mock.summarize_text = AsyncMock(return_value={"summary": "Gemini Summary"})
        mock.generate_case_summary = AsyncMock(return_value={
            "title": "Gemini Title",
            "summary": {
                "chiefComplaint": "CC",
                "history": "Hx",
                "vitals": "VS"
            }
        })
        yield mock

@pytest.fixture
def mock_openai():
    with patch('src.infrastructure.ai.ai_router.openai_service') as mock:
        mock.generate_clinical_analysis = AsyncMock(return_value={
            "differentialDiagnosis": ["Dx1"],
            "keywords": ["k1"],
            "nelsonContext": "Context"
        })
        yield mock

@pytest.mark.asyncio
async def test_transcribe_enforces_groq_only(mock_groq):
    """
    Test that transcription uses Groq and does NOT fallback.
    """
    # Success case
    result = await ai_router.transcribe_with_fallback("test.mp3")
    assert result == "Transcribed text from Groq"
    mock_groq.transcribe_file.assert_called_once_with("test.mp3")

    # Failure case
    mock_groq.transcribe_file.side_effect = Exception("Groq Error")
    
    with pytest.raises(Exception) as excinfo:
        await ai_router.transcribe_with_fallback("test.mp3")
    
    assert "Groq Error" in str(excinfo.value)
    # Ensure it didn't try to call others (though others aren't even imported in the method scope usually, but logic check)

@pytest.mark.asyncio
async def test_analyze_case_pipeline_execution(mock_groq, mock_gemini, mock_openai):
    """
    Test the full pipeline: Groq -> (Gemini + GPT)
    """
    result = await ai_router.analyze_case("test.mp3", "audio/mp3")

    # 1. Verify Groq Transcription
    mock_groq.transcribe_file.assert_called_once()
    
    # 2. Verify Gemini Summarization
    mock_gemini.generate_case_summary.assert_called_once_with("Transcribed text from Groq")
    
    # 3. Verify GPT Analysis
    mock_openai.generate_clinical_analysis.assert_called_once_with("Transcribed text from Groq")
    
    # 4. Verify Result Structure
    assert result["transcript"] == "Transcribed text from Groq"
    assert result["title"] == "Gemini Title"
    assert result["differentialDiagnosis"] == ["Dx1"]
    assert result["provider"] == "pipeline(groq+gemini+gpt)"

@pytest.mark.asyncio
async def test_analyze_case_pipeline_failure(mock_groq, mock_gemini, mock_openai):
    """
    Test that if one part fails, the pipeline handles it (currently re-raises).
    """
    mock_groq.transcribe_file.side_effect = Exception("Transcription Failed")
    
    with pytest.raises(Exception) as excinfo:
        await ai_router.analyze_case("test.mp3", "audio/mp3")
    
    assert "Transcription Failed" in str(excinfo.value)
    mock_gemini.generate_case_summary.assert_not_called()
