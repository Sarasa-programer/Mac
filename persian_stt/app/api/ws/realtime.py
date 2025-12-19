import asyncio
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.buffer_manager import BufferManager
from app.services.groq_service import GroqService
from app.services.vad_service import VADService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    
    buffer_manager = BufferManager()
    groq_service = GroqService()
    # VAD is used inside BufferManager, but we might need it here for logic control?
    # Actually BufferManager handles the accumulation. We just feed it.
    
    # Context State
    last_transcription = ""
    
    try:
        while True:
            # 1. Receive Audio Chunk (Bytes)
            data = await websocket.receive_bytes()
            
            # 2. Add to Buffer (Handles VAD & Windowing internally?)
            # Wait, BufferManager.add_audio just appends. 
            # We need to check if we should process.
            
            window_payload = buffer_manager.add_audio(data)
            
            # 3. If Window Ready -> Process
            if window_payload:
                logger.info(f"Processing window: {len(window_payload)} bytes")
                
                # Run Groq transcription in background (or await if we want strict ordering)
                # For real-time, await is safer to keep context sequential.
                new_text = await groq_service.transcribe(
                    window_payload, 
                    prompt=last_transcription
                )
                
                if new_text:
                    logger.info(f"Transcribed: {new_text}")
                    last_transcription = new_text # Update context
                    
                    # Send partial result
                    await websocket.send_json({
                        "type": "transcription",
                        "text": new_text,
                        "partial": False # It's a "final" for this window
                    })
            
            # 4. Optional: Handle VAD silence flush?
            # If buffer has data but VAD says silence for X seconds, flush it.
            # This logic needs a timer or check. 
            # For MVP, we rely on the window fill.
            
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        await websocket.close()
