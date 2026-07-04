# PowerShell Production Launcher Script for InvoMatch (Local Windows Environment)
# Automates environment checks, database validation, frontend builds, and backend serving

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   InvoMatch Production Deployment Launcher  " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Backend environment validation
Write-Host "`n[1/4] Checking python virtual environment..." -ForegroundColor Yellow
$venvPath = "backend/venv"
if (-not (Test-Path $venvPath)) {
    Write-Error "Virtual environment not found under $venvPath. Please run Phase 1 setup first."
    Exit 1
}
Write-Host "SUCCESS: Virtual environment located." -ForegroundColor Green

# 2. Re-verify backend sanity & database schemas
Write-Host "`n[2/4] Validating database & schema configurations..." -ForegroundColor Yellow
$verifyOutput = & "backend/venv/Scripts/python.exe" "verify_backend.py"
Write-Host $verifyOutput

if ($verifyOutput -like "*SUCCESS*") {
    Write-Host "SUCCESS: Database engine and model configurations validated." -ForegroundColor Green
} else {
    Write-Error "Database verification failed. See logs above."
    Exit 1
}

# 3. Frontend compilation
Write-Host "`n[3/4] Checking Node environment to compile React frontend..." -ForegroundColor Yellow
$npmCheck = Get-Command npm -ErrorAction SilentlyContinue
if ($null -eq $npmCheck) {
    Write-Host "WARNING: NPM is not installed in the global environment path." -ForegroundColor Orange
    Write-Host "Skipping frontend assets compilation. Standard static files can be served or built manually." -ForegroundColor Gray
} else {
    Write-Host "SUCCESS: NPM located. Compiling production bundle..." -ForegroundColor Green
    Push-Location frontend
    & npm install
    & npm run build
    Pop-Location
    Write-Host "SUCCESS: Production frontend bundle compiled inside 'frontend/dist'." -ForegroundColor Green
}

# 4. Starting backend production server (Multi-process Uvicorn workers)
Write-Host "`n[4/4] Starting FastAPI Uvicorn backend with multi-process workers..." -ForegroundColor Yellow
Write-Host "  Service Address: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to terminate the process." -ForegroundColor Gray
Write-Host "---------------------------------------------" -ForegroundColor Gray

# Change directory to backend to execute imports correctly
Push-Location backend
& "../backend/venv/Scripts/uvicorn.exe" "app.main:app" --host "127.0.0.1" --port 8000 --workers 4
Pop-Location
