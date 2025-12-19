from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routers import summarize, differential, nelson, pubmed, audio, pediatric
from app.services.llm_service import UnifiedLLMService
import logging

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("MAIN")

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Create static directory if not exists
os.makedirs("app/static/reports", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # NOT ["*"]
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(summarize.router)
app.include_router(differential.router)
app.include_router(nelson.router)
app.include_router(pubmed.router)
app.include_router(audio.router)
app.include_router(pediatric.router)

@app.get("/health")
async def health_check():
    """Run before any pipeline execution"""
    try:
        # 1. Service Initialization Check
        llm_service = UnifiedLLMService()
        
        # 2. Check Groq (Simulated or Lightweight call)
        # Note: A real ping might consume credits/rate limit, so we check configuration + client readiness
        if not llm_service.groq_client:
             logger.error("Groq client not initialized")
             raise HTTPException(status_code=503, detail="Groq not configured")

        # 3. Check Fallbacks (Optional)
        status = {
            "status": "healthy",
            "groq": "configured",
            "openrouter": "configured" if llm_service.openrouter_client else "missing",
            "openai": "configured" if llm_service.openai_client else "missing",
            "gemini": "configured" if llm_service.gemini_model else "missing",
            "pubmed": "ready"
        }
        return status
    except Exception as e:
        logger.critical(f"HEALTH CHECK FAILED | {e}")
        raise HTTPException(status_code=503, detail=str(e))
