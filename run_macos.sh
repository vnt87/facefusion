#!/bin/bash

echo "Starting FaceFusion Web UI on MacOS..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run install.py first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check for Modal
if command -v modal &> /dev/null; then
    echo "Modal CLI found. Defaulting to Modal processing."
    ARGS="--modal"
else
    echo "Modal CLI not found. Falling back to Core ML."
    ARGS="--execution-providers coreml"
fi

# Start Backend API in background
echo "Starting Backend API with args: $ARGS"
python facefusion.py run-api $ARGS &
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
