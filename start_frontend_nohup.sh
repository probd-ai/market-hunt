#!/bin/bash

# Start Frontend Next.js Server in nohup mode
echo "Starting Market Hunt Frontend Server..."

# Change to frontend directory
cd /media/guru/Data/workspace/market-hunt/frontend

# Check if node_modules exists, install if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start the frontend in development mode
echo "Starting frontend in development mode..."
nohup npm run dev > ../frontend.log 2>&1 &

# Get the process ID
FRONTEND_PID=$!
echo "Frontend Server started with PID: $FRONTEND_PID"
echo $FRONTEND_PID > ../frontend.pid

# Display startup message
echo "Frontend Server is running in background on port 3000"
echo "Access: http://localhost:3000"
echo "Logs: tail -f frontend.log"
echo "Stop: kill \$(cat frontend.pid)"
