from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    """
    Abstract Interface for Large Language Model Providers.
    Enables switching between Groq, OpenRouter/Qwen, OpenAI, and other providers.
    """
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.5,
        json_mode: bool = False
    ) -> str:
        """
        Send a chat completion request to the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Optional model name override
            temperature: Sampling temperature (0.0 to 2.0)
            json_mode: Whether to force JSON response format
            
        Returns:
            str: The model's response text
        """
        pass
    
    @abstractmethod
    async def analyze_case_comprehensive(self, transcript: str) -> Dict[str, Any]:
        """
        Perform comprehensive case analysis with structured JSON output.
        
        Args:
            transcript: The transcribed text to analyze
            
        Returns:
            dict: Structured analysis result with keys:
                - title: str
                - summary: dict (chiefComplaint, history, vitals)
                - differentialDiagnosis: list[str]
                - keywords: list[str]
                - nelsonContext: str
        """
        pass

