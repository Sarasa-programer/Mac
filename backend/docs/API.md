# REST API Documentation (FastAPI + SQLAlchemy + SQLite)

Format: OpenAPI-like markdown for easy conversion to Swagger/ReDoc.

## Auth Endpoints

- Method/Route: `POST /api/v1/auth/signup`
  - Summary: Register a new user
  - Request: JSON body
    - Example:
      ```json
      { "email": "user@example.com", "password": "password123", "full_name": "User", "role": "student" }
      ```
  - Response:
    - 201 Success:
      ```json
      { "id": 1, "email": "user@example.com", "full_name": "User", "role": "student" }
      ```
    - 400 Error: Email already registered
  - Auth: Public
  - Controller: `backend/app/api/v1/endpoints/auth.py:57`

- Method/Route: `POST /api/v1/auth/login`
  - Summary: Login and get JWT token
  - Request: Form data
    - Example:
      - `username`: user@example.com
      - `password`: password123
  - Response:
    - 200 Success:
      ```json
      { "access_token": "<jwt>", "token_type": "bearer", "user": { "id": 1, "email": "user@example.com" } }
      ```
    - 401 Error: Incorrect email or password
  - Auth: Public
  - Controller: `backend/app/api/v1/endpoints/auth.py:85`

- Method/Route: `GET /api/v1/auth/me`
  - Summary: Get current user profile
  - Request: Bearer token
  - Response:
    - 200 Success: User profile
    - 401 Error: Unauthorized
  - Auth: JWT
  - Controller: `backend/app/api/v1/endpoints/auth.py:118`

## Case Endpoints

- Method/Route: `POST /api/v1/cases/`
  - Summary: Create a new case (professors only)
  - Request: JSON body `CaseCreate`
  - Response: 201 CaseResponse
  - Auth: JWT + role=professor
  - Controller: `backend/app/api/v1/endpoints/cases.py:32`

- Method/Route: `POST /api/v1/cases/upload`
  - Summary: Upload audio case file
  - Request: multipart/form-data with `file`
  - Response: 200 CaseResponse
  - Auth: JWT
  - Controller: `backend/app/api/v1/endpoints/cases.py:60`

- Method/Route: `GET /api/v1/cases/`
  - Summary: List cases with optional filters
  - Query: `skip`, `limit`, `category`, `difficulty`
  - Response: 200 `[CaseResponse]`
  - Auth: JWT
  - Controller: `backend/app/api/v1/endpoints/cases.py:84`

- Method/Route: `GET /api/v1/cases/{case_id}`
  - Summary: Get case details
  - Response: 200 CaseResponse, 404 if not found
  - Auth: JWT
  - Controller: `backend/app/api/v1/endpoints/cases.py:108`

- Method/Route: `PUT /api/v1/cases/{case_id}`
  - Summary: Update case (professors only)
  - Request: JSON body `CaseUpdate`
  - Response: 200 CaseResponse
  - Auth: JWT + role=professor
  - Controller: `backend/app/api/v1/endpoints/cases.py:125`

- Method/Route: `DELETE /api/v1/cases/{case_id}`
  - Summary: Delete case (professors only)
  - Response: 204 No Content
  - Auth: JWT + role=professor
  - Controller: `backend/app/api/v1/endpoints/cases.py:157`

- Method/Route: `POST /api/v1/cases/{case_id}/analyze`
  - Summary: Analyze case audio using Multi-AI Pipeline (Groq -> Gemini + GPT)
  - Request: Bearer token
  - Response:
    - 200 Success:
      ```json
      { "status": "success", "case_id": 1, "transcript_preview": "...", "keywords": ["fever"] }
      ```
    - 400 Error: Case has no audio
    - 404 Error: Case not found
    - 500 Error: Analysis failed
  - Auth: JWT
  - Controller: `backend/app/api/v1/endpoints/cases.py:177`

## Health Endpoint
- Method/Route: `GET /health`
  - Summary: Basic liveness probe
  - Response: 200
  - Auth: Public

## Realtime WebSocket

- Route: `GET /api/v1/realtime` (WebSocket upgrade)
  - Summary: Bidirectional channel for real-time audio transcription
  - Protocol: WebSocket (`ws://` or `wss://`)
  - Direction:
    - Client → Server: Binary audio chunks (16 kHz, 16-bit PCM)
    - Server → Client: JSON messages
      - Example:
        ```json
        {
          "type": "transcription",
          "text": "partial or full transcript",
          "partial": false
        }
        ```
  - Notes:
    - Intended for use by the RealTimeRecorder UI component
    - Requires the main API service to be reachable at `/api/v1`

## Schemas
- See `backend/app/schemas/case.py` and `backend/app/schemas/user.py`

## Notes
- Caching is implemented via Redis with cache-aside pattern.
- Responses may include deprecated fields; refer to schemas for current shape.
