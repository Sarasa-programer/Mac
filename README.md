# Clinical Voice Assistant

## Current Status

🚀 **Migration in Progress**: Moving from Groq to independent providers

- **Current Version**: v1.0-groq-baseline (stable)
- **Development Branch**: independent (migration work)
- **Migration Status**: Foundation complete, integration in progress

## Stack

### Current (v1.0-groq-baseline)
- STT: Groq Whisper Turbo
- LLM: Llama-3.3-70B via Groq
- Backend: FastAPI
- RAG: PubMed
- Language: Persian (fa-IR)

### Target (independent branch)
- STT: OpenAI Whisper (or local Whisper)
- LLM: Qwen 2.5 72B via OpenRouter (free tier)
- Backend: FastAPI
- RAG: PubMed
- Language: Persian (fa-IR)

## Migration

See [MIGRATION_SUMMARY.md](./MIGRATION_SUMMARY.md) for current status and [docs/MIGRATION_GUIDE.md](./docs/MIGRATION_GUIDE.md) for detailed migration instructions.

## Notes
- `.env` is required (not included)
- Audio processing is file-based
