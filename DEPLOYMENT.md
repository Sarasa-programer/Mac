# Deployment Playbook (Render)

## Prerequisites
- Render account
- GHCR (GitHub Container Registry) access
- Secrets: `OPENAI_API_KEY`, `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`

## Steps
- Build & push Docker image via GitHub Actions (see `.github/workflows/deploy.yml`).
- On Render, create a new Web Service:
  - Runtime: Docker
  - Image: `ghcr.io/<org>/pmr-backend:latest`
  - Port: `8000`
  - Health path: `/health`
  - Environment Variables:
    - `SECRET_KEY`
    - `ALGORITHM=HS256`
    - `ACCESS_TOKEN_EXPIRE_MINUTES=30`
    - `DATABASE_URL` (use PostgreSQL instance or SQLite file if ephemeral)
    - `OPENAI_API_KEY`
    - `REDIS_URL` (use Render Redis or external)

## Database
- Provision PostgreSQL on Render or use external managed Postgres.
- Set `DATABASE_URL` accordingly.

## Continuous Deployment
- On push to `main`, GitHub Actions builds and pushes the image.
- Render can auto-deploy when new image is available.

## CLI Snippets
```bash
# Local compose
docker-compose up -d --build

# Run container locally
docker build -t pmr-backend -f backend/Dockerfile .
docker run -e OPENAI_API_KEY=... -p 8000:8000 pmr-backend
```

