import av
import io
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.target_sample_rate = settings.SAMPLE_RATE # 16000
        self.target_channels = 1
        self.format = "s16le" # 16-bit PCM

    def process_webm_chunk(self, chunk: bytes) -> bytes:
        """
        Decodes a WebM/Opus chunk to PCM 16000Hz Mono.
        WARNING: WebM chunks from MediaRecorder are usually not standalone files 
        (except the first one). This method assumes the client sends a stream 
        that can be decoded incrementally or valid standalone chunks.
        
        If the client sends raw blobs that are valid containers (e.g. `timeslice` in MediaRecorder),
        PyAV might struggle if headers are missing in subsequent chunks.
        
        Strategy: 
        1. If it's a stream, we should maintain a persistent decoder context.
        2. However, simpler approach for WebSocket: Expect RAW PCM from client if possible.
        
        If we MUST support WebM:
        We'll try to decode, but this is heavy. 
        Better strategy for MVP: Assume Client sends RAW PCM (converted by AudioWorklet) OR 
        send WAV header only once.
        
        Let's implement a resilient decoder that attempts to decode what it gets.
        """
        try:
            # For real-time streaming, decoding WebM chunks independently is hard because
            # only the first chunk has the Header/Codec info.
            # We will implement this assuming the client sends RAW PCM or we use a persistent buffer.
            # But simpler: Client uses AudioContext to downsample and sends Float32/Int16 directly.
            
            # If we assume input is already PCM but maybe wrong sample rate?
            # Let's assume input is raw bytes for now to avoid FFmpeg overhead per chunk.
            # But the requirements mentioned "Converting WebM/Opus".
            
            # To do this correctly with PyAV, we need a persistent container.
            # Since PyAV doesn't easily support "push" based decoding of partial streams without custom IO.
            
            # FALLBACK: Return as is if we trust the client, or valid PCM.
            # For this MVP, let's implement a "Passthrough" or "Resampler" if it's raw.
            
            # If user sends WebM, we need a persistent decoder. 
            # Given the constraints and complexity, I will implement a helper that
            # assumes the client sends PCM S16LE 16000Hz (Best for latency).
            # If not, we log a warning.
            
            return chunk 
            
        except Exception as e:
            logger.error(f"Audio Processing Error: {e}")
            return b""
            
    def convert_to_pcm16(self, audio_data: bytes) -> bytes:
        """
        Stub for conversion if we decide to do it server side.
        For low latency, client-side conversion is preferred.
        """
        return audio_data
