#!/bin/bash

# Complete Market Hunt Application Startup Script
# Starts both backend and frontend in nohup mode

echo "=========================================="
echo "Starting Market Hunt Application"
echo "=========================================="

# Change to project directory
cd /media/guru/Data/workspace/market-hunt

# Make scripts executable
chmod +x start_backend.sh
chmod +x start_frontend_nohup.sh

echo ""
echo "1. Starting Backend API Server..."
echo "=========================================="
./start_backend.sh

# Wait a moment for backend to initialize
sleep 3

echo ""
echo "2. Starting Frontend Server..."
echo "=========================================="
./start_frontend_nohup.sh

echo ""
echo "=========================================="
echo "Market Hunt Application Started Successfully!"
echo "=========================================="
echo ""
echo "🔧 Backend API: http://localhost:3001"
echo "🌐 Frontend: http://localhost:3000"
echo ""
echo "📊 Monitoring:"
echo "  Backend Logs: tail -f backend.log"
echo "  Frontend Logs: tail -f frontend.log"
echo ""
echo "🛑 Stop Services:"
echo "  Backend: kill \$(cat backend.pid)"
echo "  Frontend: kill \$(cat frontend.pid)"
echo "  Both: ./stop_all.sh"
echo ""
echo "✅ Application is now running in background!"
