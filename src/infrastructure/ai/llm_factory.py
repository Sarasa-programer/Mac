import os
import logging
from typing import Optional
from src.core.interfaces.llm_provider import LLMProvider
from src.config.settings import settings

logger = logging.getLogger(__name__)

class LLMProviderFactory:
    """
    Factory to create LLMProvider instances based on configuration.
    Supports multiple providers with fallback mechanism.
    """
    
    @staticmethod
    def get_provider(provider_name: Optional[str] = None) -> LLMProvider:
        """
        Get an LLM provider instance based on configuration.
        
        Args:
            provider_name: Provider name ('groq', 'openrouter', 'openai', etc.)
                          If None, uses PRIMARY_PROVIDER from settings.
        
        Returns:
            LLMProvider instance
        """
        if not provider_name:
            provider_name = getattr(settings, 'PRIMARY_PROVIDER', 'openrouter').lower()
        
        provider_name = provider_name.lower()
        
        # Lazy imports to avoid circular dependencies
        if provider_name == "openrouter":
            try:
                from src.infrastructure.ai.openrouter_provider import OpenRouterLLMProvider
                return OpenRouterLLMProvider()
            except ImportError as e:
                logger.warning(f"OpenRouter provider not available: {e}")
                # Fallback to Groq if available
                if getattr(settings, 'ENABLE_GROQ', True):
                    return LLMProviderFactory.get_provider("groq")
                raise
        
        elif provider_name == "groq":
            if not getattr(settings, 'ENABLE_GROQ', True):
                logger.warning("Groq is disabled. Falling back to OpenRouter.")
                return LLMProviderFactory.get_provider("openrouter")
            
            try:
                from src.infrastructure.ai.groq_llm_provider import GroqLLMProvider
                return GroqLLMProvider()
            except ImportError as e:
                logger.warning(f"Groq provider not available: {e}")
                raise
        
        elif provider_name == "openai":
            # OpenAI LLM provider (for GPT models, not just Whisper)
            try:
                # Could implement OpenAILLMProvider if needed
                logger.warning("OpenAI LLM provider not yet implemented, using OpenRouter")
                return LLMProviderFactory.get_provider("openrouter")
            except Exception as e:
                logger.error(f"OpenAI provider error: {e}")
                raise
        
        else:
            logger.warning(f"Unknown provider '{provider_name}', defaulting to OpenRouter")
            return LLMProviderFactory.get_provider("openrouter")
    
    @staticmethod
    def get_provider_with_fallback() -> LLMProvider:
        """
        Get provider with automatic fallback chain.
        Tries providers in order: PRIMARY_PROVIDER -> fallback chain.
        
        Returns:
            First available LLMProvider
        """
        primary = getattr(settings, 'PRIMARY_PROVIDER', 'openrouter').lower()
        fallbacks = getattr(settings, 'fallback_providers_list', ['openrouter', 'groq'])
        
        # Try primary first
        providers_to_try = [primary] + [p for p in fallbacks if p != primary]
        
        last_error = None
        for provider_name in providers_to_try:
            try:
                provider = LLMProviderFactory.get_provider(provider_name)
                logger.info(f"✅ Using LLM provider: {provider_name}")
                return provider
            except Exception as e:
                logger.warning(f"⚠️ Provider '{provider_name}' failed: {e}")
                last_error = e
                continue
        
        raise last_error if last_error else Exception("No LLM provider available")

