import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_response(response, tag):
    print(f"--- {tag} ---")
    print(f"Status: {response.status_code}")
    try:
        print(f"Body: {response.json()}")
    except:
        print(f"Body: {response.text}")
    print("----------------")
    if response.status_code >= 400:
        print("FAILED")
        sys.exit(1)

def main():
    # 1. Signup Professor
    prof_email = "prof@example.com"
    prof_pass = "password123"
    print(f"Registering Professor: {prof_email}")
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": prof_email,
        "password": prof_pass,
        "full_name": "Dr. House",
        "role": "professor"
    })
    if resp.status_code == 400 and "Email already registered" in resp.text:
        print("Professor already exists, logging in...")
    else:
        print_response(resp, "Signup Professor")

    # 2. Login Professor
    print("Logging in Professor...")
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": prof_email,
        "password": prof_pass
    })
    print_response(resp, "Login Professor")
    prof_token = resp.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}

    # 3. Create Case
    print("Creating Case...")
    case_data = {
        "title": "Test Case 1",
        "description": "A patient with unknown symptoms",
        "patient_age": 45,
        "patient_gender": "Male",
        "chief_complaint": "Headache",
        "difficulty_level": "medium",
        "category": "Neurology"
    }
    resp = requests.post(f"{BASE_URL}/cases/", json=case_data, headers=prof_headers)
    print_response(resp, "Create Case")
    case_id = resp.json()["id"]

    # 4. Signup Student
    student_email = "student@example.com"
    student_pass = "password123"
    print(f"Registering Student: {student_email}")
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": student_email,
        "password": student_pass,
        "full_name": "John Doe",
        "role": "student"
    })
    if resp.status_code == 400 and "Email already registered" in resp.text:
        print("Student already exists, logging in...")
    else:
        print_response(resp, "Signup Student")

    # 5. Login Student
    print("Logging in Student...")
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": student_email,
        "password": student_pass
    })
    print_response(resp, "Login Student")
    student_token = resp.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 6. Get Cases (Student)
    print("Getting Cases (Student)...")
    resp = requests.get(f"{BASE_URL}/cases/", headers=student_headers)
    print_response(resp, "Get Cases")

    # 7. Submit Answer (Student)
    print("Submitting Answer...")
    submission_data = {
        "case_id": case_id,
        "answer_text": "I think it is migraine."
    }
    resp = requests.post(f"{BASE_URL}/cases/{case_id}/submit", json=submission_data, headers=student_headers)
    print_response(resp, "Submit Answer")

    # 8. Get Submissions (Professor)
    print("Getting Submissions (Professor)...")
    resp = requests.get(f"{BASE_URL}/cases/{case_id}/submissions", headers=prof_headers)
    print_response(resp, "Get Submissions")
    
    # 9. Get My Submissions (Student)
    print("Getting My Submissions (Student)...")
    resp = requests.get(f"{BASE_URL}/cases/submissions/me", headers=student_headers)
    print_response(resp, "Get My Submissions")

if __name__ == "__main__":
    main()
