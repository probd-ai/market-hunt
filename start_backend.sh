#!/bin/bash

# Start Backend API Server in nohup mode
echo "Starting Market Hunt Backend API Server..."

# Change to project directory
cd /media/guru/Data/workspace/market-hunt

# Activate virtual environment and start the backend
nohup /media/guru/Data/workspace/market-hunt/.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 3001 > backend.log 2>&1 &

# Get the process ID
BACKEND_PID=$!
echo "Backend API Server started with PID: $BACKEND_PID"
echo $BACKEND_PID > backend.pid

# Display startup message
echo "Backend API Server is running in background"
echo "Logs: tail -f backend.log"
echo "Stop: kill \$(cat backend.pid)"
