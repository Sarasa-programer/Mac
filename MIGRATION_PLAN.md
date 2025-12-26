# Model Migration Plan: Groq to Independent Models

## Executive Summary

This document outlines the comprehensive migration strategy from Groq-based models to independent model providers (Medium V3 Turbo/Large V3 Turbo/Whisper/Quwen).

**Current Version**: v1.0-groq-baseline  
**Target Branch**: independent  
**Migration Status**: In Progress

---

## 1. Model Mapping Document

### 1.1 Speech-to-Text (STT) Migration

| Current Groq Model | Replacement Model | Provider | API Changes Required | Performance Characteristics |
|-------------------|-------------------|----------|---------------------|---------------------------|
| `whisper-large-v3-turbo` (via Groq) | `whisper-large-v3` | OpenAI/Open-source Whisper | Change from Groq audio API to OpenAI audio API or local Whisper | Similar latency, potentially better accuracy with OpenAI |
| `whisper-large-v3-turbo` (real-time) | `whisper-large-v3` | OpenAI/Open-source Whisper | Streaming transcription API | Real-time transcription with chunk-based processing |

**Implementation Notes**:
- OpenAI Whisper API: Direct API replacement, minimal code changes
- Open-source Whisper: Requires local deployment, GPU resources
- Maintain backward compatibility with existing audio format expectations

### 1.2 Large Language Model (LLM) Migration

| Current Groq Model | Replacement Model | Provider | API Changes Required | Performance Characteristics |
|-------------------|-------------------|----------|---------------------|---------------------------|
| `llama-3.3-70b-versatile` (main) | `qwen2.5-72b-instruct` | OpenRouter (Free tier) / Local Qwen | Change from Groq chat API to OpenRouter or local inference | Similar capability, potentially faster response times |
| `llama-3.1-8b-instant` (fast/query expansion) | `qwen2.5-7b-instruct` | OpenRouter (Free tier) / Local Qwen | Change from Groq chat API | Faster for simple tasks, similar accuracy |
| `llama-3.3-70b-versatile` (analysis) | `qwen2.5-72b-instruct` | OpenRouter / Local | JSON mode compatibility required | Maintains JSON response format capability |

**Implementation Notes**:
- OpenRouter provides Qwen models on free tier
- Maintain JSON mode for structured outputs
- Ensure system/user message format compatibility
- Temperature settings should remain configurable

### 1.3 Use Case Mapping

#### Use Case 1: Audio Transcription
- **Current**: `GroqService.transcribe()` → Groq Whisper API
- **Target**: `OpenAIService.transcribe()` OR `LocalWhisperService.transcribe()`
- **Files Affected**:
  - `src/infrastructure/ai/groq_service.py`
  - `persian_stt/app/services/groq_service.py`
  - `src/infrastructure/ai/groq_provider.py`
  - `src/core/use_cases/analyze_case.py`

#### Use Case 2: Clinical Case Analysis
- **Current**: `GroqService.analyze_case_comprehensive()` → Llama 3.3 70B
- **Target**: `QwenService.analyze_case_comprehensive()` → Qwen 2.5 72B
- **Files Affected**:
  - `src/infrastructure/ai/groq_service.py`
  - `src/core/use_cases/analyze_case.py`
  - `app/services/llm_service.py`

#### Use Case 3: Query Expansion (PubMed)
- **Current**: `UnifiedLLMService._expand_query()` → Llama 3.1 8B
- **Target**: `UnifiedLLMService._expand_query()` → Qwen 2.5 7B
- **Files Affected**:
  - `app/services/llm_service.py`

#### Use Case 4: Real-time Streaming Transcription
- **Current**: `GroqService.transcribe()` in chunks → Groq Whisper
- **Target**: Streaming transcription via OpenAI or local Whisper
- **Files Affected**:
  - `src/infrastructure/ai/groq_service.py`
  - `persian_stt/app/services/groq_service.py`
  - `src/api/v1/endpoints/realtime.py`
  - `persian_stt/app/api/ws/realtime.py`

---

## 2. Required API Endpoint Changes

### 2.1 Transcription Endpoints

**Groq Current Implementation**:
```python
# Groq API
transcription = await self.client.audio.transcriptions.create(
    file=(filename, file_content),
    model=self.model,
    language=self.language,
    temperature=0.0,
    response_format="json"
)
```

**OpenAI Replacement**:
```python
# OpenAI API
transcription = await self.client.audio.transcriptions.create(
    file=open(file_path, "rb"),
    model="whisper-1",
    language=self.language,
    temperature=0.0,
    response_format="json"
)
```

**Local Whisper Replacement**:
```python
# Local Whisper (using openai-whisper library)
import whisper
model = whisper.load_model("large-v3")
result = model.transcribe(file_path, language="fa")
```

### 2.2 Chat Completion Endpoints

**Groq Current Implementation**:
```python
# Groq API
completion = await self.client.chat.completions.create(
    model=target_model,
    messages=messages,
    temperature=0.1,
    response_format={"type": "json_object"}
)
```

**OpenRouter/Qwen Replacement**:
```python
# OpenRouter API
completion = await self.client.chat.completions.create(
    model="qwen/qwen2.5-72b-instruct:free",
    messages=messages,
    temperature=0.1,
    response_format={"type": "json_object"}
)
```

---

## 3. Configuration Management Updates

