from fastapi import APIRouter
from src.api.v1.endpoints import auth, cases, analysis, audio, realtime, tasks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(realtime.router, tags=["realtime"]) # WebSocket router has its own path /ws/realtime
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
