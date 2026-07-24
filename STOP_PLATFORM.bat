@echo off
title Ultimate Scraper Platform Stopper
color 0C

echo ===================================================
echo       Stopping Ultimate Scraper Platform...
echo ===================================================
echo.

echo Stopping Backend process (port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Frontend process (port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ===================================================
echo   All platform servers have been stopped.
echo ===================================================
echo.
pause
