@echo off
title Autonomous Multi-Agent Software Team
echo Starting Autonomous Multi-Agent Software Team...

start "Backend Server (FastAPI :8000)" cmd /k "set PYTHONPATH=backend&& .\backend\venv\Scripts\python backend\run.py"
start "Frontend Dashboard (Next.js :3000)" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo  System Initialized!
echo  Backend Docs:    http://127.0.0.1:8000/docs
echo  Control Center:  http://localhost:3000
echo ========================================================
echo.
pause
