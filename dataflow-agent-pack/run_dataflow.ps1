# DATAFLOW Windows Launcher (PowerShell)
# Binds strictly to 127.0.0.1:8501 with zero outbound telemetry
param (
    [switch]$NoBrowser,
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   DATAFLOW v1.0.0 - Automated KP Data Pipeline        " -ForegroundColor Green
Write-Host "   Privacy-Preserving Local Streamlit Application      " -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Python
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
} else {
    Write-Host "[ERROR] Python 3.11+ was not found in your system PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/ and check 'Add python.exe to PATH'." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

$PyVersion = (& $PythonCmd --version)
Write-Host "[OK] Detected $PyVersion via $PythonCmd" -ForegroundColor Gray

# 2. Virtual Environment Setup
$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[INFO] Creating virtual environment in .venv..." -ForegroundColor Yellow
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

# 3. Dependency Verification
Write-Host "[INFO] Verifying pinned dependencies..." -ForegroundColor Gray
$StreamlitExe = Join-Path $VenvDir "Scripts\streamlit.exe"
if (-not (Test-Path $StreamlitExe)) {
    Write-Host "[INFO] Installing requirements from requirements.txt (this may take a couple of minutes)..." -ForegroundColor Yellow
    & $VenvPython -m pip install --upgrade pip --quiet
    & $VenvPython -m pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
        exit 1
    }
}

# 4. Prepare Runtime Directories
$RuntimeDirs = @(
    (Join-Path $ScriptDir "runtime\temporary"),
    (Join-Path $ScriptDir "runtime\audit"),
    (Join-Path $ScriptDir "runtime\audit\diagnostics"),
    (Join-Path $ScriptDir "runtime\exports")
)
foreach ($dir in $RuntimeDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# 5. Launch Application on Localhost
$AppUrl = "http://127.0.0.1:$Port"
Write-Host ""
Write-Host "-------------------------------------------------------" -ForegroundColor Cyan
Write-Host " Launching DATAFLOW on local host: $AppUrl" -ForegroundColor Green
Write-Host " Kenya DPA 2019 / NASCOP strict privacy mode active    " -ForegroundColor Gray
Write-Host " Press Ctrl+C in this console window to stop the server" -ForegroundColor Gray
Write-Host "-------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $AppUrl
}

& $VenvPython -m streamlit run app.py `
    --server.address=127.0.0.1 `
    --server.port=$Port `
    --browser.gatherUsageStats=false `
    --server.headless=true
