# Architecture Overview

Project: Pediatric Morning Report AI

## Clean Architecture Layers
- Controllers (FastAPI Endpoints): `src/api/v1/endpoints/*.py`
- Services: `src/infrastructure/ai/*.py` (AI Providers), `app/services/*.py` (Application Logic)
- Core: `src/core/*` (config, security, interfaces)
- Repositories/Data Access: `src/infrastructure/db/session.py`, `src/core/domain/*.py`
- Schemas: `src/api/schemas/*.py` (Pydantic models)

## Data Flow
- Client → FastAPI Endpoint → AI Service (via Provider Factory) → External API (OpenRouter/OpenAI) or Local Model → Response
- **Multi-Provider Strategy**:
    - **LLM**: Primary: OpenRouter (Qwen); Fallback: OpenAI; Legacy: Groq.
    - **Transcription**: Primary: OpenAI (Whisper); Option: Local Whisper (Medium/Large V3 Turbo).

## External Integrations
- **OpenRouter**: Access to Qwen 2.5 models.
- **OpenAI**: GPT-4o and Whisper API.
- **Local Inference**: Faster-Whisper for local transcription.
- **Redis**: Cache analysis results.
- **PubMed**: Article search helper.

## Security & Validation
- JWT Auth via `python-jose`, `passlib`.
- Role-based access.
- Input validation through Pydantic schemas.

## Design Rationale
- **Factory Pattern**: `LLMProviderFactory` and `TranscriptionProviderFactory` allow switching providers without changing business logic.
- **Feature Flags**: Enable/Disable providers via environment variables for gradual migration.
- **FastAPI**: Speed and type safety.

## Scalability Considerations
- Horizontal scaling behind a gateway.
- Background workers for long-running analyses (especially for local inference).

## Diagram (Mermaid)
```mermaid
flowchart LR
  Client -->|HTTP| Endpoints
  Endpoints --> Factory[Provider Factory]
  Factory -->|Primary| OpenRouter[OpenRouter (Qwen)]
  Factory -->|Fallback| OpenAI[OpenAI (GPT/Whisper)]
  Factory -->|Local| Local[Local Whisper]
  Factory -->|Legacy| Groq[Groq]
  Endpoints --> Redis
  Endpoints --> DB[(Database)]
```
