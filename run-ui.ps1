# Local launcher: builds frontend if missing, then starts FastAPI on 127.0.0.1:8000.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path "frontend\dist")) {
    Write-Host "Building frontend (one-time)..."
    Push-Location frontend
    if (-not (Test-Path "node_modules")) { npm install }
    npm run build
    Pop-Location
}

if (Test-Path "venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}

python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
