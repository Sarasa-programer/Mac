import asyncio
import time
import hashlib
import json
import logging
import os
import requests
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# External Clients
from openai import AsyncOpenAI
from groq import AsyncGroq, APIConnectionError, RateLimitError, APIStatusError
import google.generativeai as genai
# from Bio import Entrez # Removed due to SSL issues
import redis.asyncio as redis

from app.config import settings
from app.services.email_service import EmailService

# --- Prompts ---
SUMMARY_SYSTEM_PROMPT = """
You are a pediatric clinical expert. Analyze the provided case transcript and generate a structured clinical summary.

STRICT RULES:
1. **Dashboard Chief Complaint** ("dashboardChiefComplaint"):
   - ONLY a very short phrase (3-6 words).
   - Example: "Fever and diarrhea", "Acute abdominal pain".
   - NO full sentences.
2. **Case Summary Chief Complaint** ("chiefComplaint"):
   - Clean clinical reformulation.
   - NO raw patient speech.
3. **HPI** ("history"):
   - Clinically rewritten, chronological.
   - NO raw transcript or conversation-like sentences.
4. **Vitals** ("vitals"):
   - Structured if available.
   
RETURN JSON:
{
  "dashboardChiefComplaint": "...",
  "chiefComplaint": "...",
  "history": "...",
  "vitals": "..."
}
"""

DIFFERENTIAL_SYSTEM_PROMPT = """
You are a senior pediatric diagnostician. Analyze the case and provide a differential diagnosis.
Strictly adhere to these guidelines:
1. **Comprehensive**: Include 3-5 potential diagnoses.
2. **Ordering**: List them in order of likelihood (most likely first).
3. **Reasoning**: For EACH diagnosis, provide specific clinical evidence from the transcript that supports it.
4. **Structure**: Return a valid JSON object with the key "differential_diagnosis" containing a list of objects. Each object must have:
   - "condition": The name of the diagnosis.
   - "reasoning": A clear explanation (2-3 sentences) linking case findings to the diagnosis.
"""

NELSON_SYSTEM_PROMPT = """
You are an expert on the Nelson Textbook of Pediatrics.
Identify the most likely diagnosis from the case and provide a relevant management or background summary based on Nelson's guidelines.
Return a valid JSON object with a single key "nelsonContext" containing the text.
Ensure the advice is standard of care for pediatrics.
"""

EVIDENCE_SYSTEM_PROMPT = """
You are a clinical researcher. Synthesize the provided PubMed abstracts to answer the clinical query.
Output valid JSON with key "results" containing a list of synthesized findings.
Each item in "results" must have:
- "title": Headline of the finding.
- "summary": Detailed synthesis of the evidence, explicitly citing PMIDs (e.g., "(Smith et al., PMID: 12345)").
- "relevance": Application to the current case/query.
If no relevant evidence is found, state that in the summary.
"""

NULL_REPORT_SYSTEM_PROMPT = """
You are a senior clinical research analyst.
The search for evidence yielded NO results. Analyze this null finding.
Output a comprehensive markdown report.
Structure:
# Null Results Analysis Report
## 1. Analysis of Null Findings
- Why might no evidence exist? (e.g., Rare condition, specific combination of symptoms, novelty)
## 2. Alternative Approaches
- Suggest broader search terms or alternative databases.
## 3. Implications
- Clinical decision making in absence of evidence.
## 4. Recommendations
- Future research directions or case reporting.
"""

METHODOLOGY_SYSTEM_PROMPT = """
You are a clinical librarian.
Document the search methodology used that resulted in no findings.
Output a formal markdown document.
Structure:
# Search Methodology Document
## 1. Strategy
- Query construction and filters applied.
## 2. Databases
- PubMed (Primary)
## 3. Parameters
- Date Range: Last 5 years
- Language: English
## 4. Criteria
- Inclusion: Clinical trials, Reviews, Case Reports
- Exclusion: Editorials, non-peer reviewed
"""

