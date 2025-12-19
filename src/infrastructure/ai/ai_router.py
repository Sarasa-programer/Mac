import asyncio
from typing import Dict, Any, Optional
from src.infrastructure.ai import openai_service
from src.infrastructure.ai import gemini_service
from src.infrastructure.ai import groq_service

class AIServiceRouter:
    """
    Intelligent Router for AI Services (OpenAI, Gemini, Groq).
    Handles fallback logic and provider selection.
    """
    
    def __init__(self):
        self.providers = {
            "openai": openai_service,
            "gemini": gemini_service,
            "groq": groq_service
        }
        self.fallback_chain = {
            "openai": ["gemini", "groq"],
            "gemini": ["openai", "groq"],
            "groq": ["openai", "gemini"]
        }

    async def transcribe_with_fallback(self, file_path: str) -> str:
        """
        Transcribe audio/video using Groq (Strictly enforced).
        No fallback to OpenAI to prevent sending files to GPT.
        """
        # 1. Try Groq (Preferred for speed and mp4)
        try:
            return await groq_service.transcribe_file(file_path)
        except Exception as e:
            print(f"⚠️ Groq Transcription failed: {e}")
            # User explicitly requested NOT to send to GPT.
            # So we raise the error instead of falling back.
            raise e

    async def summarize_with_fallback(self, text: str, preferred_provider: str = "gemini") -> Dict[str, Any]:
        """
        Summarize text with fallback: Gemini -> OpenAI
        """
        # Default chain: Gemini -> OpenAI
        chain = ["gemini", "openai"]
        
        # If user really preferred OpenAI, swap them? 
        # But for this specific task (summarization), the prompt emphasized Gemini.
        # We'll respect preferred_provider if passed, but default to Gemini.
        if preferred_provider == "openai":
            chain = ["openai", "gemini"]
            
        last_error = None
        
        for provider_name in chain:
            try:
                if provider_name == "gemini":
                    result = await gemini_service.summarize_text(text)
                elif provider_name == "openai":
                    result = await openai_service.summarize_text(text)
                else:
                    continue
                    
                result["provider"] = provider_name
                return result
            except Exception as e:
                print(f"⚠️ {provider_name.upper()} Summarization failed: {e}")
                last_error = e
                continue
                
        raise last_error if last_error else Exception("All summarization providers failed.")

    async def analyze_case(self, audio_path: str, mime_type: str, preferred_provider: str = "openai") -> Dict[str, Any]:
        """
        Analyze case with Multi-AI Pipeline:
        1. Transcribe (Groq) - Exclusive
        2. Summarize (Gemini) - Exclusive
        3. Analyze (GPT-4o) - Exclusive for DiffDx/Context
        """
        print(f"🚀 Analyzing case {audio_path} (Type: {mime_type})")
        
        # Step 1: Transcribe (Groq)
        transcript_text = await self.transcribe_with_fallback(audio_path)
        print("✅ Transcription successful (Groq)")
        
        # Step 2 & 3: Summarize (Gemini) & Analyze (GPT) - Parallel execution for speed
        print("🔄 Starting Parallel Analysis (Gemini + GPT)...")
        
        try:
            # Create tasks
            summary_task = asyncio.create_task(gemini_service.generate_case_summary(transcript_text))
            analysis_task = asyncio.create_task(openai_service.generate_clinical_analysis(transcript_text))
            
            # Wait for both
            summary_result, analysis_result = await asyncio.gather(summary_task, analysis_task)
            print("✅ Parallel Analysis Complete")
            
            # Merge results
            final_result = {
                "transcript": transcript_text,
                "title": summary_result.get("title", "Untitled Case"),
                "summary": summary_result.get("summary", {}),
                "differentialDiagnosis": analysis_result.get("differentialDiagnosis", []),
                "keywords": analysis_result.get("keywords", []),
                "nelsonContext": analysis_result.get("nelsonContext", ""),
                "provider": "pipeline(groq+gemini+gpt)" # Indicating the hybrid pipeline
            }
            
            return final_result
            
        except Exception as e:
            print(f"❌ Analysis Pipeline Failed: {e}")
            raise e
        
        return analysis_result

    async def find_pubmed_articles(self, keywords: list, preferred_provider: str = "openai"):
        # Similar fallback logic for search?
        # Gemini doesn't really search Pubmed, it hallucinates or uses internal knowledge unless tools connected.
        # OpenAI service function mock searches or uses tools.
        # Let's just try preferred then fallback to OpenAI (which seems to be the default implementation).
        
        try:
            provider = self.providers.get(preferred_provider, openai_service)
            return await provider.find_pubmed_articles(keywords)
        except Exception:
            # Fallback to OpenAI if not used
            if preferred_provider != "openai":
                return await openai_service.find_pubmed_articles(keywords)
            return []

ai_router = AIServiceRouter()
