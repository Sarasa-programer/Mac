import asyncio
import numpy as np
from typing import Optional, Tuple
from src.config.settings import settings
from src.infrastructure.ai.vad_service import VADService

class BufferManager:
    def __init__(self):
        # Memory Optimization: Use predefined capacity to avoid resizing
        self.sample_rate = settings.SAMPLE_RATE
        self.bytes_per_sample = 2
        self.bytes_per_second = self.sample_rate * self.bytes_per_sample
        
        # Max buffer size: 30 seconds
        self.max_buffer_size = 30 * self.bytes_per_second
        self.buffer = bytearray()
        
        self.window_size_bytes = int(settings.WINDOW_DURATION * self.bytes_per_second)
        self.overlap_size_bytes = int(settings.OVERLAP_DURATION * self.bytes_per_second)
        
        self.vad_service = VADService()
        self.overlap_buffer = bytearray()

    def add_audio(self, chunk: bytes) -> Optional[bytes]:
        """
        Adds audio to buffer. 
        Returns a full window of bytes if ready to process, otherwise None.
        """
        # Safety check for memory leak
        if len(self.buffer) + len(chunk) > self.max_buffer_size:
            # Drop oldest data if overflow (circular buffer behavior simulation)
            overflow = (len(self.buffer) + len(chunk)) - self.max_buffer_size
            self.buffer = self.buffer[overflow:]
            
        self.buffer.extend(chunk)
        
        # Check if we have enough data for a full window
        if len(self.buffer) >= self.window_size_bytes:
            return self._extract_window()
        
        return None

    def _extract_window(self) -> bytes:
        """
        Extracts the current window + overlap from previous.
        Uses memoryview for zero-copy slicing where possible in future optimization.
        Currently ensures safe bytes return.
        """
        # Current window content
        current_window = self.buffer[:self.window_size_bytes]
        
        # Construct payload: Overlap + Current
        full_payload = self.overlap_buffer + current_window
        
        # Update Overlap: Last N bytes of current window
        new_overlap = current_window[-self.overlap_size_bytes:]
        self.overlap_buffer = bytearray(new_overlap)
        
        # Slide Buffer: Remove (Window - Overlap)
        # To maintain continuity, we actually just remove the "processed" non-overlapping part?
        # Standard sliding window: Move forward by hop_size = window - overlap
        hop_size = self.window_size_bytes - self.overlap_size_bytes
        self.buffer = self.buffer[hop_size:]
        
        return bytes(full_payload)

    def flush(self) -> Optional[bytes]:
        """
        Force flush the remaining buffer.
        """
        if not self.buffer:
            return None
            
        full_payload = self.overlap_buffer + self.buffer
        self.buffer.clear()
        self.overlap_buffer.clear()
        return bytes(full_payload)
