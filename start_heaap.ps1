$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$frontend = Join-Path $root "frontend"
$python = Join-Path $root ".venv\Scripts\python.exe"
$backendUrl = "http://127.0.0.1:8000"
$frontendUrl = "http://127.0.0.1:3000"

Write-Host "`n===== HEAAP STARTUP =====" -ForegroundColor Cyan

if (-not (Test-Path $python)) {
    throw "Python virtual environment not found: $python"
}

if (-not (Test-Path $frontend)) {
    throw "Frontend directory not found: $frontend"
}

# Configure frontend
$envFile = Join-Path $frontend ".env.local"

if (Test-Path $envFile) {
    $lines = @(
        Get-Content $envFile |
        Where-Object {
            $_ -notmatch '^\s*(HEAAP_API_URL|NEXT_PUBLIC_API_URL)\s*='
        }
    )
}
else {
    $lines = @()
}

$lines += "HEAAP_API_URL=$backendUrl"
$lines += "NEXT_PUBLIC_API_URL=$backendUrl"

Set-Content $envFile $lines

Write-Host "Frontend configured for $backendUrl"

# Check backend
$backendHealthy = $false

try {
    $api = Invoke-RestMethod "$backendUrl/openapi.json" -TimeoutSec 5

    if ($api.info.title -match "HEAAP") {
        $backendHealthy = $true
        Write-Host "Backend already running: $($api.info.title)" -ForegroundColor Green
    }
}
catch {
    Write-Host "Backend not running." -ForegroundColor Yellow
}

if (-not $backendHealthy) {

    # Do not start another process if the port is occupied
    $occupied = Test-NetConnection 127.0.0.1 -Port 8000 `
        -InformationLevel Quiet -WarningAction SilentlyContinue

    if ($occupied) {
        throw "Port 8000 is occupied by a non-HEAAP service. Inspect it before restarting."
    }

    Write-Host "Starting HEAAP backend..." -ForegroundColor Cyan

    Start-Process `
        -FilePath $python `
        -ArgumentList @(
            "-m", "uvicorn",
            "app.heaap_server:app",
            "--host", "127.0.0.1",
            "--port", "8000"
        ) `
        -WorkingDirectory $root

    Start-Sleep -Seconds 5
}

# Verify backend
$api = Invoke-RestMethod "$backendUrl/openapi.json" -TimeoutSec 10

if ($api.info.title -notmatch "HEAAP") {
    throw "Unexpected backend application: $($api.info.title)"
}

Write-Host "Backend verified: $($api.info.title)" -ForegroundColor Green

# Check frontend
$frontendHealthy = $false

try {
    $page = Invoke-WebRequest $frontendUrl -UseBasicParsing -TimeoutSec 5

    if ($page.StatusCode -eq 200) {
        $frontendHealthy = $true
        Write-Host "Frontend already running on port 3000" -ForegroundColor Green
    }
}
catch {
    Write-Host "Frontend not running." -ForegroundColor Yellow
}

if (-not $frontendHealthy) {

    $occupied = Test-NetConnection 127.0.0.1 -Port 3000 `
        -InformationLevel Quiet -WarningAction SilentlyContinue

    if ($occupied) {
        throw "Port 3000 is occupied. Inspect the process before starting Next.js."
    }

    Write-Host "Starting HEAAP frontend..." -ForegroundColor Cyan

    Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList "/c npm run dev -- -p 3000" `
        -WorkingDirectory $frontend

    Start-Sleep -Seconds 8
}

# Final health checks
Write-Host "`n===== HEAAP HEALTH CHECK =====" -ForegroundColor Cyan

$api = Invoke-RestMethod "$backendUrl/openapi.json" -TimeoutSec 10
Write-Host "Backend: SUCCESS - $($api.info.title)" -ForegroundColor Green

$page = Invoke-WebRequest $frontendUrl -UseBasicParsing -TimeoutSec 10
Write-Host "Frontend: HTTP $($page.StatusCode)" -ForegroundColor Green

try {
    $summary = Invoke-RestMethod `
        "$frontendUrl/api/heaap/api/assurance/live/summary" `
        -TimeoutSec 15

    Write-Host "Frontend-to-backend proxy: SUCCESS" -ForegroundColor Green
    Write-Host "Assurance tests: $($summary.total_tests)"
}
catch {
    Write-Host "Frontend-to-backend proxy: FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`nDashboard: $frontendUrl"
Write-Host "Swagger: $backendUrl/docs"