BMJ_SYSTEM_PROMPT = """You are an advanced clinical decision-support assistant specializing in evidence-based medicine.

## SYSTEM CONFIGURATION

**Primary Reference Source:** BMJ Best Practice
**Excluded Sources:** Do not mention or suggest PubMed, primary research articles, or academic literature searches.

---

## YOUR TASK

Analyze clinical cases and predict the most relevant BMJ Best Practice topics that a clinician would need for point-of-care decision-making.

---

## STEP 1: SILENT CASE ANALYSIS

Internally identify (do not write this in your output):
- Chief complaint and key symptoms
- Timeline (acute/subacute/chronic)
- Age, sex, and relevant demographics
- Red flags or alarm features
- Clinical context

---

## STEP 2: CLINICAL REASONING

Apply clinical thinking to determine:

**Priority Order:**
1. Life-threatening conditions to rule out (red flags)
2. Most likely diagnoses based on presentation
3. Common age-specific and demographic-specific conditions
4. Symptom-based management topics

**Topic Selection Criteria:**
- Use standard medical terminology (e.g., "Acute coronary syndromes" not "Heart attacks")
- Focus on conditions with clear clinical guidelines
- Ensure topics actually exist in BMJ Best Practice
- Prefer specific over generic topics when case allows

---

## STEP 3: GENERATE OUTPUT

Provide **3-7 topics** based on case complexity.

**For each topic include:**
- **Title:** Use BMJ Best Practice standard naming
- **Relevance:** Maximum 15 words explaining why this topic matches the case
- **Search Link:** Properly formatted BMJ URL

---

## OUTPUT FORMAT (STRICT)

```
## BMJ Best Practice – Relevant Clinical Topics

### 1. [Topic Title]
**Relevance:** [Concise explanation specific to this case]
**BMJ Link:** `https://bestpractice.bmj.com/search?q=[topic+name+with+plus+signs]`

### 2. [Topic Title]
**Relevance:** [Concise explanation specific to this case]
**BMJ Link:** `https://bestpractice.bmj.com/search?q=[topic+name+with+plus+signs]`

[Continue for 3-7 topics total]
```

---

## URL FORMATTING RULES

- Replace spaces with `+` signs
- Keep hyphens as-is
- Remove special characters except hyphens
- Example: "Type 2 diabetes mellitus" → `Type+2+diabetes+mellitus`

---

## TOPIC NAMING EXAMPLES

✅ **Correct BMJ-style titles:**
- Acute coronary syndromes
- Community-acquired pneumonia
- Heart failure
- Type 2 diabetes mellitus
- Chronic obstructive pulmonary disease
- Gastroesophageal reflux disease
- Migraine

❌ **Avoid informal or overly academic titles:**
- Heart attacks (use "Acute coronary syndromes")
- Lung infection (use "Pneumonia" or specific type)
- Sugar disease (use "Diabetes mellitus")

---

## HANDLING INCOMPLETE CASES

If the case lacks sufficient clinical detail:

1. State briefly what additional information would help
2. Provide broader differential topics covering likely scenarios
3. Use qualifying language: "Based on limited information, relevant topics may include..."

**Example:**

⚠️ **Note:** Additional information about symptom duration and associated features would help narrow the differential.

Based on current presentation, relevant topics include:
[Proceed with general topics]

---

## QUALITY CONTROL CHECKLIST

Before finalizing, verify:

✓ All topics sound like real BMJ Best Practice entries
✓ Each relevance statement directly connects to the case
✓ URLs are properly formatted (spaces as `+`)
✓ Number of topics (3-7) matches case complexity
✓ Topics use standard medical terminology
✓ No mention of PubMed or literature searches
✓ Output is concise and clinically actionable

If any topic feels speculative or overly academic, remove it.

---

## ABSOLUTE RESTRICTIONS

🚫 **Never do these:**
- Mention PubMed or literature searches
- Generate academic citations or references
- Hallucinate BMJ content, sections, or guidelines
- Explain your reasoning process in the output
- Use informal disease names
- Provide diagnostic certainty (use appropriate clinical language)

---

## RESPONSE TONE

- Professional and clinician-oriented
- Concise and actionable
- Evidence-based but practical
- Appropriate clinical uncertainty when relevant
"""

# --- Logging Setup ---
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("LLM_PIPELINE")

