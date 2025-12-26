import os
import logging
from src.core.interfaces.transcription_provider import TranscriptionProvider
from src.config.settings import settings

logger = logging.getLogger(__name__)

class LocalWhisperProvider(TranscriptionProvider):
    """
    Local implementation of TranscriptionProvider using faster-whisper.
    Supports Medium V3 Turbo and Large V3 Turbo models.
    """
    
    def __init__(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.error("❌ faster-whisper not installed. Please run `pip install faster-whisper`.")
            raise ImportError("faster-whisper is required for LocalWhisperProvider")

        self.model_size = settings.WHISPER_MODEL_SIZE
        self.device = settings.WHISPER_DEVICE
        self.compute_type = settings.WHISPER_COMPUTE_TYPE
        
        logger.info(f"Loading Local Whisper Model: {self.model_size} on {self.device}...")
        try:
            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type
            )
            logger.info("✅ Local Whisper Model loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load Local Whisper Model: {e}")
            raise e

    async def transcribe(self, file_path: str, language: str = "fa") -> str:
        """
        Transcribe audio file using local Whisper model.
        """
        logger.info(f"🎙️ Local Transcription ({self.model_size})...")
        try:
            # faster-whisper's transcribe is synchronous (blocking)
            # For a proper async implementation, we should run this in a thread executor
            # However, for simplicity here (and since it's a compute bound task), we'll call it directly
            # or wrap it if needed. Given the interface is async, we should technically not block the event loop.
            
            import asyncio
            from functools import partial
            
            loop = asyncio.get_event_loop()
            
            # segments is a generator, we need to iterate over it to get text
            # run_in_executor might need a wrapper function
            
            def _run_transcribe():
                segments, info = self.model.transcribe(
                    file_path, 
                    language=language,
                    beam_size=5
                )
                return " ".join([segment.text for segment in segments])

            result = await loop.run_in_executor(None, _run_transcribe)
            return result.strip()
            
        except Exception as e:
            logger.error(f"❌ Local Transcription Failed: {e}")
            raise e
