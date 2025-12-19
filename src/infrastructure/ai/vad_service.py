import webrtcvad
import logging
# audioop is deprecated/removed in Python 3.13, using numpy as replacement
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import asyncio

class VADService:
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000):
        """
        :param aggressiveness: 0-3 (2 is balanced)
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        # Energy threshold for quick rejection (RMS)
        self.energy_threshold = 300 
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def is_speech(self, frame_bytes: bytes) -> bool:
        """
        Checks if the given frame contains speech.
        Uses Hybrid Approach: Energy Check -> WebRTC VAD
        Offloads CPU-intensive VAD to thread pool.
        """
        # 1. Fast Energy Check (Main Thread)
        try:
            # Calculate RMS using numpy instead of audioop
            # Convert bytes to int16 array
            audio_data = np.frombuffer(frame_bytes, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(np.float64)**2))
            
            if rms < self.energy_threshold:
                return False
        except Exception:
            pass # Fallback to VAD if rms fails

        # 2. WebRTC VAD (Thread Pool)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._vad_check, frame_bytes)

    def _vad_check(self, frame_bytes: bytes) -> bool:
        try:
            return self.vad.is_speech(frame_bytes, self.sample_rate)
        except Exception:
            return True # Fail open 
