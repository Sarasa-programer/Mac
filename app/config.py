from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Primary Provider Selection (for migration)
    primary_provider: str = "openrouter"  # Options: "groq", "openrouter", "openai", "gemini"
    primary_stt_provider: str = "openai"  # Options: "groq", "openai"
    
    # Primary (Groq) - Deprecated, will be phased out
    groq_api_key: Optional[str] = None
    groq_main_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_audio_model: str = "whisper-large-v3-turbo"
    groq_rate_limit: int = 30
    groq_timeout: int = 30

    # Fallback 1 (OpenRouter) - Primary replacement
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "qwen/qwen2.5-72b-instruct:free"
    openrouter_fast_model: str = "qwen/qwen2.5-7b-instruct:free"

    # Fallback 2 (OpenAI)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_whisper_model: str = "whisper-1"

    # Fallback 3 (Gemini)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"

    # Feature Flags (for gradual migration)
    enable_groq: bool = True  # Set to False to disable Groq entirely
    enable_model_abstraction: bool = True
    enable_fallback: bool = True
    
    # Local Whisper (New)
    enable_local_whisper: bool = False
    whisper_model_size: str = "large-v3-turbo" # Options: medium, large-v3, large-v3-turbo
    whisper_device: str = "auto" # Options: auto, cuda, cpu, mps
    whisper_compute_type: str = "float16" # Options: float16, int8_float16, int8


    # PubMed
    ncbi_email: str = "ali.karimian.poco@gmail.com"
    ncbi_tool: str = "MDapi-Clinical-Reasoning"
    pubmed_retmax: int = 5
    pubmed_timeout: int = 10
    pubmed_date_filter: int = 5  # Last 5 years

    # System Config
    log_level: str = "INFO"
    retry_strategy: str = "exponential"
    cache_driver: str = "redis"

    # Redis (Optional)
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in .env

settings = Settings()
