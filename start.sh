#!/bin/bash

echo "===================================="
echo "SAP O2C Graph System - Quick Start"
echo "===================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Please install Node.js 16 or higher"
    exit 1
fi

echo "Starting Backend Server..."
echo ""

cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing backend dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo ""
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and add your GEMINI_API_KEY"
    echo ""
    echo "Example:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
    exit 1
fi

echo ""
echo "Starting backend server on http://localhost:8000"
echo ""

# Start backend in background
python app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

cd ../frontend

echo ""
echo "Checking frontend dependencies..."
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (this may take a few minutes)..."
    npm install
fi

echo ""
echo "Starting frontend on http://localhost:3000"
echo "Browser will open automatically..."
echo ""

# Start frontend
npm start &
FRONTEND_PID=$!

echo ""
echo "===================================="
echo "Both servers are running!"
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "===================================="

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
