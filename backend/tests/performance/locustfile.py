import time
import uuid
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 2)
    token = None
    headers = {}

    def on_start(self):
        # Create a unique user
        self.email = f"user_{uuid.uuid4()}@example.com"
        self.password = "password123"
        
        # Signup - ignore error if user already exists (unlikely with uuid)
        self.client.post("/api/v1/auth/signup", json={
            "email": self.email,
            "password": self.password,
            "full_name": "Locust User",
            "role": "student"
        })
        
        # Login
        response = self.client.post("/api/v1/auth/login", data={
            "username": self.email,
            "password": self.password
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            print(f"Login failed for {self.email}: {response.text}")
    
    @task(3)
    def health_check(self):
        self.client.get("/health")
        
    @task(1)
    def get_cases(self):
        if self.token:
            self.client.get("/api/v1/cases/", headers=self.headers)
