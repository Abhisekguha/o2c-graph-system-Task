@echo off
echo ====================================
echo SAP O2C Graph System - Quick Start
echo ====================================
echo.

echo Checking prerequisites...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 16 or higher
    pause
    exit /b 1
)

echo.
echo Starting Backend Server...
echo.

cd backend
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing backend dependencies...
pip install -q -r requirements.txt

if not exist ".env" (
    echo.
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your GEMINI_API_KEY
    echo.
    echo Example:
    echo   copy .env.example .env
    echo   notepad .env
    echo.
    pause
    exit /b 1
)

echo.
echo Starting backend server on http://localhost:8000
echo.
start "SAP O2C Backend" cmd /k "python app.py"

timeout /t 5 /nobreak >nul

cd ..\frontend

echo.
echo Checking frontend dependencies...
if not exist "node_modules" (
    echo Installing frontend dependencies (this may take a few minutes)...
    call npm install
)

echo.
echo Starting frontend on http://localhost:3000
echo Browser will open automatically...
echo.

start "SAP O2C Frontend" cmd /k "npm start"

echo.
echo ====================================
echo Both servers are starting!
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to view backend logs...
pause >nul
