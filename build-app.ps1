# Build the Neo desktop app (Windows) with PyInstaller. Run from the neo dir:
#   powershell -ExecutionPolicy Bypass -File .\build-app.ps1
# Output: dist\Neo\Neo.exe  (a single-folder app you can zip and share)

$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

& $py -m PyInstaller --noconfirm --name Neo --windowed `
  --add-data "dashboard/profiles;dashboard/profiles" `
  --collect-all fastapi --collect-all starlette --collect-all uvicorn `
  --collect-all pydantic --collect-all pydantic_core --collect-all stripe `
  --collect-submodules dashboard --collect-submodules reviewer --collect-submodules neo `
  desktop.py

Write-Host "`nBuilt -> dist\Neo\Neo.exe  (double-click to run)" -ForegroundColor Green
