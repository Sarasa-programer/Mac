import webrtcvad
import logging

class VADService:
    def __init__(self, aggressiveness: int = 3, sample_rate: int = 16000):
        """
        :param aggressiveness: 0-3 (3 is most aggressive in filtering out non-speech)
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)

    def is_speech(self, frame_bytes: bytes) -> bool:
        """
        Checks if the given frame contains speech.
        Frame length must be 10, 20, or 30 ms.
        For 16000Hz, 10ms = 320 bytes, 20ms = 640 bytes, 30ms = 960 bytes.
        """
        try:
            return self.vad.is_speech(frame_bytes, self.sample_rate)
        except Exception as e:
            # If frame size is incorrect, webrtcvad throws error. 
            # We log and assume speech to avoid losing data, or silence to be safe? 
            # Assuming silence is safer to avoid garbage, but for STT we prefer false positives.
            # self.logger.warning(f"VAD Error: {e}")
            return True 
