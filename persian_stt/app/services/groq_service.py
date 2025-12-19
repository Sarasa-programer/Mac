import logging
import asyncio
from typing import Optional
from groq import AsyncGroq
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.language = "fa"
    
    async def transcribe(self, audio_bytes: bytes, prompt: str = "") -> Optional[str]:
        """
        Transcribes audio bytes using Groq Whisper API.
        
        Args:
            audio_bytes: Raw audio data (must be valid audio file format like wav/webm/mp3, 
                        or raw PCM if wrapped in wav container). 
                        Note: Groq API expects file-like object with filename.
            prompt: Previous context to guide the model.
        
        Returns:
            Transcribed text or None if failed.
        """
        try:
            # Groq expects a tuple (filename, file_content) or just bytes if it can sniff.
            # Best practice: wrap in (filename, bytes) tuple.
            # Since we are sending raw PCM wrapped in WAV (handled by caller) or WebM.
            # Let's assume the caller sends valid WAV bytes.
            
            # Using a pseudo-filename to hint format
            file_payload = ("audio.wav", audio_bytes)
            
            transcription = await self.client.audio.transcriptions.create(
                file=file_payload,
                model=self.model,
                prompt=prompt, # Context injection
                language=self.language,
                temperature=0.0, # Deterministic output
                response_format="json"
            )
            
            return transcription.text.strip()
            
        except Exception as e:
            logger.error(f"Groq Transcription Error: {e}")
            return None
