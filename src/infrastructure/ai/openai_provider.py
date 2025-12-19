import os
import openai
from src.core.interfaces.transcription_provider import TranscriptionProvider
from src.config.settings import settings

class OpenAITranscriptionProvider(TranscriptionProvider):
    """
    OpenAI implementation of TranscriptionProvider using Whisper.
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
             print("⚠️ OPENAI_API_KEY not found.")
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        self.model = "whisper-1"

    async def transcribe(self, file_path: str, language: str = "fa") -> str:
        print(f"🎙️ OpenAI Transcription ({self.model})...")
        try:
            with open(file_path, "rb") as file:
                transcription = await self.client.audio.transcriptions.create(
                    file=file,
                    model=self.model,
                    language=language
                )
            return transcription.text
        except Exception as e:
            print(f"❌ OpenAI Transcription Failed: {e}")
            raise e
