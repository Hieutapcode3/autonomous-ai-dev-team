# Autonomous Multi-Agent Software Team Launcher
Write-Host "Starting Autonomous Multi-Agent Software Team..." -ForegroundColor Cyan

# Start Backend
Write-Host "Starting Python FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
$backendProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; $env:PYTHONPATH='backend'; .\backend\venv\Scripts\python backend/run.py" -PassThru

# Start Frontend
Write-Host "Starting Next.js Control Center on http://localhost:3000..." -ForegroundColor Green
$frontendProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev" -PassThru

Write-Host "`nSystem online!" -ForegroundColor Cyan
Write-Host "Backend API:      http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "Control Center:   http://localhost:3000" -ForegroundColor Yellow
Write-Host "`nPress Ctrl+C or close the opened terminal windows to stop."
