#!/bin/bash

# Function to kill all background jobs on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM EXIT

echo "🚀 Starting MDapi001 Services..."

# 1. Start Infrastructure (Redis) if Docker is available
if command -v docker >/dev/null 2>&1; then
    if [ -f "docker-compose.yml" ]; then
        echo "🐳 Starting Redis via Docker..."
        docker-compose up -d redis
    fi
else
    echo "⚠️ Docker not found. Redis caching might fail if not running locally."
fi

# 2. Start Backend
echo "🐍 Starting Backend (FastAPI)..."
# Using root .venv if exists, or creating one
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing backend dependencies..."
    pip install -r backend/requirements.txt
else
    source .venv/bin/activate
fi

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Port 8000 is already in use. Attempting to kill..."
    kill $(lsof -Pi :8000 -sTCP:LISTEN -t) 2>/dev/null
    sleep 1
fi

# Run uvicorn in background from ROOT directory
# Because src/ is at root
export PYTHONPATH=$PYTHONPATH:.
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a bit for backend to initialize
sleep 3

# 3. Start Frontend
echo "⚛️ Starting Frontend (Vite)..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Check if port 5173 is in use (default vite port)
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Port 5173 is already in use. Vite will likely pick the next available port."
fi

npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ All services started!"
echo "   Backend API: http://localhost:8000/docs"
echo "   Frontend App: http://localhost:5173"
echo "   (Press Ctrl+C to stop)"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
