from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Persian Real-time STT"
    DEBUG: bool = True
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "whisper-large-v3"
    
    # Audio Settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024  # Bytes per chunk received from client
    
    # Buffer Settings
    WINDOW_DURATION: float = 4.0  # Seconds of audio to send to Groq
    OVERLAP_DURATION: float = 1.0  # Seconds to overlap between windows
    SILENCE_THRESHOLD: float = 0.5 # Seconds of silence to trigger flush
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

@lru_cache()
def get_settings():
    return Settings()
