import asyncio
from typing import Dict, Any
from src.infrastructure.ai.groq_service import GroqService

async def process_case_pipeline(file_path: str, mime_type: str) -> Dict[str, Any]:
    """
    Orchestrates the full AI pipeline using Groq (Whisper + Llama 3.3).
    Replaces the previous multi-provider pipeline (Gemini/OpenAI) with a unified Groq solution.
    
    Steps:
    1. Transcribe (Whisper-large-v3-turbo)
    2. Comprehensive Analysis (Llama-3.3-70b-versatile)
    """
    service = GroqService()
    
    # 1. Transcribe
    print("🎙️ Groq Transcription (whisper-large-v3-turbo)...")
    transcript_text = await service.transcribe_file(file_path)
    
    if not transcript_text:
        # Fallback or error handling
        print("❌ Transcription returned empty result.")
        raise Exception("Transcription failed or returned empty text.")
        
    print("✅ Transcription successful")

    # 2. Analysis
    print("🧠 Groq Llama 3.3 Comprehensive Analysis...")
    analysis_result = await service.analyze_case_comprehensive(transcript_text)
    
    if not analysis_result:
        print("❌ Analysis failed.")
        raise Exception("Analysis failed.")
        
    print("✅ Analysis Complete")
    
    # Merge results
    final_result = {
        "transcript": transcript_text,
        "title": analysis_result.get("title", "Untitled Case"),
        "summary": analysis_result.get("summary", {}),
        "differentialDiagnosis": analysis_result.get("differentialDiagnosis", []),
        "keywords": analysis_result.get("keywords", []),
        "nelsonContext": analysis_result.get("nelsonContext", ""),
        "provider": "groq-llama-3.3"
    }
    
    return final_result
