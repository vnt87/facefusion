@echo off
echo Starting FaceFusion Web UI...

:: Check if venv exists
if not exist venv (
    echo Virtual environment not found. Please run install.bat first.
    pause
    exit /b
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Start Backend API in a new window
echo Starting Backend API...
start "FaceFusion API" python facefusion.py run-api --log-level debug

:: Start Frontend
cd facefusion-web
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)

echo Starting Frontend Server...
call npm run dev

pause
