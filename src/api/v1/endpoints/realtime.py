import asyncio
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.infrastructure.ai.buffer_manager import BufferManager
from src.infrastructure.ai.groq_service import GroqService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    
    # Queue for decoupling audio reception from processing
    queue = asyncio.Queue()
    
    async def process_audio():
        buffer_manager = BufferManager()
        groq_service = GroqService()
        last_transcription = ""
        
        try:
            while True:
                data = await queue.get()
                if data is None:  # Sentinel to stop
                    break
                
                # Check queue backlog
                qsize = queue.qsize()
                if qsize > 10:
                    logger.warning(f"Audio processing queue backlog: {qsize} items")
                    
                try:
                    window_payload = buffer_manager.add_audio(data)
                    
                    if window_payload:
                        logger.info(f"Processing window: {len(window_payload)} bytes")
                        
                        start_time = asyncio.get_running_loop().time()
                        
                        # Process audio without blocking the receive loop
                        new_text = await groq_service.transcribe(
                            window_payload, 
                            prompt=last_transcription
                        )
                        
                        duration = asyncio.get_running_loop().time() - start_time
                        if duration > 2.0:
                            logger.info(f"Groq transcription took {duration:.2f}s")
                        
                        if new_text:
                            logger.info(f"Transcribed: {new_text}")
                            last_transcription = new_text
                            
                            await websocket.send_json({
                                "type": "transcription",
                                "text": new_text,
                                "partial": False
                            })
                except Exception as e:
                    logger.error(f"Error in processing audio chunk: {e}")
                    if "403" in str(e) or "Forbidden" in str(e):
                         logger.critical("🛑 Groq Permission Denied. Stopping audio processing to prevent ban.")
                         # Optionally inform client
                         try:
                             await websocket.send_json({"type": "error", "message": "Transcription Service Unavailable (403)"})
                         except:
                             pass
                         break # Stop processing loop
                    # Don't crash the loop on other processing errors (like network blip)
                    
                finally:
                    queue.task_done()
        except asyncio.CancelledError:
            logger.info("Audio processor task cancelled")
            raise

    # Start the processor task
    processor_task = asyncio.create_task(process_audio())
    
    try:
        while True:
            # 1. Receive Audio Chunk (Bytes)
            data = await websocket.receive_bytes()
            # 2. Put into queue immediately
            await queue.put(data)
            
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
    finally:
        # Cleanup
        await queue.put(None)  # Signal processor to stop
        try:
            # Wait for processor to finish pending items with a timeout
            await asyncio.wait_for(processor_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Processor task timed out during cleanup")
            processor_task.cancel()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
        try:
            await websocket.close()
        except:
            pass
