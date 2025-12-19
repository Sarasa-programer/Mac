import json
import openai
from openai import OpenAI
from src.config.settings import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def transcribe_file(audio_path: str):
    """
    Transcribe audio using OpenAI Whisper-1.
    """
    print("🎙️ OpenAI Transcription...")
    with open(audio_path, "rb") as audio_file:
        try:
            # Try GPT-4o-audio-preview or similar if available, but standard is whisper-1
            # For fallback, whisper-1 is standard.
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            return transcription
        except Exception as e:
            print(f"❌ OpenAI Transcription Failed: {e}")
            raise e

async def generate_clinical_analysis(text: str):
    """
    Generate clinical analysis (Diff Dx, Keywords, Nelson Context) using GPT-4o.
    """
    print("🧠 GPT-4o Clinical Analysis...")
    system_prompt = """You are a pediatric expert assistant. Analyze the following morning report case transcript. 
    Return a JSON object with:
    - differentialDiagnosis: string[] (List of 5 potential diagnoses)
    - keywords: string[] (List of search terms)
    - nelsonContext: string (Summary of the condition from Nelson Textbook of Pediatrics context)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={ "type": "json_object" }
        )

        analysis_content = response.choices[0].message.content
        return json.loads(analysis_content)
    except Exception as e:
        print(f"❌ GPT-4o Analysis Failed: {e}")
        raise e

async def summarize_text(text: str):
    """
    Summarize text using GPT-4o.
    """
    print("📋 OpenAI Summarization...")
    system_prompt = """You are a pediatric expert assistant. Analyze the following morning report case transcript. 
    Return a JSON object with:
    - title: string (A suitable title for the case)
    - transcript: string (The original transcript)
    - summary: object { chiefComplaint: string, history: string, vitals: string }
    - differentialDiagnosis: string[] (List of 5 potential diagnoses)
    - keywords: string[] (List of search terms)
    - nelsonContext: string (Summary of the condition from Nelson Textbook of Pediatrics context)
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        response_format={ "type": "json_object" }
    )

    analysis_content = response.choices[0].message.content
    analysis = json.loads(analysis_content)
    
    if not analysis.get("transcript"):
        analysis["transcript"] = text
        
    return analysis

async def analyze_audio_case(audio_path: str, mime_type: str = "audio/mp3"):
    # 1. Transcription (prefer GPT-4o Transcribe, fallback to Whisper)
    # Re-using the logic for standalone call compatibility
    transcript_text = await transcribe_file(audio_path)
    
    # 2. Analysis (GPT-4o)
    return await summarize_text(transcript_text)

async def find_pubmed_articles(keywords: list[str]):
    # OpenAI doesn't have a direct search tool without extensions.
    # We will generate search links similar to the previous frontend implementation.
    return [
        {
            "title": f"Search PubMed for {kw}",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={kw.replace(' ', '+')}",
            "snippet": "Click to view search results on PubMed"
        }
        for kw in keywords[:5]
    ]
