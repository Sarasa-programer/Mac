import os
from google import genai
from google.genai import types
from src.core.interfaces.transcription_provider import TranscriptionProvider
from src.config.settings import settings

class GeminiTranscriptionProvider(TranscriptionProvider):
    """
    Gemini implementation of TranscriptionProvider using Gemini 1.5/2.0 Flash.
    """
    
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        if not self.api_key:
             print("⚠️ GOOGLE_API_KEY not found.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash"

    async def transcribe(self, file_path: str, language: str = "fa") -> str:
        print(f"🎙️ Gemini Transcription ({self.model})...")
        try:
            # Determine mime type
            mime_type = "audio/mp3"
            if file_path.endswith(".mp4") or file_path.endswith(".m4a"):
                mime_type = "audio/mp4"
            elif file_path.endswith(".wav"):
                mime_type = "audio/wav"

            with open(file_path, "rb") as f:
                file_content = f.read()
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                             types.Part.from_text(text=f"Transcribe this audio exactly as spoken in {language} language."),
                             types.Part.from_bytes(data=file_content, mime_type=mime_type)
                        ]
                    )
                ]
            )
            return response.text
        except Exception as e:
            print(f"❌ Gemini Transcription Failed: {e}")
            raise e
