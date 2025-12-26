# Release Notes - Version 1.2

## Overview
**Release Date**: December 26, 2024
**Version**: 1.2.0

Version 1.2 introduces a robust **Multi-Provider Architecture**, enabling seamless switching between Groq, OpenRouter (Qwen), OpenAI, and Local Inference models. This release eliminates vendor lock-in and provides fallback mechanisms for high availability.

## 🚀 New Features

### 1. Multi-Provider Support
- **Factory Pattern Implementation**: New `LLMProviderFactory` and `TranscriptionProviderFactory` abstract the underlying API calls.
- **Provider Options**:
    - **LLM**: Groq (Llama 3), OpenRouter (Qwen 2.5 72B), OpenAI (GPT-4o).
    - **Transcription**: Groq (Whisper V3), OpenAI (Whisper V1), Local (Faster-Whisper).

### 2. Local Inference
- **Local Whisper Support**: Run transcription locally using `faster-whisper`.
- **Privacy & Cost**: Process sensitive audio on-premise without API costs.
- **Configuration**: Toggle via `ENABLE_LOCAL_WHISPER` in `app/config.py`.

### 3. Resilience & Stability
- **Fallback Logic**: Automatic fallback chain (e.g., OpenRouter -> OpenAI -> Groq) if the primary provider fails.
- **Retry Mechanism**: Implemented `tenacity` retry logic for transient network errors.
- **Async Processing**: Improved async handling for non-blocking I/O during transcription and analysis.

### 4. Configuration Management
- **Feature Flags**: Granular control over providers and features (e.g., `ENABLE_GROQ`, `ENABLE_FALLBACK`).
- **Environment Variables**: Simplified `.env` configuration for multiple keys.

## 🛠 Bug Fixes & Improvements
- **Refactoring**: Decoupled service logic from API implementation.
- **Testing**: Added comprehensive unit tests for provider factories and local whisper integration.
- **Documentation**: Updated architecture diagrams and migration guides.

## 📦 Upgrade Guide

### From v1.1
1.  Pull the latest code: `git checkout version-1.2 && git pull`.
2.  Install new dependencies:
    ```bash
    pip install faster-whisper openai tenacity
    ```
3.  Update `.env` with new keys:
    ```bash
    OPENROUTER_API_KEY=sk-or-...
    OPENAI_API_KEY=sk-...
    PRIMARY_PROVIDER=openrouter
    ```

## ⚠️ Known Issues
- Local Whisper requires FFmpeg installed on the system.
- Initial download of local models (e.g., `large-v3-turbo`) may take time depending on internet speed.
