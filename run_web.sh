#!/bin/bash

echo "Starting FaceFusion Web UI..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start Backend API in background
echo "Starting Backend API..."
python facefusion.py run-api &
API_PID=$!

# Function to kill API on exit
cleanup() {
    echo "Stopping Backend API..."
    kill $API_PID
}
trap cleanup EXIT

# Start Frontend
cd facefusion-web
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting Frontend Server..."
npm run dev
