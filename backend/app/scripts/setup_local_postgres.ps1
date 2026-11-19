# JanMitra Assist - Automated PostgreSQL 16 Setup & Migration Script
# Run this script in PowerShell as Administrator to provision PostgreSQL 16 Windows service,
# initialize the database, execute Alembic migrations, and migrate development data.

param(
    [string]$SuperPassword = "postgres",
    [string]$AppUserPassword = "JanMitra_Secure_Dev_2026!",
    [string]$DatabaseName = "janmitra",
    [string]$AppUserName = "janmitra_app",
    [int]$Port = 5432
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "JANMITRA ASSIST - POSTGRESQL 16 AUTOMATED PROVISIONING" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check Administrator Rights
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script requires Administrator privileges to configure Windows services."
    Write-Warning "Please right-click PowerShell and select 'Run as Administrator', then execute:"
    Write-Host "powershell -ExecutionPolicy Bypass -File E:\Janmitra\backend\app\scripts\setup_local_postgres.ps1" -ForegroundColor Yellow
    exit 1
}

# 2. Check if PostgreSQL 16 is already installed
$pgService = Get-Service postgresql-x64-16 -ErrorAction SilentlyContinue
$installerPath = "E:\Janmitra\installers\postgresql-16.16-1-windows-x64.exe"

if (-not $pgService) {
    if (-not (Test-Path $installerPath)) {
        Write-Error "Official PostgreSQL 16 installer not found at $installerPath."
        exit 1
    }

    Write-Host "[STEP 1] Installing PostgreSQL 16 as a Windows service..." -ForegroundColor Green
    $installArgs = @(
        "--mode", "unattended",
        "--unattendedmodeui", "minimal",
        "--superpassword", $SuperPassword,
        "--servicepassword", $SuperPassword,
        "--serverport", $Port
    )

    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Error "Installer exited with error code: $($process.ExitCode)"
        exit 1
    }
    Write-Host "  ✓ PostgreSQL 16 installed successfully." -ForegroundColor Green
} else {
    Write-Host "[STEP 1] PostgreSQL 16 service found ($($pgService.Status))." -ForegroundColor Green
    if ($pgService.Status -ne "Running") {
        Write-Host "  Starting PostgreSQL service..." -ForegroundColor Yellow
        Start-Service postgresql-x64-16
    }
}

# 3. Locate psql and configure PATH
$psqlPath = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
if (-not (Test-Path $psqlPath)) {
    # Search alternative paths
    $found = Get-ChildItem "C:\Program Files\PostgreSQL" -Filter "psql.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $psqlPath = $found.FullName
    } else {
        Write-Error "psql.exe not found under C:\Program Files\PostgreSQL."
        exit 1
    }
}
$pgBinDir = Split-Path $psqlPath
Write-Host "  ✓ Located PostgreSQL binaries at: $pgBinDir" -ForegroundColor Green

# Add to current session PATH
$env:PATH = "$pgBinDir;" + $env:PATH

# 4. Provision Database and Restricted Application User
Write-Host "`n[STEP 2] Provisioning dedicated database and application user..." -ForegroundColor Green
$env:PGPASSWORD = $SuperPassword

$sqlInit = @"
DO `$do`$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$AppUserName') THEN
      CREATE ROLE $AppUserName WITH LOGIN PASSWORD '$AppUserPassword';
   END IF;
END
`$do`$;

SELECT 'CREATE DATABASE $DatabaseName WITH OWNER $AppUserName ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DatabaseName')\gexec

\c $DatabaseName

GRANT ALL ON SCHEMA public TO $AppUserName;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $AppUserName;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $AppUserName;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $AppUserName;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $AppUserName;
"@

$sqlInit | & $psqlPath -U postgres -h localhost -p $Port -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to provision PostgreSQL database and role."
    exit 1
}
Write-Host "  ✓ Database '$DatabaseName' and user '$AppUserName' configured." -ForegroundColor Green

# 5. Run Alembic Migrations to Head
Write-Host "`n[STEP 3] Running Alembic migrations to head revision (f8a9b0c1d2e3)..." -ForegroundColor Green
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

# 6. Migrate Existing Development Data
Write-Host "`n[STEP 4] Migrating development data from SQLite (janmitra_dev.db)..." -ForegroundColor Green
$migrationScript = Join-Path $backendDir "app\scripts\migrate_sqlite_to_postgres.py"
& $pythonExe $migrationScript "janmitra_dev.db" $pgConnString
if ($LASTEXITCODE -ne 0) {
    Write-Error "Data migration failed."
    exit 1
}
Write-Host "  ✓ Development records migrated into PostgreSQL." -ForegroundColor Green

# 7. Update .env Configuration
Write-Host "`n[STEP 5] Updating backend .env configuration..." -ForegroundColor Green
$envFile = Join-Path $backendDir ".env"
$envContent = Get-Content $envFile -Raw
# Replace or set DATABASE_URL
if ($envContent -match "DATABASE_URL=.*") {
    $envContent = $envContent -replace "DATABASE_URL=.*", "DATABASE_URL=postgresql://$($AppUserName):$($AppUserPassword)@localhost:$Port/$DatabaseName"
} else {
    $envContent += "`nDATABASE_URL=postgresql://$($AppUserName):$($AppUserPassword)@localhost:$Port/$DatabaseName`n"
}
Set-Content -Path $envFile -Value $envContent
Write-Host "  ✓ Backend .env configured with primary PostgreSQL database." -ForegroundColor Green

# 8. Run PostgreSQL Integration Tests
Write-Host "`n[STEP 6] Running dedicated PostgreSQL integration tests..." -ForegroundColor Green
$env:TEST_POSTGRES_URL = $pgConnString
$pytestExe = Join-Path $backendDir "venv\Scripts\pytest.exe"
& $pytestExe tests/test_postgres_integration.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some PostgreSQL integration tests failed or reported warnings. Check logs."
} else {
    Write-Host "  ✓ All PostgreSQL integration tests passed." -ForegroundColor Green
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "POSTGRESQL 16 SETUP AND MIGRATION COMPLETE!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
