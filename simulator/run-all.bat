@echo off
echo ============================================
echo   AI Hospital IVR Simulator - Full Stack
echo ============================================
echo.
echo Starting backend and frontend simultaneously...
echo.

start "IVR Backend" cmd /k "%~dp0run-backend.bat"
timeout /t 5 /nobreak > nul
start "IVR Frontend" cmd /k "%~dp0run-frontend.bat"

echo.
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:5173
echo   API Docs:  http://localhost:8000/docs
echo.
echo Both servers started in separate windows.
