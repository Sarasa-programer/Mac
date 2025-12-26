import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.infrastructure.ai.llm_factory import LLMProviderFactory
from src.infrastructure.ai.factory import TranscriptionProviderFactory
from src.config.settings import settings

class TestModelMigration:

    @pytest.fixture
    def mock_settings(self):
        with patch("src.config.settings.settings") as mock_settings:
            # Set defaults
            mock_settings.OPENAI_API_KEY = "sk-test"
            mock_settings.OPENAI_MODEL = "gpt-4o"
            mock_settings.WHISPER_MODEL_SIZE = "large-v3-turbo"
            mock_settings.WHISPER_DEVICE = "cpu"
            mock_settings.WHISPER_COMPUTE_TYPE = "int8"
            yield mock_settings

    @pytest.mark.asyncio
    async def test_openai_llm_provider_chat(self, mock_settings):
        """Test OpenAI LLM Provider chat functionality."""
        mock_settings.PRIMARY_PROVIDER = "openai"
        
        with patch("src.infrastructure.ai.openai_llm_provider.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Hello from OpenAI"))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Get provider via factory
            provider = LLMProviderFactory.get_provider("openai")
            
            # Act
            response = await provider.chat([{"role": "user", "content": "Hi"}])
            
            # Assert
            assert response == "Hello from OpenAI"
            mock_client.chat.completions.create.assert_called_once()
            args, kwargs = mock_client.chat.completions.create.call_args
            assert kwargs["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_local_whisper_provider_transcribe(self, mock_settings):
        """Test Local Whisper Provider transcription."""
        mock_settings.ENABLE_LOCAL_WHISPER = True
        mock_settings.WHISPER_MODEL_SIZE = "large-v3-turbo"
        
        # Mock faster_whisper module
        mock_faster_whisper = MagicMock()
        mock_model_cls = MagicMock()
        mock_faster_whisper.WhisperModel = mock_model_cls
        
        with patch.dict("sys.modules", {"faster_whisper": mock_faster_whisper}):
            # Import inside the patch context to pick up the mock
            from src.infrastructure.ai.local_whisper_provider import LocalWhisperProvider
            
            # Setup mock model instance
            mock_model = MagicMock()
            mock_model_cls.return_value = mock_model
            
            # Mock transcribe result
            mock_segment = MagicMock()
            mock_segment.text = "Hello world"
            mock_model.transcribe.return_value = ([mock_segment], None)
            
            # Instantiate provider
            provider = LocalWhisperProvider()
            
            # Act
            # Since we used run_in_executor, we need to ensure the loop runs it.
            # Ideally we mock the executor or loop, but for now let's see if the default loop handles the mock call.
            # Because run_in_executor(None, func) runs func in default executor (thread pool).
            result = await provider.transcribe("test.wav")
            
            # Assert
            assert result == "Hello world"
            mock_model.transcribe.assert_called_once()

    def test_factory_openai_resolution(self, mock_settings):
        """Test LLM Factory resolves OpenAI correctly."""
        with patch("src.infrastructure.ai.openai_llm_provider.AsyncOpenAI"):
            provider = LLMProviderFactory.get_provider("openai")
            from src.infrastructure.ai.openai_llm_provider import OpenAILLMProvider
            assert isinstance(provider, OpenAILLMProvider)

    def test_factory_local_whisper_resolution(self, mock_settings):
        """Test Transcription Factory resolves Local Whisper correctly."""
        mock_faster_whisper = MagicMock()
        with patch.dict("sys.modules", {"faster_whisper": mock_faster_whisper}):
            provider = TranscriptionProviderFactory.get_provider("local")
            from src.infrastructure.ai.local_whisper_provider import LocalWhisperProvider
            assert isinstance(provider, LocalWhisperProvider)
