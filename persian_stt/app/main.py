import logging
from fastapi import FastAPI
from app.core.config import get_settings
from app.api.ws import realtime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# Include WebSocket Router
app.include_router(realtime.router, prefix="/ws")

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME}...")
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set! processing will fail.")

@app.get("/")
async def root():
    return {"message": "Persian Real-time STT API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
