import sys
import httpx
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

def log(msg, status="INFO"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{status}] {msg}")

def run_verification():
    log("Starting End-to-End System Verification...")
    
    # 1. Health Check
    try:
        r = httpx.get(f"{BASE_URL}/health")
        if r.status_code == 200:
            log(f"Backend Health Check Passed: {r.json()}", "PASS")
        else:
            log(f"Backend Health Check Failed: {r.status_code}", "FAIL")
            sys.exit(1)
    except Exception as e:
        log(f"Backend Connection Failed: {e}", "FAIL")
        log("Make sure the backend server is running on localhost:8000", "HINT")
        sys.exit(1)

    # 2. Authentication (Login as Admin)
    token = None
    try:
        payload = {
            "username": "admin@example.com",
            "password": "password123"
        }
        r = httpx.post(f"{API_URL}/auth/login", data=payload)
        if r.status_code == 200:
            token = r.json().get("access_token")
            log("Authentication (Admin Login) Passed", "PASS")
        else:
            log(f"Authentication Failed: {r.status_code} - {r.text}", "FAIL")
            # Try to register if login fails (fallback logic similar to frontend)
            log("Attempting to register admin...", "INFO")
            reg_payload = {
                "email": "admin@example.com",
                "password": "password123",
                "full_name": "Admin User",
                "role": "admin"
            }
            r_reg = httpx.post(f"{API_URL}/auth/register", json=reg_payload)
            if r_reg.status_code in [200, 201]:
                log("Registration Successful, retrying login...", "INFO")
                r = httpx.post(f"{API_URL}/auth/login", data=payload)
                if r.status_code == 200:
                     token = r.json().get("access_token")
                     log("Authentication (After Register) Passed", "PASS")
                else:
                     log("Login failed after registration", "FAIL")
                     sys.exit(1)
            else:
                log(f"Registration Failed: {r_reg.status_code}", "FAIL")
                sys.exit(1)

    except Exception as e:
        log(f"Auth Request Error: {e}", "FAIL")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Unified Save (Simulate Realtime Flow)
    case_id = None
    try:
        # Matches CaseCreateFull schema
        case_payload = {
            "source": "realtime",
            "transcript": "This is a test transcript for verification.",
            "summary": {
                "chief_complaint": "Test Fever",
                "hpi": "History of present illness test.",
                "vitals": "T 38.5",
                "assessment": "Test Assessment",
                "plan": "Test Plan"
            },
            "differential_dx": [
                {"disease": "Test Disease A", "reasoning": "Reason A"},
                {"disease": "Test Disease B", "reasoning": "Reason B"}
            ],
            "nelson": [
                {"title": "Nelson Test", "chapter": "1", "recommendation": "Read this"}
            ],
            "pubmed": [
                {"title": "PubMed Test", "pmid": "12345", "link": "http://test.com"}
            ]
        }
        
        r = httpx.post(f"{API_URL}/cases/save", json=case_payload, headers=headers)
        if r.status_code == 201:
            data = r.json()
            case_id = data.get("id")
            log(f"Unified Save Endpoint (POST /cases/save) Passed. Case ID: {case_id}", "PASS")
        else:
            log(f"Unified Save Failed: {r.status_code} - {r.text}", "FAIL")
            sys.exit(1)

    except Exception as e:
        log(f"Save Request Error: {e}", "FAIL")
        sys.exit(1)

    # 4. Verify Persistence (Fetch List)
    try:
        r = httpx.get(f"{API_URL}/cases/", headers=headers)
        if r.status_code == 200:
            cases = r.json()
            found = any(c['id'] == case_id for c in cases)
            if found:
                log("Persistence Check (GET /cases) Passed: New case found in list.", "PASS")
            else:
                log("Persistence Check Failed: New case NOT found in list.", "FAIL")
        else:
            log(f"Fetch Cases Failed: {r.status_code}", "FAIL")
    except Exception as e:
        log(f"Fetch Request Error: {e}", "FAIL")

    # 5. Clean Up (Delete Case)
    if case_id:
        try:
            r = httpx.delete(f"{API_URL}/cases/{case_id}", headers=headers)
            if r.status_code == 204:
                log(f"Cleanup (DELETE /cases/{case_id}) Passed", "PASS")
            else:
                log(f"Cleanup Failed: {r.status_code}", "WARN")
        except Exception as e:
            log(f"Cleanup Error: {e}", "WARN")

    log("Verification Complete.", "INFO")

if __name__ == "__main__":
    run_verification()