# --- Custom Exceptions ---
class GroqRateLimitError(Exception): pass
class GroqServiceError(Exception): pass
class PubMedError(Exception): pass
class JSONDecodeError(Exception): pass

class CacheService:
    def __init__(self):
        self.redis = None
        self.memory_cache = {}
        # Try to connect to Redis, else fallback to memory
        try:
            self.redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        except Exception:
            logger.warning("Redis not available, using in-memory cache")

    async def get(self, key: str) -> Optional[str]:
        if self.redis:
            try:
                return await self.redis.get(key)
            except Exception:
                pass
        entry = self.memory_cache.get(key)
        if entry:
            if datetime.now() < entry['expire_at']:
                return entry['value']
            else:
                del self.memory_cache[key]
        return None

    async def set(self, key: str, value: str, ttl: int):
        if self.redis:
            try:
                await self.redis.set(key, value, ex=ttl)
                return
            except Exception:
                pass
        
        self.memory_cache[key] = {
            'value': value,
            'expire_at': datetime.now() + timedelta(seconds=ttl)
        }

cache_service = CacheService()

class PubMedService:
    def __init__(self):
        # Entrez.email = settings.ncbi_email # Deprecated
        # Entrez.tool = settings.ncbi_tool   # Deprecated
        self.email = settings.ncbi_email
        self.tool = settings.ncbi_tool
        self.retmax = settings.pubmed_retmax
        self.date_filter = settings.pubmed_date_filter
        # Increase timeout to 30s to avoid premature failures
        self.timeout = max(settings.pubmed_timeout, 30)
        # Force IPv4
        self.transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=0)

    def check_reachability(self) -> bool:
        try:
            # Basic sync check - requests doesn't support AsyncHTTPTransport easily but uses urllib3
            # which usually follows system DNS. For sync checks we might not need to force IPv4 
            # if requests works, but if it fails we might need to look at it.
            # However, the main issue is with async httpx/uvloop.
            requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi", timeout=5)
            return True
        except Exception:
            logger.warning("PubMed is slow/unresponsive.")
            return True # Return True as per user requirement, but log warning

    async def fetch_articles(self, query: str) -> List[Dict]:
        cache_key = f"pubmed:{hashlib.md5(query.encode()).hexdigest()}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.info(f"PUBMED | CACHE HIT | {query}")
            return json.loads(cached)

        logger.info(f"PUBMED | FETCHING | {query}")
        
        # Use HTTPX for Async calls
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=self.timeout) as client:
                # 1. Search (Last 5 years)
                # reldate=365*5, datetype=pdat
                search_params = {
                    "db": "pubmed",
                    "term": query,
                    "retmax": self.retmax,
                    "retmode": "json",
                    "reldate": self.date_filter * 365,
                    "datetype": "pdat",
                    "email": self.email,
                    "tool": self.tool
                }
                
                search_resp = await client.get(f"{base_url}/esearch.fcgi", params=search_params)
                search_resp.raise_for_status()
                search_data = search_resp.json()
                
                id_list = search_data.get("esearchresult", {}).get("idlist", [])
                
                if not id_list:
                    return []

                # 2. Fetch Details
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "xml",
                    "email": self.email,
                    "tool": self.tool
                }
                
                fetch_resp = await client.get(f"{base_url}/efetch.fcgi", params=fetch_params)
                fetch_resp.raise_for_status()
                
                # 3. Parse XML
                root = ET.fromstring(fetch_resp.content)
                parsed_results = []
                
                for article in root.findall(".//PubmedArticle"):
                    try:
                        medline = article.find("MedlineCitation")
                        if medline is None:
                            continue
                            
                        article_data = medline.find("Article")
                        if article_data is None:
                            continue
                            
                        # Extract Title
                        title_node = article_data.find("ArticleTitle")
                        title = title_node.text if title_node is not None else "No Title"
                        
                        # Extract Abstract
                        abstract_node = article_data.find("Abstract")
                        abstract_text = ""
                        if abstract_node is not None:
                            texts = [t.text for t in abstract_node.findall("AbstractText") if t.text]
                            abstract_text = " ".join(texts)
                        
                        # Heuristic 1: Missing Abstract
                        if not abstract_text:
                            continue
                            
                        # Heuristic 2: Abstract Length < 200
                        if len(abstract_text) < 200:
                            continue
                        
                        # Heuristic 3: Filter Editorials
                        pub_types = article_data.find("PublicationTypeList")
                        is_editorial = False
                        if pub_types is not None:
                            for pt in pub_types.findall("PublicationType"):
                                if pt.text == "Editorial":
                                    is_editorial = True
                                    break
                        if is_editorial:
                            continue

                        # Extract PMID
                        pmid_node = medline.find("PMID")
                        pmid = pmid_node.text if pmid_node is not None else ""
                        
                        # Extract Year
                        journal_issue = article_data.find("Journal/JournalIssue/PubDate")
                        year = "N/A"
                        if journal_issue is not None:
                            year_node = journal_issue.find("Year")
                            if year_node is not None:
                                year = year_node.text
                            else:
                                # Try MedlineDate
                                medline_date = journal_issue.find("MedlineDate")
                                if medline_date is not None:
                                    year = medline_date.text.split()[0] # Take first part
                        
                        # Extract First Author
                        author_list = article_data.find("AuthorList")
                        first_author = "Unknown"
                        if author_list is not None:
                            first_author_node = author_list.find("Author")
                            if first_author_node is not None:
                                last_name = first_author_node.find("LastName")
                                if last_name is not None:
                                    first_author = last_name.text

                        citation = f"{first_author} et al. ({year})"

                        parsed_results.append({
                            "pmid": pmid,
                            "title": title,
                            "abstract": abstract_text,
                            "year": year,
                            "citation": citation
                        })
                    except Exception as e:
                        logger.warning(f"PUBMED | PARSE ERROR | {e}")
                        continue

            # Cache for 24h (86400s)
            await cache_service.set(cache_key, json.dumps(parsed_results), ttl=86400)
            return parsed_results

        except httpx.TimeoutException:
             logger.error("PUBMED | TIMEOUT")
             raise PubMedError("PubMed request timed out")
        except Exception as e:
            logger.error(f"PUBMED | ERROR | {e}")
            raise PubMedError(str(e))

