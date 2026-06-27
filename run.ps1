# Run a Neo instance on Windows. Usage:  .\run.ps1 nessa   (or: default, neo, aria)
param([string]$ProfileName = "default")

$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) { $py = "python" }  # fall back to PATH if installed elsewhere

$env:NEO_PROFILE = $ProfileName
# An instance with its own dashboard\data-<profile> folder uses it; otherwise the default store.
$dataDir = Join-Path $PSScriptRoot "dashboard\data-$ProfileName"
$env:NEO_DATA_DIR = if (Test-Path $dataDir) { $dataDir } else { "" }

Write-Host "Starting Neo  (profile: $ProfileName)  ->  http://127.0.0.1:8000" -ForegroundColor Cyan
& $py -m uvicorn dashboard.main:app --reload --port 8000
