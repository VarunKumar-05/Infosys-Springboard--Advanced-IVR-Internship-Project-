@echo off
echo ============================================
echo   AI Hospital IVR Simulator - Backend
echo ============================================
echo.

cd /d "%~dp0backend"

:: Create virtual environment if needed
if not exist "venv" (
    echo [1/3] Creating Python virtual environment...
    python -m venv venv
)

echo [2/3] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo [3/3] Starting FastAPI server on http://localhost:8000
echo.
echo   Swagger UI:  http://localhost:8000/docs
echo   ReDoc:       http://localhost:8000/redoc
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
