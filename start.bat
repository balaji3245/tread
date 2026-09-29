@echo off
title XAUUSD Realtime Live Shadow Dashboard Launcher
echo ==========================================================
echo   🚀 Starting XAUUSD Live Market Data Dashboard (Windows)
echo ==========================================================

REM 1. Start MetaTrader 5 if not running
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] MetaTrader 5 is already running.
) else (
    echo [INFO] Launching MetaTrader 5 terminal...
    start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
    timeout /t 3 /nobreak >nul
)

REM 2. Start FastAPI Backend on localhost:8000
echo [INFO] Starting Python FastAPI Backend on http://127.0.0.1:8000...
cd /d "%~dp0backend"
start "XAUUSD Live Backend" cmd /k "..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul

REM 3. Start Next.js Frontend on localhost:3000
echo [INFO] Starting Next.js Dashboard on http://127.0.0.1:3000...
cd /d "%~dp0frontend"
start "XAUUSD Frontend Dashboard" cmd /k "npm run dev"
timeout /t 3 /nobreak >nul

REM 4. Start Production Reverse Proxy on Port 80
echo [INFO] Starting Reverse Proxy on Port 80 (Direct Browser Access)...
echo ==========================================================
echo [SUCCESS] Dashboard is live! Open in your browser:
echo   - Direct Browser Access : http://localhost/ (or http://^<AWS_PUBLIC_IP^>/)
echo ==========================================================
cd /d "%~dp0"
node reverse_proxy.js

