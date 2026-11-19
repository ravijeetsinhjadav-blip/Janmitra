# JanMitra Assist - Unified System Launcher for PowerShell
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "       JANMITRA ASSIST - MCA PROJECT DEMO LAUNCHER (POWERSHELL)    " -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Cyan

$Root = $PSScriptRoot
if (Test-Path "$Root\flutter\bin\flutter.bat") {
    $env:Path = "$Root\flutter\bin;$env:Path"
}

# Ensure PostgreSQL 16 is running on Port 5432
$pgListening = netstat -ano | Select-String ":5432" | Select-String "LISTENING"
if (-not $pgListening) {
    Write-Host "[*] Starting PostgreSQL 16 Server (Port 5432)..." -ForegroundColor Cyan
    if (Test-Path "$Root\pgsql\bin\pg_ctl.exe") {
        & "$Root\pgsql\bin\pg_ctl.exe" -D "$Root\pgsql_data" -l "$Root\pgsql_data\pg.log" start
        Start-Sleep -Seconds 2
    }
}

Write-Host "`n[1/3] Starting FastAPI Backend on Port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; .\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

Write-Host "[2/3] Starting React Admin Dashboard on Port 3000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\admin_dashboard'; npm run dev -- --host 127.0.0.1 --port 3000"

Write-Host "[3/3] Starting Flutter Citizen Web App on Port 8080..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\mobile_app'; flutter run -d web-server --web-port=8080 --web-hostname=127.0.0.1"

Write-Host "`n===================================================================" -ForegroundColor Green
Write-Host "All 3 services launched in dedicated PowerShell windows:" -ForegroundColor Green
Write-Host "  * Citizen Mobile/Web App : http://127.0.0.1:8080" -ForegroundColor White
Write-Host "  * Admin Dashboard        : http://127.0.0.1:3000" -ForegroundColor White
Write-Host "  * Backend API & Swagger  : http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "===================================================================`n" -ForegroundColor Green

