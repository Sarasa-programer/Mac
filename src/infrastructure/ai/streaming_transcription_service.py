"""
Streaming transcription service for real-time audio processing.
Handles bytes-based transcription (as opposed to file-based).
"""
import logging
import io
import struct
from typing import Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)


class StreamingTranscriptionService:
    """
    Service for transcribing audio bytes in real-time.
    Uses configuration to select the appropriate provider.
    """
    
    def __init__(self):
        self.provider = getattr(settings, 'PRIMARY_STT_PROVIDER', 'groq').lower()
        self.fallback_to_groq = False
        
        # For bytes-based transcription, we use the service directly
        # since TranscriptionProvider interface uses file paths
        if self.provider == 'groq':
            from src.infrastructure.ai.groq_service import GroqService
            self.service = GroqService()
        elif self.provider == 'openai':
            # OpenAI Whisper can handle bytes via file-like objects
            self.service = None  # Will be initialized on first use
            self._init_openai_service()
            # If OpenAI init failed, fallback_to_groq will be True
        else:
            logger.warning(f"Unknown provider '{self.provider}', defaulting to Groq")
            from src.infrastructure.ai.groq_service import GroqService
            self.service = GroqService()
            self.provider = 'groq'
    
    def _init_openai_service(self):
        """Initialize OpenAI service for streaming transcription."""
        try:
            import openai
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                logger.warning("OPENAI_API_KEY not found, falling back to Groq")
                from src.infrastructure.ai.groq_service import GroqService
                self.service = GroqService()
                self.provider = 'groq'
                self.fallback_to_groq = True
                return
            
            self.service = openai.AsyncOpenAI(api_key=api_key)
            logger.info(f"StreamingTranscriptionService using OpenAI Whisper")
        except ImportError:
            logger.error("openai package not installed, falling back to Groq")
            from src.infrastructure.ai.groq_service import GroqService
            self.service = GroqService()
            self.provider = 'groq'
            self.fallback_to_groq = True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {e}, falling back to Groq")
            from src.infrastructure.ai.groq_service import GroqService
            self.service = GroqService()
            self.provider = 'groq'
            self.fallback_to_groq = True
    
    def _create_wav_from_pcm(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
        """
        Create a valid WAV file from raw PCM data.
        Same logic as GroqService._create_wav_header but returns complete WAV file.
        """
        data_length = len(pcm_data)
        header = b'RIFF'
        header += struct.pack('<I', 36 + data_length)
        header += b'WAVE'
        
        # fmt chunk
        header += b'fmt '
        header += struct.pack('<I', 16)  # Chunk size
        header += struct.pack('<H', 1)   # Audio format (1 = PCM)
        header += struct.pack('<H', channels)
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * channels * bits_per_sample // 8)  # Byte rate
        header += struct.pack('<H', channels * bits_per_sample // 8)  # Block align
        header += struct.pack('<H', bits_per_sample)
        
        # data chunk
        header += b'data'
        header += struct.pack('<I', data_length)
        
        return header + pcm_data
    
    async def transcribe(self, audio_bytes: bytes, prompt: str = "", language: str = "fa") -> Optional[str]:
        """
        Transcribe audio bytes.
        
        Args:
            audio_bytes: Raw audio data (PCM 16-bit 16kHz for Groq, or WAV/MP3 for OpenAI)
            prompt: Previous context to guide the model
            language: ISO language code
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            # If we fell back to Groq during init, use Groq
            if self.fallback_to_groq or self.provider == 'groq':
                # GroqService.transcribe() handles bytes directly
                return await self.service.transcribe(audio_bytes, prompt=prompt)
            
            elif self.provider == 'openai':
                # OpenAI requires a file-like object
                # For PCM bytes, we need to wrap them in a WAV header
                wav_data = self._create_wav_from_pcm(audio_bytes)
                
                # Use BytesIO as a file-like object
                # OpenAI async API accepts tuple format: (filename, file_object_or_bytes, content_type)
                audio_file_obj = io.BytesIO(wav_data)
                
                # Pass as tuple with BytesIO (OpenAI SDK will read from it)
                transcription = await self.service.audio.transcriptions.create(
                    file=("audio.wav", audio_file_obj, "audio/wav"),
                    model="whisper-1",
                    language=language if language != "fa" else None,  # OpenAI may not support Persian, let it auto-detect
                    prompt=prompt if prompt else None,
                    temperature=0.0,
                    response_format="json"
                )
                return transcription.text.strip() if transcription.text else None
            
            else:
                logger.error(f"Unsupported provider for streaming: {self.provider}")
                return None
                
        except Exception as e:
            logger.error(f"Streaming transcription error ({self.provider}): {e}")
            raise e

