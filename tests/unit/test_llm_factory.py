"""
Unit tests for LLM Provider Factory.
Tests provider selection, fallback mechanisms, and feature flags.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.infrastructure.ai.llm_factory import LLMProviderFactory
from src.config.settings import settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('src.infrastructure.ai.llm_factory.settings') as mock_settings:
        mock_settings.PRIMARY_PROVIDER = 'openrouter'
        mock_settings.ENABLE_GROQ = True
        mock_settings.fallback_providers_list = ['openrouter', 'openai', 'groq']
        yield mock_settings


@pytest.mark.asyncio
async def test_get_provider_openrouter(mock_settings):
    """Test getting OpenRouter provider."""
    with patch('src.infrastructure.ai.llm_factory.OpenRouterLLMProvider') as mock_provider_class:
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        provider = LLMProviderFactory.get_provider("openrouter")
        
        assert provider == mock_provider
        mock_provider_class.assert_called_once()


def test_get_provider_groq_enabled(mock_settings):
    """Test getting Groq provider when enabled."""
    mock_settings.ENABLE_GROQ = True
    
    with patch('src.infrastructure.ai.llm_factory.GroqLLMProvider') as mock_provider_class:
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        provider = LLMProviderFactory.get_provider("groq")
        
        assert provider == mock_provider
        mock_provider_class.assert_called_once()


def test_get_provider_groq_disabled(mock_settings):
    """Test getting Groq provider when disabled (should fallback to OpenRouter)."""
    mock_settings.ENABLE_GROQ = False
    
    with patch('src.infrastructure.ai.llm_factory.OpenRouterLLMProvider') as mock_openrouter:
        mock_provider = MagicMock()
        mock_openrouter.return_value = mock_provider
        
        provider = LLMProviderFactory.get_provider("groq")
        
        # Should fallback to OpenRouter
        assert provider == mock_provider
        mock_openrouter.assert_called_once()


def test_get_provider_with_fallback_success(mock_settings):
    """Test provider selection with fallback chain - primary succeeds."""
    mock_settings.PRIMARY_PROVIDER = 'openrouter'
    mock_settings.fallback_providers_list = ['openrouter', 'groq']
    
    with patch('src.infrastructure.ai.llm_factory.OpenRouterLLMProvider') as mock_openrouter:
        mock_provider = MagicMock()
        mock_openrouter.return_value = mock_provider
        
        provider = LLMProviderFactory.get_provider_with_fallback()
        
        assert provider == mock_provider
        mock_openrouter.assert_called_once()


def test_get_provider_with_fallback_chain(mock_settings):
    """Test provider selection with fallback chain - primary fails, fallback succeeds."""
    mock_settings.PRIMARY_PROVIDER = 'openrouter'
    mock_settings.fallback_providers_list = ['openrouter', 'groq']
    
    with patch('src.infrastructure.ai.llm_factory.OpenRouterLLMProvider') as mock_openrouter:
        mock_openrouter.side_effect = Exception("OpenRouter failed")
        
        with patch('src.infrastructure.ai.llm_factory.GroqLLMProvider') as mock_groq:
            mock_provider = MagicMock()
            mock_groq.return_value = mock_provider
            
            provider = LLMProviderFactory.get_provider_with_fallback()
            
            # Should use Groq as fallback
            assert provider == mock_provider
            mock_groq.assert_called_once()


def test_get_provider_unknown_defaults_to_openrouter(mock_settings):
    """Test that unknown provider defaults to OpenRouter."""
    with patch('src.infrastructure.ai.llm_factory.OpenRouterLLMProvider') as mock_openrouter:
        mock_provider = MagicMock()
        mock_openrouter.return_value = mock_provider
        
        provider = LLMProviderFactory.get_provider("unknown_provider")
        
        # Should default to OpenRouter
        assert provider == mock_provider

