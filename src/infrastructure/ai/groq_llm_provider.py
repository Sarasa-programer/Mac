import logging
import json
from typing import List, Dict, Any, Optional
from groq import AsyncGroq, APIConnectionError, RateLimitError, APIStatusError
from src.core.interfaces.llm_provider import LLMProvider
from src.config.settings import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

logger = logging.getLogger(__name__)

class GroqLLMProvider(LLMProvider):
    """
    Groq implementation of LLMProvider (deprecated - for backward compatibility).
    This provider will be phased out in favor of OpenRouter/Qwen.
    """
    
    def __init__(self):
        api_key = settings.GROQ_API_KEY
        if not api_key:
            logger.warning("⚠️ GROQ_API_KEY not found in settings!")
        
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=0)
        http_client = httpx.AsyncClient(transport=transport, timeout=60.0)
        
        self.client = AsyncGroq(
            api_key=api_key,
            http_client=http_client,
            max_retries=0
        )
        
        self.main_model = settings.GROQ_MODEL
        
        if api_key:
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
            logger.info(f"GroqLLMProvider initialized (DEPRECATED) | Key: {masked_key} | Model: {self.main_model}")
            logger.warning("⚠️ GroqLLMProvider is deprecated. Consider migrating to OpenRouterLLMProvider.")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, APIConnectionError, RateLimitError, APIStatusError))
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.5,
        json_mode: bool = False
    ) -> str:
        """
        Send a chat completion request using Groq (deprecated).
        """
        try:
            target_model = model or self.main_model
            
            kwargs = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            completion = await self.client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"Groq Chat Error: {e}")
            raise e
    
    async def analyze_case_comprehensive(self, transcript: str) -> Dict[str, Any]:
        """
        Performs comprehensive case analysis using Groq Llama 3.3 (deprecated).
        """
        system_prompt = """You are a pediatric expert assistant. Analyze the following morning report case transcript.
        Return a valid JSON object with the following structure:
        {
            "title": "string (A suitable title for the case)",
            "summary": {
                "chiefComplaint": "string",
                "history": "string",
                "vitals": "string"
            },
            "differentialDiagnosis": ["string (Diagnosis 1)", "string (Diagnosis 2)", ...],
            "keywords": ["string (Keyword 1)", ...],
            "nelsonContext": "string (Summary of the condition from Nelson Textbook of Pediatrics context)"
        }
        Ensure the JSON is valid and strictly follows this schema.
        """
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ]
            
            response = await self.chat(
                messages=messages,
                temperature=0.1,
                json_mode=True
            )
            
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Groq JSON Decode Error: {e}")
            return {
                "title": "Analysis Failed",
                "summary": {"chiefComplaint": "N/A", "history": "N/A", "vitals": "N/A"},
                "differentialDiagnosis": [],
                "keywords": [],
                "nelsonContext": "N/A"
            }
        except Exception as e:
            logger.error(f"Groq Comprehensive Analysis Error: {e}")
            raise e

