import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.openai_service import analyze_audio_case, find_pubmed_articles

# Mock data
MOCK_TRANSCRIPT = "This is a test transcript."
MOCK_ANALYSIS_JSON = {
    "title": "Test Case",
    "transcript": MOCK_TRANSCRIPT,
    "summary": {
        "chiefComplaint": "Fever",
        "history": "History of fever",
        "vitals": "Stable"
    },
    "differentialDiagnosis": ["Flu", "Covid"],
    "keywords": ["fever"],
    "nelsonContext": "Fever context"
}

@pytest.mark.asyncio
async def test_analyze_audio_case_success():
    # Mock OpenAI client
    with patch("app.services.openai_service.client") as mock_client:
        # Mock Transcription
        mock_transcription = MagicMock()
        mock_transcription.text = MOCK_TRANSCRIPT # Set the attribute directly
        # Wait, the code uses .text on the result? 
        # In the implementation: transcription = client.audio.transcriptions.create(..., response_format="text")
        # If response_format="text", the return value IS the string, not an object with .text
        # Let's double check implementation.
        # implementation: transcript_text = transcription
        # So mock return value should be string.
        mock_client.audio.transcriptions.create.return_value = MOCK_TRANSCRIPT
        
        # Mock Chat Completion
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_message.content = str(MOCK_ANALYSIS_JSON).replace("'", '"') # valid json string
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Call function
        # Mock open() as well since it reads a file
        with patch("builtins.open", new_callable=MagicMock):
            result = await analyze_audio_case("test.mp3")
            
        assert result["title"] == "Test Case"
        assert result["transcript"] == MOCK_TRANSCRIPT
        assert len(result["differentialDiagnosis"]) == 2

@pytest.mark.asyncio
async def test_find_pubmed_articles():
    keywords = ["fever", "pediatrics"]
    articles = await find_pubmed_articles(keywords)
    
    assert len(articles) == 2
    assert "fever" in articles[0]["url"]
    assert "PubMed" in articles[0]["title"]
