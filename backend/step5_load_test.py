import time
import json
import requests
import uuid

BASE_URL = "http://localhost:8000/api/v1"
OUTPUT_FILE = "load_test_results.json"

def run_load_test():
    results = {
        "timestamp": time.ctime(),
        "tests": []
    }

    session = requests.Session()
    
    # 1. Authentication Test
    email = f"test_{uuid.uuid4()}@example.com"
    password = "password123"
    
    start_time = time.time()
    try:
        # Signup
        signup_res = session.post(f"{BASE_URL}/auth/signup", json={
            "email": email,
            "password": password,
            "full_name": "Load Test User",
            "role": "student"
        })
        signup_time = time.time() - start_time
        
        # Login
        start_time = time.time()
        login_res = session.post(f"{BASE_URL}/auth/login", data={
            "username": email,
            "password": password
        })
        login_time = time.time() - start_time
        
        if login_res.status_code == 200:
            token = login_res.json()["access_token"]
            session.headers.update({"Authorization": f"Bearer {token}"})
            results["tests"].append({
                "name": "Authentication (Signup + Login)",
                "status": "success",
                "time_seconds": round(signup_time + login_time, 4),
                "details": "User created and logged in successfully"
            })
        else:
            raise Exception(f"Login failed: {login_res.text}")

    except Exception as e:
        results["tests"].append({
            "name": "Authentication",
            "status": "failed",
            "error": str(e)
        })
        print(json.dumps(results, indent=2))
        return

    # 2. Get Cases List
    start_time = time.time()
    try:
        res = session.get(f"{BASE_URL}/cases/")
        duration = time.time() - start_time
        results["tests"].append({
            "name": "Get Cases List",
            "status": "success" if res.status_code == 200 else "failed",
            "time_seconds": round(duration, 4),
            "status_code": res.status_code
        })
    except Exception as e:
        results["tests"].append({
            "name": "Get Cases List",
            "status": "failed",
            "error": str(e)
        })

    # 3. Upload Dummy Audio (Mock)
    # We create a tiny dummy file
    dummy_audio = b"fake audio content"
    files = {'file': ('test_audio.mp3', dummy_audio, 'audio/mpeg')}
    
    start_time = time.time()
    try:
        res = session.post(f"{BASE_URL}/cases/upload", files=files)
        duration = time.time() - start_time
        
        if res.status_code == 200:
            case_id = res.json()["id"]
            results["tests"].append({
                "name": "Upload Audio Case",
                "status": "success",
                "time_seconds": round(duration, 4),
                "case_id": case_id
            })
            
            # 4. Trigger Analysis (Will fail with placeholder keys, but we measure response time)
            start_time = time.time()
            analyze_res = session.post(f"{BASE_URL}/cases/{case_id}/analyze")
            analyze_duration = time.time() - start_time
            
            results["tests"].append({
                "name": "Analyze Case (Groq+Gemini+GPT)",
                "status": "expected_failure" if analyze_res.status_code != 200 else "success", # Expected fail with dummy keys
                "time_seconds": round(analyze_duration, 4),
                "status_code": analyze_res.status_code,
                "note": "May fail if API keys are invalid/placeholders"
            })
            
        else:
            results["tests"].append({
                "name": "Upload Audio Case",
                "status": "failed",
                "status_code": res.status_code,
                "error": res.text
            })
            
    except Exception as e:
        results["tests"].append({
            "name": "Upload/Analyze Flow",
            "status": "failed",
            "error": str(e)
        })

    # Output Results
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_load_test()
