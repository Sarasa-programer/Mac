import logging
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError
from src.core.interfaces.llm_provider import LLMProvider
from src.config.settings import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class OpenAILLMProvider(LLMProvider):
    """
    OpenAI implementation of LLMProvider.
    """
    
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY not found in settings!")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.main_model = settings.OPENAI_MODEL
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, RateLimitError, APIStatusError))
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.5,
        json_mode: bool = False
    ) -> str:
        """
        Send a chat completion request using OpenAI.
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
            logger.error(f"OpenAI Chat Error: {e}")
            raise e
    
    async def analyze_case_comprehensive(self, transcript: str) -> Dict[str, Any]:
        """
        Performs comprehensive case analysis using OpenAI GPT-4o.
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
            logger.error(f"OpenAI JSON Decode Error: {e}")
            return {
                "title": "Analysis Failed",
                "summary": {"chiefComplaint": "N/A", "history": "N/A", "vitals": "N/A"},
                "differentialDiagnosis": [],
                "keywords": [],
                "nelsonContext": "N/A"
            }
        except Exception as e:
            logger.error(f"OpenAI Comprehensive Analysis Error: {e}")
            raise e
