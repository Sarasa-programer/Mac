# Real-time Persian Speech-to-Text (STT) Pipeline

Production-grade real-time transcription using FastAPI, WebSockets, and Groq Whisper API.

## Features
- **Real-time Streaming**: WebSocket-based audio streaming.
- **Persian Language Support**: Optimized for `fa` language using Whisper-Large-V3.
- **Sliding Window Buffer**: Handles stateless API constraints with overlap to prevent word cutting.
- **VAD Integration**: Voice Activity Detection to minimize latency and API calls.

## Architecture
- **Backend**: FastAPI
- **Audio Processing**: PyAV (In-memory resampling), Numpy
- **AI Model**: Groq API (Whisper)

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables (create `.env`):
   ```
   GROQ_API_KEY=your_key_here
   ```
3. Run server:
   ```bash
   uvicorn app.main:app --reload
   ```
