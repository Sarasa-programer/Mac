import os
from typing import Optional
from src.core.interfaces.transcription_provider import TranscriptionProvider
from src.infrastructure.ai.groq_provider import GroqTranscriptionProvider
from src.infrastructure.ai.openai_provider import OpenAITranscriptionProvider
from src.infrastructure.ai.gemini_provider import GeminiTranscriptionProvider

class TranscriptionProviderFactory:
    """
    Factory to create TranscriptionProvider instances.
    """
    
    @staticmethod
    def get_provider(provider_name: Optional[str] = None) -> TranscriptionProvider:
        """
        Get a transcription provider instance.
        
        Args:
            provider_name: 'groq', 'openai', or 'gemini'. 
                           If None, uses AI_PROVIDER env var.
        """
        if not provider_name:
            provider_name = os.getenv("AI_PROVIDER", "groq")
            
        provider_name = provider_name.lower()
        
        if provider_name == "groq":
            return GroqTranscriptionProvider()
        elif provider_name == "openai":
            return OpenAITranscriptionProvider()
        elif provider_name == "gemini":
            return GeminiTranscriptionProvider()
        else:
            # Fallback or error
            print(f"⚠️ Unknown provider '{provider_name}', defaulting to Groq")
            return GroqTranscriptionProvider()
