from abc import ABC, abstractmethod
from typing import Optional

class TranscriptionProvider(ABC):
    """
    Abstract Interface for Transcription Providers.
    Enables switching between Groq, OpenAI, and Gemini.
    """
    
    @abstractmethod
    async def transcribe(self, file_path: str, language: str = "fa") -> str:
        """
        Transcribe audio/video file to text.
        
        Args:
            file_path: Path to the audio file on disk.
            language: ISO language code (default 'fa' for Persian).
            
        Returns:
            str: The transcribed text.
        """
        pass
