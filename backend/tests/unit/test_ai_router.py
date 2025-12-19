import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.ai_router import ai_router

@pytest.mark.asyncio
async def test_router_fallback_success_first_try():
    # Setup
    with patch("app.services.ai_router.openai_service.analyze_audio_case", new_callable=AsyncMock) as mock_openai:
        mock_openai.return_value = {"provider": "openai", "result": "success"}
        
        # Act
        result = await ai_router.analyze_case("test.mp3", "audio/mp3", preferred_provider="openai")
        
        # Assert
        assert result["provider"] == "openai"
        mock_openai.assert_called_once()

@pytest.mark.asyncio
async def test_router_fallback_to_gemini():
    # Setup
    with patch("app.services.ai_router.openai_service.analyze_audio_case", new_callable=AsyncMock) as mock_openai, \
         patch("app.services.ai_router.gemini_service.analyze_audio_case", new_callable=AsyncMock) as mock_gemini:
        
        # OpenAI fails
        mock_openai.side_effect = Exception("Quota Exceeded")
        # Gemini succeeds
        mock_gemini.return_value = {"result": "success"} # Provider added by router
        
        # Act
        result = await ai_router.analyze_case("test.mp3", "audio/mp3", preferred_provider="openai")
        
        # Assert
        assert result["provider"] == "gemini"
        mock_openai.assert_called_once()
        mock_gemini.assert_called_once()

@pytest.mark.asyncio
async def test_router_fallback_to_groq():
    # Setup
    with patch("app.services.ai_router.openai_service.analyze_audio_case", new_callable=AsyncMock) as mock_openai, \
         patch("app.services.ai_router.gemini_service.analyze_audio_case", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai_router.groq_service.analyze_audio_case", new_callable=AsyncMock) as mock_groq:
        
        # OpenAI fails
        mock_openai.side_effect = Exception("Quota Exceeded")
        # Gemini fails
        mock_gemini.side_effect = Exception("Rate Limit")
        # Groq succeeds
        mock_groq.return_value = {"result": "success"}
        
        # Act
        result = await ai_router.analyze_case("test.mp3", "audio/mp3", preferred_provider="openai")
        
        # Assert
        assert result["provider"] == "groq"
        mock_openai.assert_called_once()
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()
