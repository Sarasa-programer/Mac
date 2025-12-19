import os
from groq import AsyncGroq
from src.core.interfaces.transcription_provider import TranscriptionProvider
from src.config.settings import settings

class GroqTranscriptionProvider(TranscriptionProvider):
    """
    Groq implementation of TranscriptionProvider using Whisper-large-v3.
    """
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key:
            print("⚠️ GROQ_API_KEY not found. Groq provider may fail.")
        self.client = AsyncGroq(api_key=self.api_key)
        self.model = settings.GROQ_AUDIO_MODEL # Best for Persian

    async def transcribe(self, file_path: str, language: str = "fa") -> str:
        print(f"🎙️ Groq Transcription ({self.model})...")
        try:
            with open(file_path, "rb") as file:
                # Read file content asynchronously or just read it (file io is blocking anyway usually unless using aiofiles, but acceptable for small files or if threadpool used)
                # For simplicity and since AsyncGroq expects file content or tuple, we read it.
                content = file.read()
                
            transcription = await self.client.audio.transcriptions.create(
                file=(os.path.basename(file_path), content),
                model=self.model,
                language=language,
                response_format="verbose_json",
                temperature=0.0
            )
            return transcription.text
        except Exception as e:
            print(f"❌ Groq Transcription Failed: {e}")
            if hasattr(e, 'status_code') and e.status_code == 401:
                 raise Exception("Authentication failed: Invalid GROQ_API_KEY.")
            raise e
