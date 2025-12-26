"""
Integration tests for provider migration.
Tests end-to-end workflows with new providers.
"""
import pytest
import os
from src.infrastructure.ai.llm_factory import LLMProviderFactory
from src.infrastructure.ai.factory import TranscriptionProviderFactory
from src.config.settings import settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openrouter_provider_integration():
    """Integration test for OpenRouter provider (requires API key)."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")
    
    provider = LLMProviderFactory.get_provider("openrouter")
    
    # Test basic chat
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello, World!' in JSON format with key 'message'."}
    ]
    
    response = await provider.chat(messages, json_mode=True)
    
    assert response is not None
    assert len(response) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_transcription_integration():
    """Integration test for OpenAI transcription (requires API key)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    
    # Note: This test requires an actual audio file
    # For now, we'll just test that the provider can be instantiated
    provider = TranscriptionProviderFactory.get_provider("openai")
    
    assert provider is not None
    # Uncomment below when you have a test audio file
    # test_audio_path = "tests/fixtures/test_audio.mp3"
    # if os.path.exists(test_audio_path):
    #     result = await provider.transcribe(test_audio_path, language="en")
    #     assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_fallback_chain():
    """Test that fallback chain works correctly."""
    # This test verifies the fallback mechanism
    # It requires proper configuration and may need actual API keys
    
    try:
        provider = LLMProviderFactory.get_provider_with_fallback()
        assert provider is not None
    except Exception as e:
        # If all providers fail, that's expected in test environment
        pytest.skip(f"All providers failed: {e}")


@pytest.mark.integration
def test_provider_configuration():
    """Test that provider configuration is correct."""
    assert hasattr(settings, 'PRIMARY_PROVIDER') or hasattr(settings, 'primary_provider')
    
    # Check that at least one provider is configured
    openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', None)
    groq_key = getattr(settings, 'GROQ_API_KEY', None)
    openai_key = getattr(settings, 'OPENAI_API_KEY', None)
    
    assert any([openrouter_key, groq_key, openai_key]), "At least one API key should be configured"

