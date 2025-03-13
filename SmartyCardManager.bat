@echo off
:: filepath: x:\smarty\SmartCardManager.bat
title Smart Card Manager Launcher
echo Starting Smart Card Manager...

:: Set the path to the application directory - change this if installed elsewhere
set APP_DIR=x:\smarty

:: Change to the application directory
cd /d %APP_DIR%

:: Check if Python exists
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from python.org
    echo and ensure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)

:: First run the setup checker script to ensure all dependencies are installed
echo Checking required packages...
echo.
python setup_checker.py --quiet 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Setup checker reported issues. Please resolve before continuing.
    pause
    exit /b 1
)

:: Check if virtual environment exists, activate if it does
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Note: Running without virtual environment
)

:: Start the application in the background
echo Launching Smart Card Manager...
start /B "" python smart.py

:: Wait for the server to start
echo Waiting for server to start...
timeout /t 3 /nobreak >nul

:: Open the browser to the application
echo Opening browser...
start http://localhost:5000/

:: Display success message
echo.
echo Smart Card Manager is now running!
echo You can close this window once you're finished using the application.
echo To shut down the server, press Ctrl+C in this window before closing.

:: Keep the window open so the server keeps running
pause >nul
echo Smart Card Manager has been closed.

:: Deactivate virtual environment if it was activated
if exist venv\Scripts\activate.bat (
    call venv\Scripts\deactivate.bat
)
pause