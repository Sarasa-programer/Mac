from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Primary (Groq)
    groq_api_key: Optional[str] = None
    groq_main_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_audio_model: str = "whisper-large-v3-turbo"
    groq_rate_limit: int = 30
    groq_timeout: int = 30

    # Fallback 1 (OpenRouter)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "qwen/qwen-2.5-72b-instruct:free"

    # Fallback 2 (OpenAI)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"

    # Fallback 3 (Gemini)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"

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
