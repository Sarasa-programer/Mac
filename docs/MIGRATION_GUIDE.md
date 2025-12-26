# Model Migration Guide: Groq to Independent Providers

This guide provides step-by-step instructions for migrating from Groq-based models to independent providers (OpenRouter/Qwen, OpenAI/Whisper).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration Setup](#configuration-setup)
3. [Migration Steps](#migration-steps)
4. [Testing](#testing)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required API Keys

1. **OpenRouter API Key** (for Qwen models)
   - Sign up at: https://openrouter.ai/
   - Get your API key from the dashboard
   - Free tier available with rate limits

2. **OpenAI API Key** (for Whisper transcription)
   - Get from: https://platform.openai.com/api-keys
   - Required for Whisper transcription service

### Environment Variables

Add the following to your `.env` file:

```bash
# Primary Provider Selection
PRIMARY_PROVIDER=openrouter
PRIMARY_STT_PROVIDER=openai

# OpenRouter Configuration (for Qwen LLM)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MAIN_MODEL=qwen/qwen2.5-72b-instruct:free
OPENROUTER_FAST_MODEL=qwen/qwen2.5-7b-instruct:free

# OpenAI Configuration (for Whisper STT)
OPENAI_API_KEY=sk-...
OPENAI_WHISPER_MODEL=whisper-1

# Feature Flags
ENABLE_GROQ=false
ENABLE_MODEL_ABSTRACTION=true
ENABLE_FALLBACK=true

# Fallback Chain (comma-separated)
FALLBACK_PROVIDERS=openrouter,openai,groq
```

## Configuration Setup

### Step 1: Update Configuration Files

The migration uses enhanced configuration in:
- `src/config/settings.py` (for src/ services)
- `app/config.py` (for app/ services)

Both files have been updated with:
- Primary provider selection
- OpenRouter and OpenAI settings
- Feature flags for gradual migration
- Fallback chain configuration

### Step 2: Install Dependencies

Ensure you have the required Python packages:

```bash
pip install openai>=1.0.0
pip install httpx
```

The `openai` package is used for both OpenAI and OpenRouter (OpenRouter uses OpenAI-compatible API).

## Migration Steps

### Phase 1: Gradual Migration (Recommended)

1. **Enable Feature Flags**
   ```bash
   ENABLE_GROQ=true  # Keep Groq enabled as fallback
   ENABLE_MODEL_ABSTRACTION=true
   ENABLE_FALLBACK=true
   ```

2. **Set Primary Provider**
   ```bash
   PRIMARY_PROVIDER=openrouter
   PRIMARY_STT_PROVIDER=openai
   ```

3. **Test with Fallback**
   - The system will try OpenRouter first
   - Fall back to Groq if OpenRouter fails
   - Monitor logs for provider usage

4. **Verify Functionality**
   - Run existing test suites
   - Check transcription accuracy
   - Verify analysis quality

### Phase 2: Full Migration

1. **Disable Groq**
   ```bash
   ENABLE_GROQ=false
   ```

2. **Remove Groq API Key** (optional, for security)
   ```bash
   # Comment out or remove
   # GROQ_API_KEY=...
   ```

3. **Update Fallback Chain**
   ```bash
   FALLBACK_PROVIDERS=openrouter,openai
   ```

### Code-Level Changes

#### Using LLM Provider

**Before (Groq-specific)**:
```python
from src.infrastructure.ai.groq_service import GroqService

service = GroqService()
result = await service.analyze_case_comprehensive(transcript)
```

**After (Provider-agnostic)**:
```python
from src.infrastructure.ai.llm_factory import LLMProviderFactory

provider = LLMProviderFactory.get_provider_with_fallback()
result = await provider.analyze_case_comprehensive(transcript)
```

#### Using Transcription Provider

**Before**:
```python
from src.infrastructure.ai.factory import TranscriptionProviderFactory

provider = TranscriptionProviderFactory.get_provider("groq")
transcript = await provider.transcribe(file_path)
```

**After**:
```python
from src.infrastructure.ai.factory import TranscriptionProviderFactory
from src.config.settings import settings

provider_name = settings.PRIMARY_STT_PROVIDER
provider = TranscriptionProviderFactory.get_provider(provider_name)
transcript = await provider.transcribe(file_path)
```

## Testing

### Unit Tests

Run provider-specific unit tests:

```bash
# Test OpenRouter provider
pytest tests/unit/test_openrouter_provider.py

# Test LLM factory
pytest tests/unit/test_llm_factory.py

# Test transcription providers
pytest tests/unit/test_transcription_providers.py
```

### Integration Tests

Test end-to-end workflows:

```bash
# Test case analysis pipeline
pytest tests/integration/test_cases_flow.py

# Test transcription pipeline
pytest tests/integration/test_transcription_flow.py
```

### Manual Testing

1. **Transcription Test**:
   ```python
   from src.infrastructure.ai.factory import TranscriptionProviderFactory
   from src.config.settings import settings
   
   provider = TranscriptionProviderFactory.get_provider(settings.PRIMARY_STT_PROVIDER)
   result = await provider.transcribe("path/to/audio.mp3", language="fa")
   print(result)
   ```

2. **LLM Analysis Test**:
   ```python
   from src.infrastructure.ai.llm_factory import LLMProviderFactory
   
   provider = LLMProviderFactory.get_provider_with_fallback()
   result = await provider.analyze_case_comprehensive("transcript text here")
   print(result)
   ```

## Deployment

### Pre-Deployment Checklist

- [ ] All API keys configured
- [ ] Feature flags set appropriately
- [ ] Fallback chain tested
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Monitoring configured
- [ ] Rollback plan prepared

### Deployment Steps

1. **Deploy to Staging**
   - Use gradual migration settings
   - Monitor for 24-48 hours
   - Verify performance metrics

2. **Gradual Production Rollout**
   - Start with 10% traffic
   - Monitor error rates and latency
   - Increase gradually: 25% → 50% → 100%

3. **Full Cutover**
   - Set `ENABLE_GROQ=false`
   - Remove Groq dependencies
   - Monitor for one week

### Monitoring

Key metrics to monitor:

1. **Provider Usage**:
   - Which provider is handling requests
   - Fallback frequency

2. **Performance**:
   - Response times
   - Error rates
   - Token usage

3. **Costs**:
   - API call counts
   - Cost per request

## Troubleshooting

### Common Issues

#### Issue: OpenRouter API Key Invalid

**Symptoms**: `401 Unauthorized` errors

**Solution**:
```bash
# Verify API key format
OPENROUTER_API_KEY=sk-or-v1-...  # Should start with sk-or-v1-
```

#### Issue: Model Not Available

**Symptoms**: `404 Model not found` errors

**Solution**:
- Check model name spelling
- Verify model is available on OpenRouter
- Try alternative model: `qwen/qwen2.5-32b-instruct:free`

#### Issue: Rate Limiting

**Symptoms**: `429 Too Many Requests` errors

**Solution**:
- Implement request queuing
- Add exponential backoff
- Consider upgrading OpenRouter plan
- Use fallback providers

#### Issue: JSON Mode Not Supported

**Symptoms**: Invalid JSON responses

**Solution**:
- Verify model supports `response_format`
- Check OpenRouter model documentation
- Implement JSON parsing with error handling

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set in environment:

```bash
LOG_LEVEL=DEBUG
```

## Rollback Procedure

If issues occur, rollback quickly:

1. **Quick Rollback** (Feature Flag):
   ```bash
   PRIMARY_PROVIDER=groq
   ENABLE_GROQ=true
   ```

2. **Full Rollback** (Code):
   ```bash
   git checkout v1.0-groq-baseline
   # Redeploy previous version
   ```

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review error messages in application logs
3. Consult `MIGRATION_PLAN.md` for architecture details
4. Open an issue in the repository

## Additional Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [OpenAI Whisper Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- [Qwen Model Card](https://huggingface.co/Qwen/Qwen2.5-72B-Instruct)

