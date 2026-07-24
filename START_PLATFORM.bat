@echo off
title Ultimate Scraper Platform Launcher
color 0A

echo ===================================================
echo       Launching Ultimate Scraper Platform...
echo ===================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: 1. Check Python Virtual Environment
if not exist "%ROOT_DIR%venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at:
    echo "%ROOT_DIR%venv\Scripts\python.exe"
    echo.
    echo Please make sure the Python virtual environment is set up.
    echo.
    pause
    exit /b 1
)

:: 2. Check Node.js installation
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/ to run the frontend dashboard.
    echo.
    pause
    exit /b 1
)

echo [1/3] Starting Backend API Server (http://localhost:8000)...
start "Ultimate Scraper - Backend API" /D "%ROOT_DIR%backend" cmd /k "..\venv\Scripts\python.exe -m uvicorn ""app.main:create_production_app"" --factory --port 8000"

echo [2/3] Starting Frontend Web Dashboard (http://localhost:3000)...
start "Ultimate Scraper - Frontend Dashboard" /D "%ROOT_DIR%frontend" cmd /k "npm run dev"

echo [3/3] Waiting for services to initialize...
timeout /t 5 /nobreak >nul

echo.
echo Opening Web Dashboard in your default browser...
start http://localhost:3000

echo.
echo ===================================================
echo   Ultimate Scraper is now running!
echo   - Web Dashboard: http://localhost:3000
echo   - Backend API:   http://localhost:8000
echo.
echo   NOTE: Keep the opened terminal windows running
echo   while using the application.
echo ===================================================
echo.
