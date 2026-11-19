# JanMitra Assist - Automated Docker PostgreSQL 16 Setup & Migration Script
# Run this script if you have started Docker Desktop to provision PostgreSQL 16 in a container.

param(
    [string]$AppUserPassword = "JanMitra_Secure_Dev_2026!",
    [string]$DatabaseName = "janmitra",
    [string]$AppUserName = "janmitra_app",
    [int]$Port = 5432
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "JANMITRA ASSIST - DOCKER POSTGRESQL 16 SETUP" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check Docker Daemon
try {
    docker version | Out-Null
} catch {
    Write-Error "Docker daemon is not reachable. Please start Docker Desktop and wait until it is running."
    exit 1
}

# 2. Start PostgreSQL 16 Container
$containerName = "janmitra-postgres-16"
$existing = docker ps -a --filter "name=$containerName" --format "{{.Names}}"
if ($existing -eq $containerName) {
    Write-Host "Starting existing container $containerName..." -ForegroundColor Yellow
    docker start $containerName
} else {
    Write-Host "Launching new PostgreSQL 16 container..." -ForegroundColor Green
    docker run -d `
        --name $containerName `
        -e POSTGRES_DB=$DatabaseName `
        -e POSTGRES_USER=$AppUserName `
        -e POSTGRES_PASSWORD=$AppUserPassword `
        -p ${Port}:5432 `
        --restart unless-stopped `
        postgres:16-alpine
}

Write-Host "Waiting for PostgreSQL engine to accept connections..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 3. Run Alembic Migrations to Head
Write-Host "`n[STEP 1] Running Alembic migrations to head revision (f8a9b0c1d2e3)..." -ForegroundColor Green
$backendDir = "E:\Janmitra\backend"
$pythonExe = Join-Path $backendDir "venv\Scripts\python.exe"
$alembicExe = Join-Path $backendDir "venv\Scripts\alembic.exe"

$pgConnString = "postgresql+psycopg://$($AppUserName):$($AppUserPassword)@localhost:$Port/$DatabaseName"
$env:ALEMBIC_DATABASE_URL = $pgConnString

Set-Location $backendDir
& $alembicExe upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Error "Alembic migration failed."
    exit 1
}
Write-Host "  ✓ Alembic schema upgraded to head." -ForegroundColor Green

# 4. Migrate Existing Development Data
Write-Host "`n[STEP 2] Migrating development data from SQLite (janmitra_dev.db)..." -ForegroundColor Green
$migrationScript = Join-Path $backendDir "app\scripts\migrate_sqlite_to_postgres.py"
& $pythonExe $migrationScript "janmitra_dev.db" $pgConnString
if ($LASTEXITCODE -ne 0) {
    Write-Error "Data migration failed."
    exit 1
}
Write-Host "  ✓ Development records migrated into PostgreSQL." -ForegroundColor Green

# 5. Update .env Configuration
Write-Host "`n[STEP 3] Updating backend .env configuration..." -ForegroundColor Green
$envFile = Join-Path $backendDir ".env"
$envContent = Get-Content $envFile -Raw
if ($envContent -match "DATABASE_URL=.*") {
    $envContent = $envContent -replace "DATABASE_URL=.*", "DATABASE_URL=postgresql://$($AppUserName):$($AppUserPassword)@localhost:$Port/$DatabaseName"
} else {
    $envContent += "`nDATABASE_URL=postgresql://$($AppUserName):$($AppUserPassword)@localhost:$Port/$DatabaseName`n"
}
Set-Content -Path $envFile -Value $envContent
Write-Host "  ✓ Backend .env configured with primary PostgreSQL database." -ForegroundColor Green

# 6. Run PostgreSQL Integration Tests
Write-Host "`n[STEP 4] Running dedicated PostgreSQL integration tests..." -ForegroundColor Green
$env:TEST_POSTGRES_URL = $pgConnString
$pytestExe = Join-Path $backendDir "venv\Scripts\pytest.exe"
& $pytestExe tests/test_postgres_integration.py -v

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "DOCKER POSTGRESQL 16 SETUP AND MIGRATION COMPLETE!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
