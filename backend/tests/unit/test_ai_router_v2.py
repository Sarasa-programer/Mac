import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.ai_router import ai_router

@pytest.mark.asyncio
async def test_router_mp4_transcription_groq():
    # Setup
    with patch("app.services.ai_router.groq_service.transcribe_file", new_callable=AsyncMock) as mock_groq_transcribe, \
         patch("app.services.ai_router.gemini_service.summarize_text", new_callable=AsyncMock) as mock_gemini_summarize:
        
        mock_groq_transcribe.return_value = "Video transcript"
        mock_gemini_summarize.return_value = {"summary": "done", "provider": "gemini"}
        
        # Act
        result = await ai_router.analyze_case("video.mp4", "video/mp4", preferred_provider="gemini")
        
        # Assert
        mock_groq_transcribe.assert_called_once_with("video.mp4")
        mock_gemini_summarize.assert_called_once_with("Video transcript")
        assert result["transcript"] == "Video transcript"

@pytest.mark.asyncio
async def test_router_transcription_no_fallback_openai():
    # Setup
    with patch("app.services.ai_router.groq_service.transcribe_file", new_callable=AsyncMock) as mock_groq_transcribe, \
         patch("app.services.ai_router.openai_service.transcribe_file", new_callable=AsyncMock) as mock_openai_transcribe:
        
        # Groq fails
        mock_groq_transcribe.side_effect = Exception("Rate Limit")
        
        # Act & Assert
        # Should raise exception and NOT call OpenAI
        with pytest.raises(Exception):
            await ai_router.analyze_case("video.mp4", "video/mp4")
        
        mock_groq_transcribe.assert_called_once()
        mock_openai_transcribe.assert_not_called()

@pytest.mark.asyncio
async def test_router_summarization_fallback_openai():
    # Setup
    with patch("app.services.ai_router.groq_service.transcribe_file", new_callable=AsyncMock) as mock_groq, \
         patch("app.services.ai_router.gemini_service.summarize_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai_router.openai_service.summarize_text", new_callable=AsyncMock) as mock_openai:
        
        mock_groq.return_value = "Transcript"
        # Gemini fails
        mock_gemini.side_effect = Exception("Quota")
        # OpenAI succeeds
        mock_openai.return_value = {"summary": "done", "provider": "openai"}
        
        # Act
        # We explicitly prefer Gemini to test the Gemini -> OpenAI fallback chain
        result = await ai_router.analyze_case("test.mp3", "audio/mp3", preferred_provider="gemini")
        
        # Assert
        mock_gemini.assert_called_once()
        mock_openai.assert_called_once()
        assert result["provider"] == "openai"
