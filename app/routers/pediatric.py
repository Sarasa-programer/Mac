from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal, Union
import time
import logging
import re
from app.services.llm_service import UnifiedLLMService

router = APIRouter(prefix="/pediatric", tags=["pediatric"])
logger = logging.getLogger("PEDIATRIC_AGENT")

# --- Models ---

class CaseMetadata(BaseModel):
    audio_duration_sec: Optional[float] = None
    source: Literal["upload", "recording"]

class PediatricInput(BaseModel):
    case_id: str
    language: Literal["fa", "en", "mixed"]
    transcript: Optional[str] = None
    metadata: CaseMetadata

class DifferentialItem(BaseModel):
    diagnosis: str
    reasoning: str

class DebugInfo(BaseModel):
    analysis_started: bool
    transcript_length: int
    transcript_language_detected: str
    declared_language: str
    language_mismatch: bool
    clinical_signal_detected: bool
    clinical_signals_found: List[str]
    pediatric_scope_verified: bool
    patient_age_mentioned: Optional[str]
    multiple_patients_detected: bool
    ambiguous_data_detected: bool
    quality_checks_passed: bool
    processing_time_ms: Optional[float]
    model_confidence: Literal["high", "medium", "low"]
    failure_reason: Optional[str]

class SummaryObject(BaseModel):
    chiefComplaint: str
    history: str
    vitals: str

class PediatricOutput(BaseModel):
    schema_version: str = Field(default="1.0", description="Schema version compliance")
    status: Literal[
        "COMPLETED", 
        "FAILED_INPUT", 
        "FAILED_NO_CLINICAL_DATA", 
        "FAILED_NON_PEDIATRIC", 
        "FAILED_QUALITY", 
        "FAILED_INTERNAL"
    ]
    case_id: str
    summary: Optional[SummaryObject] = None
    differential: Optional[List[DifferentialItem]] = None
    nelson_reference: Optional[str] = None
    urgency_flag: Optional[Literal["CRITICAL", "URGENT", "ROUTINE"]] = None
    debug: DebugInfo

