import pytest
import os
import shutil
from fastapi.testclient import TestClient
from app.main import app

# Create uploads dir for testing
if not os.path.exists("uploads"):
    os.makedirs("uploads")

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

def test_upload_audio():
    # Create a dummy file
    with open("test_audio.mp3", "wb") as f:
        f.write(b"dummy audio content")
    
    with open("test_audio.mp3", "rb") as f:
        response = client.post(
            "/api/v1/upload-audio",
            files={"file": ("test_audio.mp3", f, "audio/mpeg")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert "file_path" in data
    
    # Cleanup
    os.remove("test_audio.mp3")

def test_transcribe():
    # Mock upload for transcribe
    with open("test_audio.mp3", "wb") as f:
        f.write(b"dummy audio content")
        
    with open("test_audio.mp3", "rb") as f:
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test_audio.mp3", f, "audio/mpeg")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "language" in data
    
    os.remove("test_audio.mp3")

def test_summarize():
    payload = {"text": "Patient has fever and rash."}
    response = client.post("/api/v1/summarize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "chief_complaint" in data

def test_differential_dx():
    payload = {"text": "Fever, strawberry tongue, conjunctivitis."}
    response = client.post("/api/v1/differential-dx", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "diagnoses" in data
    assert isinstance(data["diagnoses"], list)

def test_nelson_section():
    payload = {"keywords": ["Kawasaki", "Fever"]}
    response = client.post("/api/v1/nelson-section", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "source" in data

def test_pubmed_search():
    payload = {"keywords": ["Kawasaki", "Treatment"]}
    response = client.post("/api/v1/pubmed-search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert len(data["articles"]) > 0

def test_keywords():
    payload = {"text": "Case description here."}
    response = client.post("/api/v1/keywords", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "keywords" in data

def test_cases_crud():
    # List cases
    response = client.get("/api/v1/cases/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

if __name__ == "__main__":
    # If run directly, run pytest
    import sys
    sys.exit(pytest.main(["-v", "backend/tests/load_test.py"]))
