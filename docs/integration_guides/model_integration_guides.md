# Model Integration Guides

## Overview
This document provides detailed instructions for integrating the replacement models: Quwen (via OpenRouter/Local) and Whisper (Medium/Large V3 Turbo).

## 1. Quwen Integration (via OpenRouter)

**Model:** `qwen/qwen2.5-72b-instruct`

### Configuration
Update `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
PRIMARY_PROVIDER=openrouter
OPENROUTER_MODEL=qwen/qwen2.5-72b-instruct
```

### Usage (Python)
```python
from src.infrastructure.ai.openrouter_provider import OpenRouterLLMProvider

provider = OpenRouterLLMProvider()
response = await provider.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model="qwen/qwen2.5-72b-instruct"
)
```

### JSON Mode
Quwen 2.5 is excellent at following instructions. For structured output, append instructions to the system prompt and optionally use `response_format` if supported by the endpoint.

```python
system_prompt = "You are a helpful assistant. Output JSON."
# ...
```

## 2. Whisper Integration (Medium/Large V3 Turbo)

**Models:** 
- `whisper-large-v3-turbo` (High Accuracy)
- `whisper-medium` (Faster, Lower Resource)

### Option A: OpenAI API (Managed)
Uses `whisper-1` which is typically Large V2/V3.

**Configuration:**
```bash
OPENAI_API_KEY=sk-...
PRIMARY_STT_PROVIDER=openai
```

### Option B: Local Inference (Faster-Whisper)
Recommended for privacy and zero cost (requires GPU/CPU).

**Prerequisites:**
```bash
pip install faster-whisper
```

**Configuration:**
```bash
ENABLE_LOCAL_WHISPER=true
WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_DEVICE=auto  # or "cuda", "cpu"
```

**Implementation Snippet:**
```python
from faster_whisper import WhisperModel

def transcribe_local(file_path, model_size="large-v3-turbo"):
    model = WhisperModel(model_size, device="auto", compute_type="float16")
    segments, info = model.transcribe(file_path, beam_size=5)
    return " ".join([segment.text for segment in segments])
```

## 3. Fallback Mechanism

The system is designed to fallback automatically:
1.  **Primary**: OpenRouter (Quwen) / OpenAI (Whisper)
2.  **Secondary**: Local Inference (if enabled)
3.  **Tertiary**: Groq (Legacy, until fully deprecated)

Ensure `app/config.py` has the correct priority list.
