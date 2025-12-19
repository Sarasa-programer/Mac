from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from fastapi.middleware.cors import CORSMiddleware
from src.api.api import api_router
from src.config.settings import settings
from src.infrastructure.db.session import init_db
from app.routers import summarize, differential, nelson, pubmed, pediatric

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title=settings.PROJECT_NAME)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    try:
        body = await request.json()
        # Log truncated body to avoid huge logs
        logger.error(f"Request body causing error: {str(body)[:1000]}...") 
    except Exception:
        logger.error("Could not read request body")
    
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(summarize.router)
app.include_router(differential.router)
app.include_router(nelson.router)
app.include_router(pubmed.router)
app.include_router(pediatric.router)

@app.get("/")
def root():
    return {"message": "Welcome to Pediatric Morning Report AI API"}

@app.get("/health")
def health_check():
    return {"status": "running"}
