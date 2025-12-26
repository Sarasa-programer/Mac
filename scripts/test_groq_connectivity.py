import asyncio
import logging
import time
import sys
import os
import struct
import wave
import json
from typing import Optional

# Add project root to path
sys.path.append(os.getcwd())

try:
    from src.infrastructure.ai.groq_service import GroqService
    from src.config.settings import settings
    from groq import AsyncGroq, APIConnectionError, RateLimitError, APIStatusError
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you are running this script from the project root.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GroqTest")

def create_dummy_wav(filename: str, duration_sec: float = 1.0):
    """Creates a dummy WAV file for testing."""
    sample_rate = 16000
    num_channels = 1
    sample_width = 2  # 16-bit
    num_samples = int(sample_rate * duration_sec)
    
    # Generate silence
    data = b'\x00' * (num_samples * num_channels * sample_width)
    
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(data)
    
    return filename

import httpx

async def test_direct_client_connection():
    """Tests direct connection using AsyncGroq client."""
    logger.info("--- Testing Direct Client Connection ---")
    start_time = time.time()
    
    api_key = settings.GROQ_API_KEY
    if not api_key:
        logger.error("GROQ_API_KEY is not set in settings.")
        # Try to load from env var directly as fallback
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
             logger.error("GROQ_API_KEY is not set in environment variables either.")
             return False
        else:
             logger.info("Loaded GROQ_API_KEY from environment variables.")
    else:
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        logger.info(f"GROQ_API_KEY loaded from settings: {masked_key}")

    # Use robust transport
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=0)
    http_client = httpx.AsyncClient(transport=transport, timeout=30.0)

    client = AsyncGroq(api_key=api_key, http_client=http_client)
    
    try:
        # Simple chat completion
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Hello, are you online?",
                }
            ],
            model="llama-3.3-70b-versatile", # Use a valid model
        )
        latency = time.time() - start_time
        logger.info(f"Direct connection successful. Latency: {latency:.4f}s")
        logger.info(f"Response: {chat_completion.choices[0].message.content}")
        return True
    except APIConnectionError as e:
        logger.error(f"Connection error: {e}")
        logger.error("Check your internet connection and DNS settings.")
        return False
    except RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        return False
    except APIStatusError as e:
        logger.error(f"API status error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

async def test_groq_service_chat():
    """Tests GroqService chat functionality."""
    logger.info("--- Testing GroqService Chat ---")
    service = GroqService()
    start_time = time.time()
    
    try:
        messages = [{"role": "user", "content": "Say 'Test Successful' if you can hear me."}]
        response = await service.chat(messages, model="llama-3.3-70b-versatile")
        latency = time.time() - start_time
        
        if response:
            logger.info(f"Service chat successful. Latency: {latency:.4f}s")
            logger.info(f"Response: {response}")
            return True
        else:
            logger.error("Service returned empty response.")
            return False
    except Exception as e:
        logger.error(f"Service chat failed: {e}")
        return False

async def test_groq_service_transcription():
    """Tests GroqService transcription functionality."""
    logger.info("--- Testing GroqService Transcription ---")
    service = GroqService()
    
    # Create dummy audio
    filename = "test_audio.wav"
    create_dummy_wav(filename)
    
    try:
        # Test file transcription
        start_time = time.time()
        logger.info("Testing transcribe_file...")
        # We need a prompt to guide it even for silence, or it might hallucinate
        transcript = await service.transcribe_file(filename, prompt="This is a test.")
        latency = time.time() - start_time
        logger.info(f"File transcription completed. Latency: {latency:.4f}s")
        logger.info(f"Transcript: {transcript}")
        
        # Test bytes transcription
        with open(filename, "rb") as f:
            # Skip header for raw PCM test if needed, but service.transcribe expects raw bytes and adds header
            # The service.transcribe method takes raw PCM bytes.
            # So we should read the file and strip the header if we want to test 'transcribe' method correctly
            # OR we just pass the bytes. Let's see how service.transcribe works.
            # It calls _create_wav_header and prepends it. So it expects RAW PCM.
            # We created a WAV file. Let's read just the data part.
            f.seek(44) # Skip 44 byte header
            audio_bytes = f.read()
            
        start_time = time.time()
        logger.info("Testing transcribe (bytes)...")
        transcript_bytes = await service.transcribe(audio_bytes, prompt="Testing bytes.")
        latency = time.time() - start_time
        logger.info(f"Bytes transcription completed. Latency: {latency:.4f}s")
        logger.info(f"Transcript: {transcript_bytes}")
        
        return True
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return False
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def main():
    logger.info("Starting Groq Connectivity Tests...")
    
    # 1. Direct Connection Test
    if not await test_direct_client_connection():
        logger.error("Direct connection failed. Aborting further tests.")
        return

    # 2. Service Chat Test
    if not await test_groq_service_chat():
        logger.error("Service chat test failed.")
    
    # 3. Service Transcription Test
    if not await test_groq_service_transcription():
        logger.error("Service transcription test failed.")

    logger.info("Tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
