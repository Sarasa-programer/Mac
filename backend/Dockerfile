# syntax=docker/dockerfile:1

# --- Builder stage ---
FROM python:3.13-slim AS builder
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

# --- Runtime stage ---
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy backend source
COPY backend/app ./app
COPY backend/sql_app.db ./sql_app.db
COPY backend/requirements.txt ./requirements.txt

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

