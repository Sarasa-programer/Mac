from pydantic_settings import BaseSettings, SettingsConfigDict # type: ignore

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

    # Audio Settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024  # Bytes per chunk received from client
    
    # Buffer Settings
    WINDOW_DURATION: float = 4.0  # Seconds of audio to send to Groq
    OVERLAP_DURATION: float = 1.0  # Seconds to overlap between windows
    SILENCE_THRESHOLD: float = 0.5 # Seconds of silence to trigger flush

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
