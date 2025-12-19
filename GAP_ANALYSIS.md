# 🎯 PedsMorningAI - Technical Gap Analysis & Migration Plan

## 1. Executive Summary
The current codebase is a functional FastAPI application using a Layered Architecture (`api` -> `services` -> `db`). The target state is a **Clean Architecture** (Core/Domain/Infrastructure) with specific endpoints and strict separation of concerns for AI providers.

## 2. Architectural Gaps

| Feature | Current State (`backend/app`) | Desired State (`src`) | Priority |
| :--- | :--- | :--- | :--- |
| **Folder Structure** | Layered (`api`, `services`, `core`, `db`) | Clean (`core`, `infrastructure`, `api`) | 🔴 Critical |
| **Dependency Rule** | Services import implementation details directly | Core defines interfaces; Infra implements them | 🔴 Critical |
| **AI Routing** | `ai_router.py` manages providers directly | `TranscriptionProvider` interface + Strategy Pattern | 🟠 High |
| **Endpoints** | `/cases/upload`, `/cases/{id}/analyze` | `/audio/transcribe`, `/audio/analyze` | 🟠 High |
| **Async Processing** | Synchronous/Await calls in request scope | Async jobs with status tracking (`/jobs/{id}`) | 🟡 Medium |
| **Language** | English comments | Bilingual (Persian/English) comments | 🟢 Low |

## 3. Detailed Technical Assessment

### 3.1 Folder Structure & Modularization
**Current:**
- `app.services` mixes business logic with external API calls.
- `app.core.config` is hardcoded in the application layer.

**Recommendation:**
- Move `models` to `src/core/domain`.
- Move `schemas` to `src/api/schemas`.
- Move `services/*` to `src/infrastructure/ai/`.
- Create `src/core/interfaces/` for `TranscriptionProvider`.

### 3.2 AI Implementation
**Current:**
- `ai_router.py` has hardcoded fallback chains (`openai` -> `gemini`).
- No formal interface for providers.

**Recommendation:**
- Define `class TranscriptionProvider(ABC):` in `src/core/interfaces`.
- Implement `GroqProvider`, `OpenAIProvider`, `GeminiProvider` in `src/infrastructure/ai`.
- Use `AI_PROVIDER` env var to inject the correct implementation at runtime.

### 3.3 API Design
**Current:**
- File upload creates a database entry immediately (`Case` model).
- Analysis is tied to a `Case` ID.

**Recommendation:**
- Implement `/audio/transcribe` as a stateless or job-based endpoint.
- Decouple audio processing from Case management (allow transcribing without creating a full case first).

## 4. Migration Roadmap

### Phase 1: Structural Refactoring (Immediate)
1.  Stop running services.
2.  Create `src/` directory structure.
3.  Migrate files to Clean Architecture locations.
4.  Update all import paths (`app.*` -> `src.*`).

### Phase 2: Interface Implementation
1.  Define `TranscriptionProvider`.
2.  Refactor `groq_service.py` et al. to implement this interface.
3.  Update Dependency Injection in `main.py`.

### Phase 3: Endpoint Updates
1.  Create `src/api/v1/endpoints/audio.py`.
2.  Implement required `/audio/*` routes.
3.  Update frontend API client (later).

## 5. Next Steps
Proceeding immediately with **Phase 1: Structural Refactoring**.
