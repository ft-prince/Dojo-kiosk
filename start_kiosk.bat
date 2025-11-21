@echo off
REM Process DOJO Kiosk Quick Start Script
REM This script starts both the SecuGen Client Bridge and Django server

title Process DOJO Kiosk Startup

echo ====================================================================
echo           Process DOJO - Biometric Training Kiosk
echo ====================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo [1/4] Checking Python installation...
python --version
echo.

echo [2/4] Starting SecuGen Client Bridge...
echo        (This connects the fingerprint scanner to the web interface)
echo.

REM Start Client Bridge in a new window
start "SecuGen Client Bridge" cmd /k "cd biometric_sdk && python secugen_client_bridge.py"

REM Wait for client bridge to initialize
echo Waiting for client bridge to initialize (5 seconds)...
timeout /t 5 /nobreak >nul

echo.
echo [3/4] Starting Django Web Server...
echo.

REM Start Django in a new window
start "Django Process DOJO" cmd /k "python manage.py runserver"

REM Wait for Django to start
echo Waiting for Django to start (5 seconds)...
timeout /t 5 /nobreak >nul

echo.
echo [4/4] Opening browser...
echo.

REM Open browser to biometric login page
start http://localhost:8000/process-dojo/biometric/login/

echo.
echo ====================================================================
echo   KIOSK IS NOW RUNNING
echo ====================================================================
echo.
echo   Biometric Login:  http://localhost:8000/process-dojo/biometric/login/
echo   Admin Panel:      http://localhost:8000/admin/
echo   Enrollment:       http://localhost:8000/process-dojo/biometric/enrollment/
echo.
echo   Client Bridge:    http://localhost:5000
echo.
echo   To stop the kiosk:
echo   1. Close the SecuGen Client Bridge window
echo   2. Close the Django Process DOJO window
echo   3. Close this window
echo.
echo ====================================================================
echo.
pause