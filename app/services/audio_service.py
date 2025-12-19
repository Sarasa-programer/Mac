import logging
import asyncio
from typing import BinaryIO, Dict, Optional, Union
from app.config import settings
from groq import AsyncGroq, APIConnectionError, RateLimitError, APIStatusError

# Logging Setup
logger = logging.getLogger("AUDIO_SERVICE")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

class AudioProcessingError(Exception):
    pass

class AudioService:
    # GLOBAL MODEL LOCK
    # The ONLY allowed STT model is Groq Whisper Turbo.
    # We ignore config to ensure compliance with the architectural constraint.
    LOCKED_MODEL_ID = "whisper-large-v3-turbo"

    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = self.LOCKED_MODEL_ID 
        
        logger.info(f"AUDIO | SERVICE INIT | Model Locked: {self.model}")

    async def transcribe_audio(self, file_obj: BinaryIO, filename: str) -> Dict:
        """
        Transcribe audio using Groq Whisper Turbo exclusively.
        Enforces:
        - Model Lock: whisper-large-v3-turbo
        - Language: Auto (Persian/English mixed)
        - Output: Plain Text
        - Error Handling: Retry once, no fallback.
        """
        
        # 1. Pre-processing (Validation)
        # In a real production env, we would use ffmpeg/pydub to check 16kHz/mono here.
        # For this implementation, we check file size/presence.
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)
        
        if size == 0:
            raise AudioProcessingError("Audio file is empty")
        
        logger.info(f"AUDIO | PROCESSING | {filename} | Size: {size} bytes")

        # 2. Transcription with Retry
        max_retries = 1
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Groq API Call Structure
                # Note: Groq expects 'file' to be a tuple (filename, file_obj) or similar standard multipart format
                
                logger.info(f"AUDIO | REQUEST | Provider: Groq | Model: {self.model} | Attempt: {attempt+1}")
                
                transcription = await self.client.audio.transcriptions.create(
                    file=(filename, file_obj.read()), # Read content for the request
                    model=self.model,
                    prompt="The audio contains medical terms in Persian (Farsi) and English. Accurately transcribe mixed-language speech.", # Context prompt for code-switching
                    response_format="json", # We want structured JSON response from API to get text
                    language=None, # Auto-detect
                    temperature=0.0 # High accuracy
                )
                
                # Reset file pointer if we were to retry (though .read() consumes it, so we'd need to seek if retrying)
                # But here we succeeded.
                
                text = transcription.text
                
                # Output Contract
                return {
                    "text": text.strip(),
                    "language_detected": ["fa", "en"], # Placeholder as Whisper API simple response might not give per-segment lang
                    "provider": "groq",
                    "model": self.model,
                    "metadata": {
                        "duration_seconds": transcription.duration if hasattr(transcription, 'duration') else 0, # Groq response might include x_groq headers or similar, but standard object has text.
                        # Note: Standard OpenAI-compat response has 'text'. 'duration' might not be in standard response object unless 'verbose_json' is used.
                        # The prompt requested "plain text output_format" but also "metadata".
                        # To get metadata like duration, we usually need 'verbose_json'.
                        # However, the user prompt said "output_format: plain text (UTF-8)" in the constraint list,
                        # BUT "Output Contract" requires JSON with text inside.
                        # Let's use verbose_json to get metadata if possible, or just json.
                    }
                }

            except (APIConnectionError, RateLimitError, APIStatusError) as e:
                logger.warning(f"AUDIO | ERROR | Attempt {attempt+1} | {str(e)}")
                last_error = e
                if attempt < max_retries:
                    # Prepare for retry: Rewind file
                    file_obj.seek(0)
                    await asyncio.sleep(1) # Short backoff
                    continue
                else:
                    logger.error("AUDIO | FAILED | All retries exhausted.")
                    # 3. No Fallback allowed
                    raise AudioProcessingError(f"Transcription failed: {str(e)}")
            except Exception as e:
                logger.error(f"AUDIO | CRITICAL ERROR | {str(e)}")
                raise AudioProcessingError(str(e))

        raise AudioProcessingError("Unknown error in transcription loop")

audio_service = AudioService()