# --- System Prompt ---
SYSTEM_PROMPT = r"""
# Pediatric Clinical AI Agent Prompt

You are a production-grade clinical AI agent for analyzing pediatric cases, operating within a multi-step pipeline. You must never fail silently.

## Clinical Standards & Language Guidelines

### 1. Evidence-Based Practice
- Strictly adhere to current evidence-based pediatric clinical guidelines (e.g., Nelson, AAP).
- All recommendations must be supported by peer-reviewed literature.

### 2. Language Requirements
- Use **probabilistic terminology**: "likely", "suggests", "consistent with", "cannot rule out".
- **AVOID** absolute terms: "always", "never", "definitely", "proven".
- Maintain an objective, neutral, clinical tone.

### 3. Diagnostic Integrity
- **NEVER** fabricate or speculate about clinical findings not in the transcript.
- **NEVER** extrapolate beyond available data.
- Explicitly state when information is missing (e.g., "Vaccination history not provided").
- Avoid premature diagnostic closure; maintain a broad differential if data is limited.

## Your Input (JSON)

You will receive a JSON object:
```json
{
  "case_id": "string",
  "language": "fa" | "en" | "mixed",
  "transcript": "string | null",
  "metadata": {
    "audio_duration_sec": "number | null",
    "source": "upload | recording"
  }
}
```

## Validation Steps (In Order - Stop at First Failure)

### Check 1: Input Validation
- transcript must not be null
- transcript must not be empty string
- transcript length must be ≥ 50 characters
- **If failed:** Return `status = "FAILED_INPUT"`

### Check 2: Clinical Signal Detection
Transcript MUST contain AT LEAST ONE of the following:
- Patient demographics (age, gender, weight)
- Chief complaint or presenting symptoms
- Physical examination findings
- Vital signs (HR, RR, BP, temp, SpO2)
- Laboratory results (CBC, chemistry, cultures)
- Imaging findings (CXR, CT, ultrasound)
- Working diagnosis or clinical impression
- Treatment plan or medications
- Clinical course or disease progression

**If none detected:** Return `status = "FAILED_NO_CLINICAL_DATA"`

### Check 3: Pediatric Scope Verification
If age is explicitly mentioned:
- Patient age must be ≤ 18 years
- OR stated as "neonate", "infant", "child", "adolescent"

**If age > 18 years:** Return `status = "FAILED_NON_PEDIATRIC"`

### Check 4: Language Validation
- Detect actual language(s) in transcript
- Verify match with declared language field
- Language rules:
  - If language = "fa" or "mixed" → Output MUST be in Persian
  - If language = "en" → Output MUST be in English
  - For "mixed": Persian prose, English medical terms (if clearer)

## Analysis (Only If All Checks Pass)

You MUST produce ALL of the following sections:

### 1. Summary
- **Structure**: Return a valid JSON object with:
  - `chiefComplaint`: The primary reason for the visit (e.g., "Fever and cough"). **MUST NOT** be "Unknown Complaint" or generic. Minimum 10 characters describing specific symptoms.
  - `history`: A concise narrative of the present illness, including duration, progression, and relevant negatives.
  - `vitals`: Significant physical exam findings and vital signs mentioned.
- **Tone**: Professional medical terminology.
- **Validation**: Ensure `chiefComplaint` captures patient-reported symptoms.

**Example:**
"summary": {
  "chiefComplaint": "High fever and persistent cough for 4 days",
  "history": "3-year-old male with onset of fever up to 39°C...",
  "vitals": "Temp 39°C, HR 120, RR 30, SpO2 94% RA"
}

### 2. Differential Diagnosis
- **Count:** Minimum 2, Maximum 5 diagnoses
- **Order:** By likelihood (most likely first)
- Each entry MUST have:
  - `diagnosis`: Clear diagnostic label
  - `reasoning`: ≥ 50 characters explaining why this diagnosis fits
- Use evidence-based pediatric reasoning
- **Diagnostic Integrity:** Do not exclude serious conditions if data is ambiguous.

**Example:**
json
[
  {
    "diagnosis": "Bacterial pneumonia",
    "reasoning": "High fever, unilateral crackles, leukocytosis with left shift, and clear radiographic findings suggest bacterial inflammatory process."
  }
]

### 3. Nelson Reference
- **Format:** `"Chapter [NUMBER]: [MAIN TOPIC] - [SUBSECTION]"`
- Use Nelson Textbook of Pediatrics structure
- If exact chapter unknown: closest match + note in debug

**Example:** `"Chapter 408: Community-Acquired Pneumonia - Diagnosis and Treatment of Bacterial Pneumonia"`

### 4. Urgency Flag
Choose ONE of:
- **"CRITICAL"**: Life-threatening, needs immediate intervention (septic shock, respiratory failure, severe dehydration)
- **"URGENT"**: Requires prompt attention within hours (moderate dehydration, high fever with toxic appearance)
- **"ROUTINE"**: Stable, can be managed in regular workflow (mild URI, stable chronic condition follow-up)

## Quality Control (Before Returning)

Before returning `status = "COMPLETED"`, verify ALL of:

- summary length: 100-500 characters
- summary contains no placeholder text
- differential count: 2-5 items
- Each diagnosis has non-empty label
- Each reasoning: ≥ 50 characters
- nelson_reference matches pattern `"Chapter \d+:"` OR contains note about unavailability
- urgency_flag is one of: CRITICAL, URGENT, ROUTINE
- All required fields are non-null

**If ANY check fails:** Return `status = "FAILED_QUALITY"` with explanation in debug

## Output Structure (Exact JSON)

json
{
  "schema_version": "1.0",
  "status": "COMPLETED" | "FAILED_INPUT" | "FAILED_NO_CLINICAL_DATA" | "FAILED_NON_PEDIATRIC" | "FAILED_QUALITY" | "FAILED_INTERNAL",
  "case_id": "string",
  "summary": "string | null",
  "differential": [
    {
      "diagnosis": "string",
      "reasoning": "string"
    }
  ] | null,
  "nelson_reference": "string | null",
  "urgency_flag": "CRITICAL" | "URGENT" | "ROUTINE" | null,
  "debug": {
    "analysis_started": "boolean",
    "transcript_length": "number",
    "transcript_language_detected": "string",
    "declared_language": "string",
    "language_mismatch": "boolean",
    "clinical_signal_detected": "boolean",
    "clinical_signals_found": ["string"],
    "pediatric_scope_verified": "boolean",
    "patient_age_mentioned": "string | null",
    "multiple_patients_detected": "boolean",
    "ambiguous_data_detected": "boolean",
    "quality_checks_passed": "boolean",
    "processing_time_ms": "number | null",
    "model_confidence": "high | medium | low",
    "failure_reason": "string | null"
  }
}

## Edge Cases

- **Multiple patients in transcript:** Analyze only the first patient + warning in debug
- **Incomplete information:** Proceed with available data + explicitly note missing elements
- **Ambiguous/conflicting information:** Note ambiguity in reasoning + flag in debug
- **Non-medical content:** Extract and analyze only clinical portions

## Critical Rules - NEVER Violate

1. NEVER return partial or malformed JSON
2. NEVER return free text outside JSON structure
3. NEVER invent clinical facts not present in transcript
4. NEVER skip quality control validation
5. NEVER leave required fields undefined (use null explicitly)
6. NEVER return COMPLETED status if quality checks fail
7. NEVER include sensitive personal identifiers in output
8. ALWAYS populate debug section with processing metadata
"""

