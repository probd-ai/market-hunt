#!/bin/bash

# Stop all Market Hunt services
echo "Stopping Market Hunt Application..."

# Change to project directory
cd /media/guru/Data/workspace/market-hunt

# Stop backend if running
if [ -f "backend.pid" ]; then
    BACKEND_PID=$(cat backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "Stopping Backend API Server (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        rm -f backend.pid
        echo "✅ Backend stopped"
    else
        echo "⚠️  Backend not running"
        rm -f backend.pid
    fi
else
    echo "⚠️  Backend PID file not found"
fi

# Stop frontend if running
if [ -f "frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "Stopping Frontend Server (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        rm -f frontend.pid
        echo "✅ Frontend stopped"
    else
        echo "⚠️  Frontend not running"
        rm -f frontend.pid
    fi
else
    echo "⚠️  Frontend PID file not found"
fi

echo ""
echo "🛑 Market Hunt Application stopped"
