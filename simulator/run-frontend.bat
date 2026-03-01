@echo off
echo ============================================
echo   AI Hospital IVR Simulator - Frontend
echo ============================================
echo.

cd /d "%~dp0frontend"

:: Install dependencies if needed
if not exist "node_modules" (
    echo [1/2] Installing npm dependencies...
    npm install
)

echo [2/2] Starting Vite dev server on http://localhost:5173
echo.
npm run dev
