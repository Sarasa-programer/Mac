from pydantic_settings import BaseSettings, SettingsConfigDict # type: ignore
from typing import Optional, List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Pediatric Morning Report AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_AUDIO_MODEL: str = "whisper-large-v3-turbo"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Primary Provider Selection (for migration)
    PRIMARY_PROVIDER: str = "openrouter"  # Options: "groq", "openrouter", "openai", "local"
    PRIMARY_STT_PROVIDER: str = "groq"  # Options: "groq", "openai", "local" - Groq uses Whisper Large V3 Turbo
    
    # OpenRouter Configuration (for Qwen models)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MAIN_MODEL: str = "qwen/qwen2.5-72b-instruct:free"
    OPENROUTER_FAST_MODEL: str = "qwen/qwen2.5-7b-instruct:free"
    
    # OpenAI Configuration (for Whisper)
    OPENAI_WHISPER_MODEL: str = "whisper-1"
    
    # Local Whisper Configuration (New in v1.1)
    ENABLE_LOCAL_WHISPER: bool = False
    WHISPER_MODEL_SIZE: str = "large-v3-turbo" # Options: medium, large-v3, large-v3-turbo
    WHISPER_DEVICE: str = "auto" # Options: auto, cuda, cpu, mps
    WHISPER_COMPUTE_TYPE: str = "float16" # Options: float16, int8_float16, int8
    
    # Fallback Chain Configuration
    FALLBACK_PROVIDERS: str = "openrouter,openai,groq"  # Comma-separated list
    
    # Feature Flags (for gradual migration)
    ENABLE_GROQ: bool = True  # Set to False to disable Groq entirely
    ENABLE_MODEL_ABSTRACTION: bool = True
    ENABLE_FALLBACK: bool = True

    # Audio Settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024  # Bytes per chunk received from client
    
    # Buffer Settings
    WINDOW_DURATION: float = 4.0  # Seconds of audio to send to transcription service
    OVERLAP_DURATION: float = 1.0  # Seconds to overlap between windows
    SILENCE_THRESHOLD: float = 0.5 # Seconds of silence to trigger flush
    
    @property
    def fallback_providers_list(self) -> List[str]:
        """Parse comma-separated fallback providers into a list."""
        return [p.strip() for p in self.FALLBACK_PROVIDERS.split(",") if p.strip()]

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
