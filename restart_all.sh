#!/bin/bash

# Restart Market Hunt Application (without rebuilding)
echo "Restarting Market Hunt Application..."

# Change to project directory
cd /media/guru/Data/workspace/market-hunt

echo "1. Stopping existing services..."
./stop_all.sh

echo ""
echo "2. Starting services..."
./start_all.sh

echo ""
echo "✅ Application restarted successfully!"
