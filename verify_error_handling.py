import asyncio
import os
import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_AUDIO_FILE = "uploads/test_audio.mp3"

def create_dummy_audio():
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    # This is invalid audio content, which should trigger a provider error
    with open(TEST_AUDIO_FILE, "wb") as f:
        f.write(b"dummy audio content")

def test_error_handling():
    print("\n🧪 Testing Error Handling (Invalid Audio File)...")
    
    # 1. Test Direct Transcription Error
    print("\n[1] Testing /audio/transcribe with invalid file...")
    with open(TEST_AUDIO_FILE, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/audio/transcribe",
            files={"file": f},
            data={"provider": "groq", "language": "fa"}
        )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    # Validation Logic
    if response.status_code == 500: # Currently returns 500 on unhandled exception
         print("✅ Received expected error status (500/400)")
         if "could not process file" in response.text or "Error code: 400" in response.text:
             print("✅ Error message confirms validation failure from provider")
         else:
             print("⚠️ Unexpected error message format")
    else:
        print(f"❌ Unexpected status code: {response.status_code}")

    # 2. Test Async Pipeline Error Propagation
    print("\n[2] Testing /audio/analyze with invalid file...")
    with open(TEST_AUDIO_FILE, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/audio/analyze",
            files={"file": f}
        )
    
    if response.status_code == 200:
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ Job Started: {job_id}")
        
        # Poll for status
        for _ in range(10):
            time.sleep(1)
            status_res = requests.get(f"{BASE_URL}/audio/jobs/{job_id}")
            status_data = status_res.json()
            print(f"   Status: {status_data['status']}")
            
            if status_data["status"] == "failed":
                print(f"✅ Job correctly marked as failed")
                print(f"   Error Details: {status_data.get('error')}")
                return
            if status_data["status"] == "completed":
                print("❌ Job unexpectedly completed with invalid file")
                return
    else:
        print(f"❌ Pipeline Start Failed: {response.text}")

if __name__ == "__main__":
    create_dummy_audio()
    try:
        test_error_handling()
    except Exception as e:
        print(f"Test Execution Failed: {e}")
