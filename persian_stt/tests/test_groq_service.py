import pytest
from unittest.mock import AsyncMock, patch
from app.services.groq_service import GroqService

@pytest.mark.asyncio
async def test_groq_transcribe_success():
    # Mock the AsyncGroq client
    with patch("app.services.groq_service.AsyncGroq") as MockClient:
        # Setup mock instance
        mock_instance = MockClient.return_value
        mock_instance.audio.transcriptions.create = AsyncMock()
        
        # Mock response object
        mock_response = AsyncMock()
        mock_response.text = "سلام دنیا"
        mock_instance.audio.transcriptions.create.return_value = mock_response
        
        service = GroqService()
        result = await service.transcribe(b"fake_audio_bytes", prompt="previous context")
        
        assert result == "سلام دنیا"
        
        # Verify call arguments
        mock_instance.audio.transcriptions.create.assert_called_once()
        call_kwargs = mock_instance.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["model"] == "whisper-large-v3"
        assert call_kwargs["language"] == "fa"
        assert call_kwargs["prompt"] == "previous context"

@pytest.mark.asyncio
async def test_groq_transcribe_error():
    with patch("app.services.groq_service.AsyncGroq") as MockClient:
        mock_instance = MockClient.return_value
        # Simulate API error
        mock_instance.audio.transcriptions.create.side_effect = Exception("API Error")
        
        service = GroqService()
        result = await service.transcribe(b"bytes")
        
        assert result is None
