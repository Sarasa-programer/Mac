# Model Migration Plan & Mapping Document

## 1. Executive Summary

This document outlines the comprehensive plan to migrate from Groq-based implementations to a multi-provider architecture using OpenRouter (Quwen), OpenAI (Whisper), and potential local inference (Medium/Large V3 Turbo). The goal is to ensure high availability, reduced dependency on a single provider, and maintain or improve performance.

## 2. Comprehensive Audit

### 2.1 Current Groq Implementations

| Component | File Path | Usage | Current Model |
|-----------|-----------|-------|---------------|
| **LLM Provider** | `src/infrastructure/ai/groq_llm_provider.py` | Chat completion, Clinical Analysis | `llama-3.3-70b-versatile` |
| **Transcription** | `src/infrastructure/ai/groq_service.py` | Audio file transcription | `whisper-large-v3-turbo` |
| **Real-time** | `src/api/v1/endpoints/realtime.py` | Streaming transcription | Groq Whisper API |
| **Config** | `app/config.py` | Configuration & Feature Flags | `groq_api_key`, `groq_model`, etc. |

### 2.2 Dependencies
- `groq` python package
- `httpx` (configured for IPv4 to bypass Groq IPv6 issues)

## 3. Detailed Mapping Document

### 3.1 Model Mapping

| Current Groq Model | Replacement Model | Provider | Performance Characteristics |
|--------------------|-------------------|----------|-----------------------------|
| `llama-3.3-70b-versatile` | **Quwen (Qwen 2.5 72B)** | OpenRouter / Local | Comparable reasoning, excellent multilingual support, JSON mode support. |
| `llama-3.1-8b-instant` | **Qwen 2.5 7B** | OpenRouter / Local | Fast inference, suitable for query expansion and simple tasks. |
| `whisper-large-v3-turbo` | **Whisper Large V3 Turbo** | OpenAI / Local / RunPod | High accuracy, similar speed if hosted on GPU. |
| `whisper-large-v3-turbo` | **Whisper Medium V3 Turbo** | Local (CPU/Small GPU) | Faster inference, slightly lower accuracy, suitable for resource-constrained environments. |

### 3.2 API Endpoint Changes

#### Transcription (Audio)

**Current (Groq):**
```python
client.audio.transcriptions.create(
    model="whisper-large-v3-turbo",
    file=file_content,
    ...
)
```

**Replacement (OpenAI/Local):**
```python
# OpenAI
client.audio.transcriptions.create(
    model="whisper-1",
    file=file_content,
    ...
)

# Local (Faster-Whisper / CTranslate2)
model = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
segments, info = model.transcribe(audio_file, beam_size=5)
```

#### Chat Completion (LLM)

**Current (Groq):**
```python
client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[...],
    response_format={"type": "json_object"}
)
```

**Replacement (OpenRouter/Quwen):**
```python
client.chat.completions.create(
    model="qwen/qwen2.5-72b-instruct",
    messages=[...],
    # Note: OpenRouter supports response_format for some models, 
    # but prompt engineering might be needed for strict JSON in some cases.
    response_format={"type": "json_object"} 
)
```

## 4. Integration Guides

### 4.1 Quwen Integration
- **Endpoint**: `https://openrouter.ai/api/v1`
- **Auth**: Bearer Token (OpenRouter Key)
- **Model ID**: `qwen/qwen2.5-72b-instruct`
- **Key Considerations**: Ensure system prompts explicitly request JSON if `response_format` is not fully supported by the provider's gateway for this specific model.

### 4.2 Whisper (Medium/Large V3 Turbo) Integration
- **Option A (OpenAI)**: Use standard OpenAI SDK. Model `whisper-1`.
- **Option B (Local)**: Use `faster-whisper` library.
    - Install: `pip install faster-whisper`
    - Code:
      ```python
      from faster_whisper import WhisperModel
      model = WhisperModel("large-v3", device="auto")
      ```

## 5. Technical Implementation Plan

1.  **Abstraction Layer**:
    - Enhance `LLMProvider` interface.
    - Create `TranscriptionProvider` interface (if not fully utilized).
    - Implement `OpenRouterLLMProvider` (already started).
    - Implement `LocalWhisperProvider`.

2.  **Feature Flags (`app/config.py`)**:
    - `ENABLE_GROQ`: Toggle legacy Groq support.
    - `ENABLE_LOCAL_WHISPER`: Toggle local inference.
    - `WHISPER_MODEL_SIZE`: "medium" or "large-v3-turbo".

3.  **Testing**:
    - Create unit tests for `OpenRouterLLMProvider`.
    - Create integration tests verifying fallback logic.

4.  **Deployment**:
    - Blue/Green deployment to switch traffic from Groq services to new services.
