import logging
import asyncio
import struct
from typing import Optional
from groq import AsyncGroq, APIConnectionError, RateLimitError, APIError, APIStatusError
from src.config.settings import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_random
import httpx

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        # Configure httpx client to force IPv4 by binding to 0.0.0.0
        # This resolves connection issues in environments with broken IPv6 (e.g. some macOS/Docker setups)
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=0)
        http_client = httpx.AsyncClient(transport=transport, timeout=60.0)

        api_key = settings.GROQ_API_KEY
        if not api_key:
            logger.error("❌ GROQ_API_KEY is missing in settings!")
        else:
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
            logger.info(f"GroqService initialized with Key: {masked_key} | Model: {settings.GROQ_AUDIO_MODEL}")

        self.client = AsyncGroq(
            api_key=api_key,
            http_client=http_client,
            max_retries=0 # We handle retries with tenacity
        )
        self.model = settings.GROQ_AUDIO_MODEL
        self.language = "fa"

    def _create_wav_header(self, data_length: int, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
        """Creates a valid WAV header for the given PCM data properties."""
        header = b'RIFF'
        header += struct.pack('<I', 36 + data_length)
        header += b'WAVE'
        
        # fmt chunk
        header += b'fmt '
        header += struct.pack('<I', 16) # Chunk size
        header += struct.pack('<H', 1)  # Audio format (1 = PCM)
        header += struct.pack('<H', channels)
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * channels * bits_per_sample // 8) # Byte rate
        header += struct.pack('<H', channels * bits_per_sample // 8) # Block align
        header += struct.pack('<H', bits_per_sample)
        
        # data chunk
        header += b'data'
        header += struct.pack('<I', data_length)
        
        return header
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout, APIConnectionError, RateLimitError, APIStatusError))
    )
    async def chat(self, messages: list, model: Optional[str] = None, json_mode: bool = False) -> Optional[str]:
        """
        Sends a chat completion request to Groq.
        """
        try:
            target_model = model or settings.GROQ_MODEL
            response_format = {"type": "json_object"} if json_mode else None
            completion = await self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.5,
                response_format=response_format
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq Chat Error: {e}")
            raise e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout, APIConnectionError, RateLimitError, APIStatusError))
    )
    async def transcribe_file(self, file_path: str, prompt: str = "") -> Optional[str]:
        """
        Transcribes an audio file using Groq Whisper API.
        """
        try:
            with open(file_path, "rb") as f:
                # Read file content
                file_content = f.read()
                
            filename = file_path.split("/")[-1]
            
            transcription = await self.client.audio.transcriptions.create(
                file=(filename, file_content),
                model=self.model, # Use self.model which is initialized from settings
                prompt=prompt,
                language=self.language,
                temperature=0.0,
                response_format="json"
            )
            
            return transcription.text.strip()
            
        except Exception as e:
            logger.error(f"Groq File Transcription Error: {e}")
            raise e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout, APIConnectionError, RateLimitError, APIStatusError))
    )
    async def analyze_case_comprehensive(self, transcript: str) -> Optional[dict]:
        """
        Performs comprehensive case analysis (Summary + Clinical Analysis) using Llama 3.3.
        Replaces Gemini and OpenAI functionality.
        """
        system_prompt = """You are a pediatric expert assistant. Analyze the following morning report case transcript.
        Return a valid JSON object with the following structure:
        {
            "title": "string (A suitable title for the case)",
            "summary": {
                "chiefComplaint": "string",
                "history": "string",
                "vitals": "string"
            },
            "differentialDiagnosis": ["string (Diagnosis 1)", "string (Diagnosis 2)", ...],
            "keywords": ["string (Keyword 1)", ...],
            "nelsonContext": "string (Summary of the condition from Nelson Textbook of Pediatrics context)"
        }
        Ensure the JSON is valid and strictly follows this schema.
        """
        
        try:
            completion = await self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                temperature=0.1, # Low temperature for consistent formatting
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content
            import json
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Groq Comprehensive Analysis Error: {e}")
            raise e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout, APIConnectionError, RateLimitError, APIStatusError))
    )
    async def transcribe(self, audio_bytes: bytes, prompt: str = "") -> Optional[str]:
        """
        Transcribes audio bytes using Groq Whisper API.
        
        Args:
            audio_bytes: Raw audio data (PCM 16-bit 16kHz). 
                        We wrap this in a WAV container before sending to Groq.
            prompt: Previous context to guide the model.
        
        Returns:
            Transcribed text or None if failed.
        """
        try:
            # Add WAV header to raw PCM bytes
            wav_header = self._create_wav_header(len(audio_bytes))
            wav_data = wav_header + audio_bytes
            
            # Groq expects a tuple (filename, file_content)
            file_payload = ("audio.wav", wav_data)
            
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
            if hasattr(e, 'status_code'):
                if e.status_code == 403:
                    logger.critical("🛑 403 Forbidden: Check API Key and Model Name. Groq may have blocked the request or the model is deprecated.")
                elif e.status_code == 400:
                    logger.critical("🛑 400 Bad Request: Check Audio Format or Model Name.")
            raise e
