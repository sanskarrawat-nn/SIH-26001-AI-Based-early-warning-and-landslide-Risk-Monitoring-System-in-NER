@echo off
title NER-LEWS Command Center Launcher
color 0A
echo.
echo  =====================================================
echo    NER-LEWS: Landslide Early Warning Command Center
echo  =====================================================
echo.

echo  [1/4] Checking and clearing ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173 "') do taskkill /f /pid %%a >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo  [2/4] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "NER-LEWS Backend (Port 8000)" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo        Waiting for backend database and ML models to warm up...
python "%~dp0check_health.py" http://127.0.0.1:8000/health 35
if %errorlevel% neq 0 (
    echo        Backend startup is taking longer than expected. Continuing...
) else (
    echo        Backend is healthy and ready!
)

echo  [3/4] Starting Vite Frontend on http://localhost:5173 ...
start "NER-LEWS Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && node node_modules/vite/bin/vite.js --port 5173 --host"

echo        Waiting for frontend server...
python "%~dp0check_health.py" http://localhost:5173 25
if %errorlevel% neq 0 (
    echo        Frontend startup is taking longer than expected. Continuing...
) else (
    echo        Frontend is live and ready!
)

echo.
echo  [4/4] Opening Web Application in browser...
echo.
echo  =====================================================
echo    NER-LEWS Command Center is LIVE!
echo    - Web Application: http://localhost:5173
echo    - REST API Docs:   http://127.0.0.1:8000/docs
echo  =====================================================
echo.

start "" "http://localhost:5173"
