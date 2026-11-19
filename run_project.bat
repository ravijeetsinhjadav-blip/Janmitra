@echo off
title JanMitra Assist - Unified System Launcher (MCA Viva Ready)
echo ===================================================================
echo             JANMITRA ASSIST - MCA PROJECT DEMO LAUNCHER
echo ===================================================================
echo.
if exist "%~dp0flutter\bin\flutter.bat" set "PATH=%~dp0flutter\bin;%PATH%"

:: Ensure PostgreSQL 16 is running on Port 5432
netstat -ano | findstr :5432 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo [*] Starting PostgreSQL 16 Server (Port 5432)...
    if exist "%~dp0pgsql\bin\pg_ctl.exe" (
        "%~dp0pgsql\bin\pg_ctl.exe" -D "%~dp0pgsql_data" -l "%~dp0pgsql_data\pg.log" start
        timeout /t 2 /nobreak >nul
    )
)

echo [1/3] Starting FastAPI Backend (Port 8000)...
start "JanMitra Backend (FastAPI)" cmd /k "cd /d %~dp0backend && venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting React Admin Dashboard (Port 3000)...
start "JanMitra Admin Dashboard (React)" cmd /k "cd /d %~dp0admin_dashboard && npm run dev -- --host 127.0.0.1 --port 3000"

echo [3/3] Starting Flutter Citizen Web App (Port 8080)...
start "JanMitra Citizen App (Flutter)" cmd /k "cd /d %~dp0mobile_app && flutter run -d web-server --web-port=8080 --web-hostname=127.0.0.1"

echo.
echo ===================================================================
echo Services are starting in separate windows:
echo - Citizen Mobile Web: http://127.0.0.1:8080
echo - Admin Dashboard:   http://127.0.0.1:3000
echo - Backend REST API:  http://127.0.0.1:8000 (Docs: /docs)
echo ===================================================================
echo.
pause

