"""
Unit tests for OpenRouter LLM Provider.
Tests the Qwen model integration through OpenRouter API.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.infrastructure.ai.openrouter_provider import OpenRouterLLMProvider
from src.config.settings import settings


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI-compatible client for OpenRouter."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def openrouter_provider(mock_openai_client):
    """Create OpenRouter provider with mocked client."""
    with patch('src.infrastructure.ai.openrouter_provider.AsyncOpenAI') as mock_openai_class:
        mock_openai_class.return_value = mock_openai_client
        provider = OpenRouterLLMProvider()
        provider.client = mock_openai_client
        return provider


@pytest.mark.asyncio
async def test_chat_completion(openrouter_provider, mock_openai_client):
    """Test basic chat completion."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    # Test
    messages = [{"role": "user", "content": "Hello"}]
    result = await openrouter_provider.chat(messages)
    
    # Verify
    assert result == "Test response"
    mock_openai_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == openrouter_provider.main_model
    assert call_kwargs["messages"] == messages


@pytest.mark.asyncio
async def test_chat_with_json_mode(openrouter_provider, mock_openai_client):
    """Test chat completion with JSON mode enabled."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"key": "value"}'
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    messages = [{"role": "user", "content": "Return JSON"}]
    result = await openrouter_provider.chat(messages, json_mode=True)
    
    assert result == '{"key": "value"}'
    call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
    assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_analyze_case_comprehensive(openrouter_provider, mock_openai_client):
    """Test comprehensive case analysis."""
    # Mock response with valid JSON
    expected_json = {
        "title": "Test Case",
        "summary": {
            "chiefComplaint": "Fever",
            "history": "Recent illness",
            "vitals": "Normal"
        },
        "differentialDiagnosis": ["Diagnosis 1", "Diagnosis 2"],
        "keywords": ["keyword1", "keyword2"],
        "nelsonContext": "Context from Nelson"
    }
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(expected_json)
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    # Test
    transcript = "Patient presents with fever and cough."
    result = await openrouter_provider.analyze_case_comprehensive(transcript)
    
    # Verify structure
    assert result["title"] == expected_json["title"]
    assert "summary" in result
    assert "differentialDiagnosis" in result
    assert "keywords" in result
    assert "nelsonContext" in result


@pytest.mark.asyncio
async def test_analyze_case_invalid_json(openrouter_provider, mock_openai_client):
    """Test case analysis with invalid JSON response (should return safe default)."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Invalid JSON response"
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    transcript = "Test transcript"
    result = await openrouter_provider.analyze_case_comprehensive(transcript)
    
    # Should return safe default structure
    assert result["title"] == "Analysis Failed"
    assert result["summary"]["chiefComplaint"] == "N/A"
    assert result["differentialDiagnosis"] == []
    assert result["keywords"] == []


@pytest.mark.asyncio
async def test_chat_error_handling(openrouter_provider, mock_openai_client):
    """Test error handling in chat method."""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
    
    messages = [{"role": "user", "content": "Test"}]
    
    with pytest.raises(Exception) as exc_info:
        await openrouter_provider.chat(messages)
    
    assert "API Error" in str(exc_info.value)

