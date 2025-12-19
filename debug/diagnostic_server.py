import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DiagnosticServer")

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")
    
    try:
        total_bytes = 0
        while True:
            # We try to receive bytes (assuming client sends Blob/ArrayBuffer)
            # If client sends text, this might fail or we should handle it.
            message = await websocket.receive()
            
            if "bytes" in message:
                data = message["bytes"]
                size = len(data)
                total_bytes += size
                logger.info(f"Received {size} bytes. Total: {total_bytes}")
                await websocket.send_text(f"Ack: {size} bytes")
                
                # Check for header (simple heuristic for WebM/WAV)
                if total_bytes == size: # First chunk
                    header = data[:4].hex()
                    logger.info(f"First chunk header (hex): {header}")
                    # WebM usually starts with 1a45dfa3
                    # RIFF/WAV starts with 52494646
            
            elif "text" in message:
                logger.info(f"Received text: {message['text']}")
                await websocket.send_text(f"Ack: Text received")
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    # Run standalone: python debug/diagnostic_server.py
    print("Starting Diagnostic Server on ws://localhost:8001/ws")
    uvicorn.run(app, host="0.0.0.0", port=8001)
