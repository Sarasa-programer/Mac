import requests
import sys
import os

# Configuration
BASE_URL = "http://localhost:8000/api/v1/cases"
TEST_FILE_PATH = "test_video.mp4"

def create_dummy_mp4_if_not_exists():
    """Creates a dummy MP4 file if it doesn't exist."""
    if not os.path.exists(TEST_FILE_PATH):
        print(f"Creating dummy file: {TEST_FILE_PATH}")
        with open(TEST_FILE_PATH, "w") as f:
            f.write("This is a dummy MP4 file content for testing upload endpoint.")
    else:
        print(f"Using existing file: {TEST_FILE_PATH}")

def upload_and_analyze_case():
    """Uploads an MP4 file and triggers analysis."""
    
    # 1. Upload File
    print(f"\n🚀 Step 1: Uploading {TEST_FILE_PATH}...")
    try:
        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": (TEST_FILE_PATH, f, "video/mp4")}
            response = requests.post(f"{BASE_URL}/upload", files=files)
            
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return
            
        case_data = response.json()
        case_id = case_data["id"]
        print(f"✅ Upload successful! Case ID: {case_id}")
        
    except Exception as e:
        print(f"❌ Error during upload: {e}")
        return

    # 2. Analyze Case (Trigger AI)
    # We prefer Groq for MP4 transcription as per logic
    print(f"\n🚀 Step 2: Triggering Analysis for Case {case_id}...")
    try:
        # Note: The server defaults to "openai" provider, but our internal logic
        # should route transcription to Groq automatically for files.
        # However, to be explicit, we can ask for 'groq' or let it fallback.
        # Let's use 'openai' (default) and verify if the backend router 
        # correctly switches to Groq for transcription as designed.
        analyze_url = f"{BASE_URL}/{case_id}/analyze"
        
        # Using 'gemini' as preferred provider for summarization as requested
        params = {"provider": "gemini"} 
        
        response = requests.post(analyze_url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Analysis Result:")
            print("-" * 30)
            print(f"Title: {result.get('title')}")
            print(f"Provider: {result.get('provider')}")
            print(f"Summary: {result.get('summary')}")
            print("-" * 30)
        else:
            print(f"❌ Analysis failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == "__main__":
    create_dummy_mp4_if_not_exists()
    upload_and_analyze_case()