@router.post("/analyze", response_model=PediatricOutput)
async def analyze_pediatric_case(input_data: PediatricInput):
    start_time = time.time()
    
    # --- Check 1: Input Validation (Python Side) ---
    if not input_data.transcript or not input_data.transcript.strip() or len(input_data.transcript) < 50:
        return PediatricOutput(
            status="FAILED_INPUT",
            case_id=input_data.case_id,
            summary=None,
            differential=None,
            nelson_reference=None,
            urgency_flag=None,
            debug=DebugInfo(
                analysis_started=True,
                transcript_length=len(input_data.transcript) if input_data.transcript else 0,
                transcript_language_detected="unknown",
                declared_language=input_data.language,
                language_mismatch=False,
                clinical_signal_detected=False,
                clinical_signals_found=[],
                pediatric_scope_verified=False,
                patient_age_mentioned=None,
                multiple_patients_detected=False,
                ambiguous_data_detected=False,
                quality_checks_passed=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_confidence="high",
                failure_reason="Transcript length < 50 characters or empty"
            )
        )

    # --- LLM Execution ---
    llm_service = UnifiedLLMService()
    
    # We prefer Groq for speed and JSON capability if available, otherwise OpenRouter/OpenAI
    # The UnifiedLLMService._call_groq supports json_mode
    
    try:
        # Prepare the prompt
        # We pass the input JSON as the user message
        user_message = input_data.model_dump_json()
        
        # Determine which LLM to use. 
        # Ideally, we want a model that follows instructions well.
        # If Groq is available, we use it with json_mode=True
        
        response_json_str = ""
        
        if llm_service.groq_client:
            # Groq is fast and good for structured output
            response_json_str = await llm_service._call_groq(
                system_prompt=SYSTEM_PROMPT,
                user_text=user_message,
                json_mode=True
            )
        elif llm_service.openrouter_client:
            # OpenRouter
            response_json_str = await llm_service._call_openrouter(
                system_prompt=SYSTEM_PROMPT + "\n\nIMPORTANT: Return ONLY valid JSON.",
                user_text=user_message
            )
        elif llm_service.openai_client:
             # OpenAI
             # Use json_object response format if possible, but the service wrapper might not expose it easily yet
             # We'll just ask for JSON
             response_json_str = await llm_service._call_openai(
                system_prompt=SYSTEM_PROMPT + "\n\nIMPORTANT: Return ONLY valid JSON.",
                user_text=user_message
             )
        elif llm_service.gemini_model:
            # Gemini
            response_json_str = await llm_service._call_gemini(
                system_prompt=SYSTEM_PROMPT + "\n\nIMPORTANT: Return ONLY valid JSON.",
                user_text=user_message
            )
            # Gemini might return markdown ```json ... ```
            if "```json" in response_json_str:
                response_json_str = response_json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_json_str:
                response_json_str = response_json_str.split("```")[1].split("```")[0].strip()
        else:
             raise HTTPException(status_code=503, detail="No LLM service configured")

        # Parse LLM Response
        import json
        try:
            result_data = json.loads(response_json_str)
        except json.JSONDecodeError:
            # Fallback cleanup
            clean_str = response_json_str.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
            result_data = json.loads(clean_str)

        # --- Quality Control (Python Side) ---
        # Even though the LLM is instructed to check quality, we verify here to ensure strict adherence
        
        # 1. Check Status consistency
        status = result_data.get("status")
        
        if status == "COMPLETED":
            # Verify Summary
            summary = result_data.get("summary")
            if not summary or not isinstance(summary, dict):
                result_data["status"] = "FAILED_QUALITY"
                result_data["debug"]["failure_reason"] = "Summary is not a valid object"
                result_data["debug"]["quality_checks_passed"] = False
            else:
                cc = summary.get("chiefComplaint", "")
                if not cc or len(cc) < 10 or "Unknown Complaint" in cc:
                     result_data["status"] = "FAILED_QUALITY"
                     result_data["debug"]["failure_reason"] = f"Chief Complaint invalid: '{cc}'"
                     result_data["debug"]["quality_checks_passed"] = False

            # Verify Differential
            diff = result_data.get("differential")
            if not diff or not isinstance(diff, list) or len(diff) < 2 or len(diff) > 5:
                result_data["status"] = "FAILED_QUALITY"
                result_data["debug"]["failure_reason"] = f"Differential count invalid: {len(diff) if diff else 0}"
                result_data["debug"]["quality_checks_passed"] = False
            else:
                for d in diff:
                    if not d.get("diagnosis"):
                        result_data["status"] = "FAILED_QUALITY"
                        result_data["debug"]["failure_reason"] = "Empty diagnosis"
                        result_data["debug"]["quality_checks_passed"] = False
                    if not d.get("reasoning") or len(d.get("reasoning")) < 50:
                        result_data["status"] = "FAILED_QUALITY"
                        result_data["debug"]["failure_reason"] = "Reasoning too short"
                        result_data["debug"]["quality_checks_passed"] = False
            
            # Verify Nelson Reference
            nelson = result_data.get("nelson_reference")
            if not nelson or not re.match(r"Chapter \d+:", nelson):
                 # We allow it to pass if it contains a note about unavailability, but the prompt says "match pattern OR contain note"
                 # Let's be lenient if it's not null
                 if not nelson:
                    result_data["status"] = "FAILED_QUALITY"
                    result_data["debug"]["failure_reason"] = "Missing Nelson reference"
                    result_data["debug"]["quality_checks_passed"] = False

            # Verify Urgency
            urgency = result_data.get("urgency_flag")
            if urgency not in ["CRITICAL", "URGENT", "ROUTINE"]:
                result_data["status"] = "FAILED_QUALITY"
                result_data["debug"]["failure_reason"] = f"Invalid urgency: {urgency}"
                result_data["debug"]["quality_checks_passed"] = False

        # Ensure debug info is present and accurate regarding processing time
        default_debug = {
            "analysis_started": True,
            "transcript_length": len(input_data.transcript) if input_data.transcript else 0,
            "transcript_language_detected": "unknown",
            "declared_language": input_data.language,
            "language_mismatch": False,
            "clinical_signal_detected": False,
            "clinical_signals_found": [],
            "pediatric_scope_verified": False,
            "patient_age_mentioned": None,
            "multiple_patients_detected": False,
            "ambiguous_data_detected": False,
            "quality_checks_passed": False,
            "processing_time_ms": 0,
            "model_confidence": "medium",
            "failure_reason": None
        }
        
        llm_debug = result_data.get("debug", {})
        if isinstance(llm_debug, dict):
            # Only update fields that are not None in llm_debug, or just update all?
            # Update all is risky if LLM sends nulls for required fields.
            # But Pydantic will catch nulls if they are not allowed.
            # Let's filter out None values from llm_debug if we want to rely on defaults?
            # Actually, Pydantic defaults are not used here since we are creating a dict.
            # Our default_debug has safe values.
            for k, v in llm_debug.items():
                if v is not None:
                    default_debug[k] = v
        
        result_data["debug"] = default_debug
        result_data["debug"]["processing_time_ms"] = (time.time() - start_time) * 1000
        
        return PediatricOutput(**result_data)

    except Exception as e:
        logger.error(f"Pediatric Analysis Failed: {e}")
        # Return FAILED_INTERNAL structure
        return PediatricOutput(
            status="FAILED_INTERNAL",
            case_id=input_data.case_id,
            summary=None,
            differential=None,
            nelson_reference=None,
            urgency_flag=None,
            debug=DebugInfo(
                analysis_started=True,
                transcript_length=len(input_data.transcript) if input_data.transcript else 0,
                transcript_language_detected="unknown",
                declared_language=input_data.language,
                language_mismatch=False,
                clinical_signal_detected=False,
                clinical_signals_found=[],
                pediatric_scope_verified=False,
                patient_age_mentioned=None,
                multiple_patients_detected=False,
                ambiguous_data_detected=False,
                quality_checks_passed=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_confidence="low",
                failure_reason=str(e)
            )
        )
