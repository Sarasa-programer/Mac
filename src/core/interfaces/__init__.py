"""
Core interfaces for AI providers.
These interfaces define contracts that all implementations must follow,
enabling provider-agnostic code and easy migration between providers.
"""
from .transcription_provider import TranscriptionProvider
from .llm_provider import LLMProvider

__all__ = [
    "TranscriptionProvider",
    "LLMProvider",
]