### 3.1 New Configuration Structure

```python
# Enhanced settings to support multiple providers
class Settings(BaseSettings):
    # Primary Provider Selection
    PRIMARY_PROVIDER: str = "openrouter"  # Options: "groq", "openrouter", "openai", "local"
    
    # OpenAI Configuration (for Whisper)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_WHISPER_MODEL: str = "whisper-1"
    
    # OpenRouter Configuration (for Qwen)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MAIN_MODEL: str = "qwen/qwen2.5-72b-instruct:free"
    OPENROUTER_FAST_MODEL: str = "qwen/qwen2.5-7b-instruct:free"
    
    # Local Model Configuration
    LOCAL_WHISPER_MODEL: str = "large-v3"
    LOCAL_WHISPER_DEVICE: str = "cuda"  # or "cpu"
    LOCAL_QWEN_MODEL_PATH: Optional[str] = None
    LOCAL_QWEN_DEVICE: str = "cuda"
    
    # Fallback Chain
    FALLBACK_PROVIDERS: List[str] = ["openrouter", "openai", "groq"]
    
    # Feature Flags
    ENABLE_GROQ: bool = False  # Gradually disable Groq
    ENABLE_MODEL_ABSTRACTION: bool = True
    ENABLE_FALLBACK: bool = True
```

### 3.2 Environment Variables

```bash
# .env.example updates
PRIMARY_PROVIDER=openrouter
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MAIN_MODEL=qwen/qwen2.5-72b-instruct:free
OPENROUTER_FAST_MODEL=qwen/qwen2.5-7b-instruct:free

# Feature Flags
ENABLE_GROQ=false
ENABLE_MODEL_ABSTRACTION=true
ENABLE_FALLBACK=true
```

---

## 4. Abstraction Layer Architecture

### 4.1 Provider Interface Design

```
AbstractProvider (ABC)
├── TranscriptionProvider (ABC)
│   ├── GroqTranscriptionProvider (deprecated)
│   ├── OpenAITranscriptionProvider (new)
│   └── LocalWhisperProvider (new)
│
└── LLMProvider (ABC)
    ├── GroqLLMProvider (deprecated)
    ├── OpenRouterLLMProvider (new)
    ├── OpenAILLMProvider (new)
    └── LocalQwenProvider (new)
```

### 4.2 Service Router Pattern

A unified service router will handle:
1. Provider selection based on configuration
2. Automatic fallback on failures
3. Feature flag evaluation
4. Model-specific parameter mapping

---

## 5. Testing Strategy

### 5.1 Unit Tests
- Model provider initialization
- API call mocking and validation
- Error handling and retries
- Configuration parsing

### 5.2 Integration Tests
- End-to-end transcription flows
- End-to-end analysis flows
- Provider fallback mechanisms
- Performance benchmarking

### 5.3 A/B Testing Framework
- Side-by-side comparison of Groq vs. new providers
- Performance metrics collection
- Accuracy validation

---

## 6. Deployment Strategy

### 6.1 Blue-Green Deployment
- Deploy independent version alongside current version
- Route traffic gradually using feature flags
- Monitor metrics closely
- Rollback capability maintained

### 6.2 Monitoring Requirements
- Model response times
- Error rates per provider
- Token usage/cost tracking
- Accuracy metrics (if applicable)

### 6.3 Rollback Procedures
- Feature flag toggle to revert to Groq
- Data migration scripts (if needed)
- Communication plan for stakeholders

---

## 7. Timeline and Milestones

1. **Phase 1: Foundation** (Week 1-2)
   - Create abstraction layers
   - Update configuration management
   - Implement new providers (OpenRouter/Qwen, OpenAI/Whisper)

2. **Phase 2: Integration** (Week 3-4)
   - Integrate new providers into existing services
   - Implement fallback mechanisms
   - Update all API endpoints

3. **Phase 3: Testing** (Week 5-6)
   - Comprehensive test suite
   - A/B testing setup
   - Performance benchmarking

4. **Phase 4: Deployment** (Week 7-8)
   - Blue-green deployment
   - Gradual traffic migration
   - Monitoring and optimization

5. **Phase 5: Validation** (Week 9-10)
   - Real-world usage validation
   - Performance analysis
   - Final deprecation of Groq components

---

## 8. Risk Mitigation

### 8.1 Technical Risks
- **API rate limits**: Implement intelligent rate limiting and queuing
- **Cost overruns**: Monitor usage closely, set budgets
- **Performance degradation**: Comprehensive benchmarking before cutover
- **Model availability**: Maintain multiple fallback providers

### 8.2 Operational Risks
- **Deployment issues**: Maintain rollback procedures
- **Data migration**: Test thoroughly in staging
- **User impact**: Gradual migration with feature flags

---

## 9. Success Criteria

- [ ] All Groq dependencies removed from production code
- [ ] New providers demonstrate equal or better performance
- [ ] Zero data loss during migration
- [ ] Cost reduction or maintained cost levels
- [ ] All existing functionality preserved
- [ ] Comprehensive documentation updated
- [ ] Test coverage >80%

---

## 10. Documentation Updates Required

- [ ] API documentation (new endpoints/parameters)
- [ ] Architecture diagrams (updated provider structure)
- [ ] Developer migration guide
- [ ] Operations deployment guide
- [ ] User-facing feature documentation (if applicable)
- [ ] Configuration reference guide

