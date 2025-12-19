# Clinical Voice Assistant (Groq-based)

⚠️ Current version uses Groq (Whisper Turbo + Llama 3.3)

## Current Stack
- STT: Groq Whisper Turbo
- LLM: Llama-3.3-70B via Groq
- Backend: FastAPI
- RAG: PubMed
- Language: Persian (fa-IR)

## Status
This repository captures the **baseline working version**.
Next steps will migrate away from Groq toward open-source / free solutions.

## Notes
- `.env` is required (not included)
- Audio processing is file-based