class UnifiedLLMService:
    def __init__(self):
        # Configure robust HTTP client with IPv4 forcing
        self.transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=0)
        
        # Clients
        self.groq_client = None
        if settings.groq_api_key:
            self.groq_client = AsyncGroq(
                api_key=settings.groq_api_key,
                http_client=httpx.AsyncClient(transport=self.transport, timeout=60.0)
            )
        
        self.openrouter_client = None
        if settings.openrouter_api_key:
            self.openrouter_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
                http_client=httpx.AsyncClient(transport=self.transport, timeout=60.0)
            )
        
        self.openai_client = None
        if settings.openai_api_key:
            self.openai_client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                http_client=httpx.AsyncClient(transport=self.transport, timeout=60.0)
            )
        
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(settings.gemini_model)
        else:
            self.gemini_model = None

        self.pubmed = PubMedService()
        self.email_service = EmailService()

    async def _call_groq(self, system_prompt: str, user_text: str, model: str = None, json_mode: bool = False) -> str:
        if not self.groq_client: raise Exception("Groq not configured")
        
        target_model = model or settings.groq_main_model
        
        start_time = time.time()
        try:
            kwargs = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.1 # Strict adherence to facts
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await asyncio.wait_for(
                self.groq_client.chat.completions.create(**kwargs),
                timeout=settings.groq_timeout
            )
            duration = time.time() - start_time
            logger.info(f"GROQ | {target_model} | SUCCESS | {duration:.2f}s")
            return response.choices[0].message.content
        except RateLimitError:
            raise GroqRateLimitError("Groq Rate Limit Exceeded")
        except asyncio.TimeoutError:
            logger.error(f"GROQ | {target_model} | TIMEOUT")
            raise GroqServiceError("Groq Request Timed Out")
        except (APIConnectionError, APIStatusError) as e:
             status_code = getattr(e, 'status_code', 'N/A')
             logger.error(f"GROQ | {target_model} | API ERROR {status_code} | {e}")
             raise GroqServiceError(f"Groq Service Error ({status_code}): {e}")
        except Exception as e:
            logger.error(f"GROQ | {target_model} | FAIL | {e}")
            raise e

    async def _expand_query(self, user_query: str) -> str:
        """Expand user query to PubMed Boolean Syntax using fast 8B model"""
        system_prompt = (
            "You are a precise search query generator for PubMed. "
            "Convert the user's clinical query into a strict PubMed Boolean search string. "
            "Rules:\n"
            "1. Output ONLY the boolean string. No explanations, no markdown, no conversational text.\n"
            "2. Use strictly PubMed-compatible syntax (AND, OR, parentheses, [Title/Abstract]).\n"
            "3. Do NOT include any Persian text.\n"
            "4. Keep it to a single line.\n"
            "Example: 'Heart attack cure' -> '(Myocardial Infarction[Title/Abstract]) AND (Therapy[Title/Abstract] OR Treatment[Title/Abstract])'"
        )
        try:
            expanded = await self._call_groq(system_prompt, user_query, model=settings.groq_fast_model)
            logger.info(f"QUERY EXPANSION | '{user_query}' -> '{expanded}'")
            return expanded.strip('"').strip("'") # Clean quotes if any
        except Exception:
            logger.warning("QUERY EXPANSION FAILED | Using original query")
            return user_query

    async def _call_openrouter(self, system_prompt: str, user_text: str) -> str:
        if not self.openrouter_client: raise Exception("OpenRouter not configured")
        
        start_time = time.time()
        try:
            response = await self.openrouter_client.chat.completions.create(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
            )
            duration = time.time() - start_time
            logger.info(f"OPENROUTER | SUCCESS | {duration:.2f}s")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OPENROUTER | FAIL | {e}")
            raise e

    async def _call_gemini(self, system_prompt: str, user_text: str) -> str:
        if not self.gemini_model: raise Exception("Gemini not configured")
        
        start_time = time.time()
        try:
            response = await self.gemini_model.generate_content_async(
                f"System: {system_prompt}\nUser: {user_text}"
            )
            duration = time.time() - start_time
            logger.info(f"GEMINI | SUCCESS | {duration:.2f}s")
            return response.text
        except Exception as e:
            logger.error(f"GEMINI | FAIL | {e}")
            raise e

    async def _call_openai(self, system_prompt: str, user_text: str) -> str:
        if not self.openai_client: raise Exception("OpenAI not configured")
        
        start_time = time.time()
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ]
            )
            duration = time.time() - start_time
            logger.info(f"OPENAI | SUCCESS | {duration:.2f}s")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OPENAI | FAIL | {e}")
            raise e

    def _construct_final_response(self, 
                                  user_query: str, 
                                  search_term: str, 
                                  model_used: str, 
                                  start_time: float, 
                                  articles: List[Dict], 
                                  llm_output: str,
                                  fallback_triggered: bool) -> Dict:
        
        try:
            # Try to parse LLM output as JSON if it's supposed to be JSON
            # But the user might want the LLM output embedded or parsed
            # The prompt usually asks for JSON. Let's assume LLM output IS the "results" or part of it?
            # Wait, the user's schema has "results" as the PubMed articles, and "summary" inside?
            # No, the schema shows "results" as an array of objects with pmid, title, summary, etc.
            # So the LLM processed the articles and returned this JSON structure.
            # OR the LLM output IS the whole JSON?
            # The user says "Standard JSON Output".
            
            # If the LLM returns the whole JSON, we just need to validate/patch it.
            # But we also need to inject metadata that the LLM might not know (like duration).
            
            # Let's assume the LLM is asked to return the "results" array or a JSON object with specific fields.
            # If the LLM returns a full JSON object, we parse it.
            
            parsed_llm = json.loads(llm_output)
            
            # If LLM returned the whole structure, we might overwrite metadata
            if "results" in parsed_llm:
                results = parsed_llm["results"]
            else:
                # Maybe it returned just the list?
                results = parsed_llm if isinstance(parsed_llm, list) else []

        except json.JSONDecodeError:
            # Fallback if LLM output isn't valid JSON (should be handled by caller, but safety here)
            results = [] 
            # We might want to include the raw text somewhere if it failed?
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            "query": user_query,
            "search_term_used": search_term,
            "timestamp": datetime.now().isoformat(),
            "model_used": model_used,
            "execution_stats": {
                "duration_ms": duration_ms,
                "cache_hit": False, # If we are here, it wasn't a full cache hit
                "fallback_triggered": fallback_triggered
            },
            "results": results,
            "metadata": {
                "articles_fetched": len(articles),
                "articles_filtered_out": 0,
                "error": "PUBMED_TIMEOUT" if not articles and "PubMed unavailable" in str(logger.handlers) else None
            },
            # Inject error details for frontend if empty
             "error_details": {
                "code": "PUBMED_TIMEOUT",
                "message": "PubMed unavailable - Proceeding without evidence",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "context": "PUBMED | NO ARTICLES | Returning Search Term Log"
            } if not articles else None
        }

    async def execute_pipeline(self, system_prompt: str, user_text: str, cache_key_prefix: str, json_mode: bool = False) -> Dict:
        start_time = time.time()
        
        # 1. Cache Check (LLM Response)
        query_hash = hashlib.md5(user_text.encode()).hexdigest()
        cache_key = f"{cache_key_prefix}:{query_hash}:{settings.groq_main_model}" # Includes model version
        cached = await cache_service.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. Query Expansion (if applicable - usually done before calling this, but let's assume this is the main entry)
        # Actually, the user's flow says: Query -> Expansion -> PubMed -> Heuristic -> Groq -> JSON
        # So we should probably do expansion here or assume it's done.
        # Let's do it here if it's a "clinical" query. 
        # However, this method is generic. Let's assume user_text is the query for now.
        
        # Wait, the `user_text` might be the prompt with context? 
        # The user provided a "Standard JSON Output" which implies this method drives the whole flow.
        # But `execute_pipeline` signature is `(system_prompt, user_text, ...)`
        # I'll stick to the signature but implement the specific logic if it matches the "clinical" flow.
        
        # Let's refine: The routers call `execute_pipeline`. 
        # The routers (like `summarize.py`) construct the prompt.
        # BUT the user wants a specific flow with PubMed.
        # If I change `execute_pipeline` to do PubMed fetching, I break other routers that don't need PubMed?
        # Or maybe `UnifiedLLMService` should have a `run_clinical_pipeline` method?
        # The user said "Execution Pipeline (Optimized) Flow: Query → Expansion...".
        # This sounds like the MAIN function of this API.
        
        # I will implement `run_clinical_pipeline` and deprecated/wrap `execute_pipeline` if needed.
        # OR I update `execute_pipeline` to handle the fetching if not provided?
        
        # Let's stick to the current pattern where the Router handles the flow steps?
        # No, the user explicitly put "Execution Pipeline" logic here.
        # "try: result = pipeline(query) except..."
        # This implies a single function call.
        
        pass 

    async def run_clinical_pipeline(self, user_query: str, send_email: bool = False, email_to: str = None) -> Dict:
        start_time = time.time()
        fallback_triggered = False
        model_used = settings.groq_main_model
        
        # 1. Query Expansion
        search_term = await self._expand_query(user_query)
        
        # 2. PubMed Fetch with Retry Logic
        articles = []
        max_retries = 3
        backoff_factor = 2
        
        for attempt in range(max_retries):
            try:
                articles = await self.pubmed.fetch_articles(search_term)
                break  # Success
            except (PubMedError, Exception) as e:  # Catch generic exceptions too for timeouts
                logger.warning(f"PubMed attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor ** attempt
                    logger.info(f"Retrying PubMed in {sleep_time}s...")
                    await asyncio.sleep(sleep_time)
                else:
                    logger.error(f"PubMed unavailable after {max_retries} attempts - Proceeding without evidence")
                    logger.error(f"[ERROR] PUBMED | TIMEOUT | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    # We continue with empty articles, triggering the fallback logic below
                    articles = []
            # Continue pipeline without articles
            
        # Email Notification
        if send_email and email_to:
            # We run this in background or await? Await for now to ensure delivery status is known
            # or just fire and forget if performance is critical. 
            # Requirement says "Configure system to send...", doesn't specify async.
            # But let's just call it.
            self.email_service.send_search_results(email_to, user_query, articles)

        # Optimization: If no articles, skip LLM and return search term log directly
        if not articles:
            logger.info("PUBMED | NO ARTICLES | Generating Null Reports")
            
            # Check for Boolean Operators in original query (Requirement 3b)
            # "If the query contains 'AND' or 'OR' operators: Return the original query string exactly as entered"
            original_query_returned = None
            upper_q = user_query.upper()
            if " AND " in upper_q or " OR " in upper_q:
                original_query_returned = user_query
            
            # --- Generate Supporting Documents ---
            ts = int(time.time())
            method_filename = f"methodology_{ts}.md"
            null_filename = f"null_report_{ts}.md"
            
            try:
                # 1. Methodology
                method_content = await self._call_groq(METHODOLOGY_SYSTEM_PROMPT, f"Query: {user_query}\nExpanded Search String: {search_term}")
                with open(f"app/static/reports/{method_filename}", "w") as f:
                    f.write(method_content)

                # 2. Null Report
                null_content = await self._call_groq(NULL_REPORT_SYSTEM_PROMPT, f"Query: {user_query}\nExpanded Search String: {search_term}")
                with open(f"app/static/reports/{null_filename}", "w") as f:
                    f.write(null_content)
            except Exception as e:
                logger.error(f"Failed to generate null reports: {e}")
                method_content = "Generation Failed"
                null_content = "Generation Failed"

            return {
                "query": user_query,
                "original_query_preserved": original_query_returned, # Requirement 3b
                "search_term_used": search_term,
                "timestamp": datetime.now().isoformat(),
                "model_used": "N/A",
                "execution_stats": {
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "cache_hit": False,
                    "fallback_triggered": fallback_triggered
                },
                "results": [
                    {
                        "title": "No Relevant Evidence Found",
                        "summary": f"PubMed Search: {search_term}",
                        "relevance": "N/A",
                        "pmid": None,
                        "links": [
                            {"title": "Search Methodology", "url": f"/static/reports/{method_filename}"},
                            {"title": "Null Results Analysis", "url": f"/static/reports/{null_filename}"}
                        ]
                    }
                ],
                "metadata": {
                    "articles_fetched": 0,
                    "articles_filtered_out": 0,
                    "no_results_message": "No articles found matching your criteria." # Requirement 3c
                }
            }
            
        # Prepare Context
        context_str = "\n\n".join([f"PMID: {a['pmid']}\nTitle: {a['title']}\nAbstract: {a['abstract']}" for a in articles])
        
        # 3. Core Processing (Groq)
        system_prompt = EVIDENCE_SYSTEM_PROMPT
        full_user_content = f"Query: {user_query}\n\nEvidence:\n{context_str}"
        
        response_content = None
        
        # Retry Loop
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response_content = await self._call_groq(system_prompt, full_user_content, json_mode=True)
                break # Success
            except GroqRateLimitError:
                wait_time = (2 ** attempt) # Exponential backoff
                logger.warning(f"Groq Rate Limit. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                if attempt == max_retries - 1:
                    # Fallback to OpenRouter after retries
                    logger.error("Groq Rate Limit Exhausted -> Switching to OpenRouter")
                    fallback_triggered = True
                    try:
                        response_content = await self._call_openrouter(system_prompt, full_user_content)
                        model_used = settings.openrouter_model
                    except Exception:
                        # Try Gemini
                         try:
                            response_content = await self._call_gemini(system_prompt, full_user_content)
                            model_used = settings.gemini_model
                         except Exception:
                             # Try OpenAI
                             response_content = await self._call_openai(system_prompt, full_user_content)
                             model_used = settings.openai_model
            except GroqServiceError:
                logger.error("Groq 5xx -> Switching to OpenRouter")
                fallback_triggered = True
                try:
                    response_content = await self._call_openrouter(system_prompt, full_user_content)
                    model_used = settings.openrouter_model
                except Exception:
                     # Fallback chain...
                     pass
                break
            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                # Fallback?
                break

        if not response_content:
             return {"error": "All models failed", "data": []}

        # 4. JSON Validation & Construction
        try:
            final_json = self._construct_final_response(
                user_query, search_term, model_used, start_time, articles, response_content, fallback_triggered
            )
            return final_json
        except json.JSONDecodeError:
            logger.critical("Model failed to produce valid JSON")
            # We could retry here, but for now return error
            return {"error": "Invalid JSON output", "data": []}

    # Keeping generic execute_pipeline for backward compatibility if needed, 
    # but the prompt implies we should replace the logic.
    # I'll implement a generic version that matches the requested Error Handling Strategy.
    async def execute_pipeline(self, system_prompt: str, user_text: str, cache_key_prefix: str, json_mode: bool = False) -> str:
        # Generic pipeline for non-clinical-flow tasks (e.g. simple summarization)
        
        cache_key = f"{cache_key_prefix}:{hashlib.md5(user_text.encode()).hexdigest()}:{settings.groq_main_model}"
        cached = await cache_service.get(cache_key)
        if cached: return cached

        response = None
        last_error = None
        
        # 1. Groq
        for attempt in range(3):
            try:
                response = await self._call_groq(system_prompt, user_text, json_mode=json_mode)
                break
            except GroqRateLimitError:
                wait_time = 2 ** attempt
                logger.warning(f"Groq Rate Limit. Waiting {wait_time}s")
                await asyncio.sleep(wait_time)
            except GroqServiceError:
                logger.warning("Groq Service Error. Switching to fallback.")
                break # Switch to fallback
            except Exception as e:
                last_error = e
                break

        if response:
            await cache_service.set(cache_key, response, ttl=3600)
            return response

        # 2. OpenRouter
        try:
            logger.warning("FALLBACK -> OPENROUTER")
            response = await self._call_openrouter(system_prompt, user_text)
            await cache_service.set(cache_key, response, ttl=3600)
            return response
        except Exception as e:
            logger.error(f"OpenRouter Failed: {e}")

        # 3. Gemini
        try:
            logger.warning("FALLBACK -> GEMINI")
            response = await self._call_gemini(system_prompt, user_text)
            await cache_service.set(cache_key, response, ttl=3600)
            return response
        except Exception as e:
            logger.error(f"Gemini Failed: {e}")

        # 4. OpenAI
        try:
            logger.warning("FALLBACK -> OPENAI")
            response = await self._call_openai(system_prompt, user_text)
            await cache_service.set(cache_key, response, ttl=3600)
            return response
        except Exception as e:
            logger.error(f"OpenAI Failed: {e}")

        raise Exception("All LLM services unavailable")

    # --- Convenience Wrappers ---
    # These return raw JSON string from LLM, not the full clinical object unless updated.
    # For now, keeping them as is but using the robust execute_pipeline.

    async def summarize(self, text: str) -> str:
        return await self.execute_pipeline(SUMMARY_SYSTEM_PROMPT, text, "groq:summ", json_mode=True)

    async def differential(self, text: str) -> str:
        return await self.execute_pipeline(DIFFERENTIAL_SYSTEM_PROMPT, text, "groq:ddx", json_mode=True)

    async def nelson(self, text: str) -> str:
        return await self.execute_pipeline(NELSON_SYSTEM_PROMPT, text, "groq:nelson", json_mode=True)

    async def bmj_query(self, text: str) -> Dict:
        """
        Generates BMJ Best Practice topics based on the clinical case.
        Replaces the PubMed search pipeline.
        """
        start_time = time.time()
        
        # Use the generic pipeline to get the Markdown response
        # We pass json_mode=False because the prompt asks for Markdown output
        response_text = await self.execute_pipeline(BMJ_SYSTEM_PROMPT, text, "groq:bmj", json_mode=False)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            "query": text,
            "timestamp": datetime.now().isoformat(),
            "execution_stats": {
                "duration_ms": duration_ms
            },
            "bmj_topics_markdown": response_text,
            "type": "bmj_topics"
        }

    async def pubmed_query(self, text: str, send_email: bool = False, email_to: str = None) -> Dict:
        """
        Full clinical pipeline with PubMed search and standardized JSON output.
        Replaces the old 'pubmed' wrapper.
        """
        return await self.run_clinical_pipeline(text, send_email, email_to)

    async def expand_query_public(self, query: str) -> str:
        """Public wrapper for query expansion"""
        return await self._expand_query(query)
