import asyncio
import numpy as np
from typing import Optional, Tuple
from app.core.config import get_settings
from app.services.vad_service import VADService

settings = get_settings()

class BufferManager:
    def __init__(self):
        self.buffer = bytearray()
        self.overlap_buffer = bytearray()
        
        # Audio constants
        self.sample_rate = settings.SAMPLE_RATE
        self.bytes_per_sample = 2  # 16-bit PCM
        self.bytes_per_second = self.sample_rate * self.bytes_per_sample
        
        # Window logic
        self.window_size_bytes = int(settings.WINDOW_DURATION * self.bytes_per_second)
        self.overlap_size_bytes = int(settings.OVERLAP_DURATION * self.bytes_per_second)
        
        # VAD
        self.vad_service = VADService()
        self.last_speech_time = 0
        
    def add_audio(self, chunk: bytes) -> Optional[bytes]:
        """
        Adds audio to buffer. 
        Returns a full window of bytes if ready to process, otherwise None.
        """
        self.buffer.extend(chunk)
        
        # Check if we have enough data for a full window
        if len(self.buffer) >= self.window_size_bytes:
            return self._extract_window()
        
        return None

    def _extract_window(self) -> bytes:
        """
        Extracts the current window + overlap from previous.
        Updates internal state for next slide.
        """
        # 1. Construct the payload: Overlap + Current Buffer (up to window size)
        # Actually, we just take the first WINDOW_SIZE from buffer, 
        # prepended with stored overlap?
        # Strategy: The 'buffer' already accumulates everything.
        
        # Let's take the first window_size_bytes
        current_window = self.buffer[:self.window_size_bytes]
        
        # The payload to return includes the previous overlap
        full_payload = self.overlap_buffer + current_window
        
        # 2. Prepare for next turn:
        # We need to keep the LAST part of this current_window as the next overlap.
        # And remove the consumed part from self.buffer.
        
        # New overlap is the end of the current window
        new_overlap = current_window[-self.overlap_size_bytes:]
        self.overlap_buffer = bytearray(new_overlap)
        
        # Remove the processed part from main buffer
        # We slide forward by (Window - Overlap) effectively?
        # Wait, if we just drop the whole window, we might lose words if we don't overlap.
        # Correct Sliding Window Logic:
        # We consume (Window - Overlap) bytes, leaving the rest.
        
        consume_size = self.window_size_bytes - self.overlap_size_bytes
        self.buffer = self.buffer[consume_size:]
        
        return bytes(full_payload)

    def flush(self) -> Optional[bytes]:
        """
        Force flush the remaining buffer (e.g. on silence or disconnect).
        """
        if not self.buffer:
            return None
            
        full_payload = self.overlap_buffer + self.buffer
        self.buffer.clear()
        self.overlap_buffer.clear() # Reset overlap on flush
        return bytes(full_payload)
