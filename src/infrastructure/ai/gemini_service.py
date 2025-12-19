import os
import json
from google import genai
from google.genai import types
from src.config.settings import settings

client = genai.Client(api_key=settings.GOOGLE_API_KEY)

async def generate_case_summary(text: str):
    """
    Generate only the case summary (Title, Chief Complaint, History, Vitals) using Gemini.
    """
    print("📋 Gemini Summarization (Exclusive)...")
    response_schema = {
      "type": "OBJECT",
      "properties": {
        "title": { "type": "STRING" },
        "summary": {
          "type": "OBJECT",
          "properties": {
            "chiefComplaint": { "type": "STRING", "description": "Clean clinical reformulation for the summary page." },
            "dashboardChiefComplaint": { "type": "STRING", "description": "Very short phrase (3-6 words) for dashboard view. Ex: 'Fever and diarrhea'." },
            "history": { "type": "STRING", "description": "Clinically rewritten HPI, chronological, no raw transcript." },
            "vitals": { "type": "STRING", "description": "Structured vital signs if available." },
          },
          "required": ["chiefComplaint", "dashboardChiefComplaint", "history", "vitals"],
        }
      },
      "required": ["title", "summary"],
    }

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text="""You are a pediatric expert assistant. Analyze this morning report transcript. Provide a suitable title and a structured summary.
                        
STRICT RULES:
1. Dashboard Chief Complaint: ONLY a very short phrase (3-6 words). Ex: "Fever and diarrhea". NO sentences.
2. Case Summary Chief Complaint: Clean clinical reformulation. NO raw patient speech.
3. HPI: Clinically rewritten, chronological. NO raw transcript.
4. Vitals: Structured if available.
"""),
                        types.Part.from_text(text=text)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        print(f"❌ Gemini Summary Failed: {e}")
        raise e

async def summarize_text(text: str):
    """
    Summarize text using Gemini Pro.
    """
    print("📋 Gemini Summarization...")
    response_schema = {
      "type": "OBJECT",
      "properties": {
        "title": { "type": "STRING" },
        "transcript": { "type": "STRING" },
        "summary": {
          "type": "OBJECT",
          "properties": {
            "chiefComplaint": { "type": "STRING", "description": "Clean clinical reformulation for summary." },
            "dashboardChiefComplaint": { "type": "STRING", "description": "Very short phrase (3-6 words) for dashboard. Ex: 'Fever and diarrhea'." },
            "history": { "type": "STRING", "description": "Clinically rewritten HPI, chronological." },
            "vitals": { "type": "STRING" },
          },
          "required": ["chiefComplaint", "dashboardChiefComplaint", "history", "vitals"],
        },
        "differentialDiagnosis": {
          "type": "ARRAY",
          "items": { "type": "STRING" },
        },
        "keywords": {
          "type": "ARRAY",
          "items": { "type": "STRING" },
        },
        "nelsonContext": { "type": "STRING" },
      },
      "required": ["title", "transcript", "summary", "differentialDiagnosis", "keywords", "nelsonContext"],
    }

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text="""You are a pediatric expert assistant. Analyze this morning report transcript.
                        
STRICT RULES:
1. Dashboard Chief Complaint: ONLY a very short phrase (3-6 words). Ex: "Fever and diarrhea".
2. Case Summary Chief Complaint: Clean clinical reformulation. NO raw patient speech.
3. HPI: Clinically rewritten, chronological. NO raw transcript.
4. Vitals: Structured if available.
"""),
                        types.Part.from_text(text=text)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        
        result = json.loads(response.text)
        if not result.get("transcript"):
            result["transcript"] = text
        return result
        
    except Exception as e:
        print(f"❌ Gemini Summarization Failed: {e}")
        raise e

async def analyze_audio_case(audio_path: str, mime_type: str = "audio/mp3"):
    
    # Upload file (or send bytes directly if supported, but typically file API is better for large audio)
    # For simplicity with GenAI SDK, we can pass the file path if local, or bytes.
    # Assuming local file path from upload.
    
    with open(audio_path, "rb") as f:
        file_content = f.read()

    # Define schema
    response_schema = {
      "type": "OBJECT",
      "properties": {
        "title": { "type": "STRING" },
        "transcript": { "type": "STRING" },
        "summary": {
          "type": "OBJECT",
          "properties": {
            "chiefComplaint": { "type": "STRING", "description": "Clean clinical reformulation for summary." },
            "dashboardChiefComplaint": { "type": "STRING", "description": "Very short phrase (3-6 words) for dashboard." },
            "history": { "type": "STRING", "description": "Clinically rewritten HPI." },
            "vitals": { "type": "STRING" },
          },
          "required": ["chiefComplaint", "dashboardChiefComplaint", "history", "vitals"],
        },
        "differentialDiagnosis": {
          "type": "ARRAY",
          "items": { "type": "STRING" },
        },
        "keywords": {
          "type": "ARRAY",
          "items": { "type": "STRING" },
        },
        "nelsonContext": { "type": "STRING" },
      },
      "required": ["title", "transcript", "summary", "differentialDiagnosis", "keywords", "nelsonContext"],
    }

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text="""You are a pediatric expert assistant. Listen to this morning report case. Transcribe it, summarize it, list differential diagnoses, provide search keywords, and summarize the relevant section from Nelson Textbook of Pediatrics.

STRICT RULES:
1. Dashboard Chief Complaint: ONLY a very short phrase (3-6 words). Ex: "Fever and diarrhea".
2. Case Summary Chief Complaint: Clean clinical reformulation. NO raw patient speech.
3. HPI: Clinically rewritten, chronological. NO raw transcript.
4. Vitals: Structured if available.
"""),
                    types.Part.from_bytes(data=file_content, mime_type=mime_type)
                ]
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema
        )
    )
    
    return json.loads(response.text)

async def find_pubmed_articles(keywords: list[str]):
    query = f"Find PubMed articles for pediatric case: {', '.join(keywords)}"
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    
    # Parse grounding metadata
    # Python SDK structure might differ slightly from JS
    # Typically response.candidates[0].grounding_metadata
    
    articles = []
    if response.candidates and response.candidates[0].grounding_metadata:
         chunks = response.candidates[0].grounding_metadata.grounding_chunks
         if chunks:
             for chunk in chunks:
                 if chunk.web and chunk.web.uri and chunk.web.title:
                     articles.append({
                         "title": chunk.web.title,
                         "url": chunk.web.uri,
                         "snippet": "Referenced via Google Search Grounding"
                     })
    
    # Deduplicate
    unique_articles = {v['url']: v for v in articles}.values()
    return list(unique_articles)
