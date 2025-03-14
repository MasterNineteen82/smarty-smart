@echo off
REM filepath: x:\smarty-smart\SmartyCardManager_fixed.bat
title Smart Card Manager Launcher
echo Starting Smart Card Manager...

REM Set the path to the application directory
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%" || (
    echo ERROR: Could not change to application directory.
    pause
    exit /b 1
)

REM Check for Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check required packages
echo Checking required packages...
python -m pip install -r requirements.txt >nul 2>&1

REM Run the setup checker
python setup_checker.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Setup checker reported issues. Please resolve before continuing.
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Determine the entry point file
set "ENTRY_POINT=app\smart.py"
if not exist "%ENTRY_POINT%" (
    if exist "smart.py" (
        set "ENTRY_POINT=smart.py"
    ) else if exist "app\core\smart.py" (
        set "ENTRY_POINT=app\core\smart.py"
    ) else if exist "app\main.py" (
        set "ENTRY_POINT=app\main.py"
    ) else (
        echo ERROR: Could not find application entry point.
        pause
        exit /b 1
    )
)

REM Start the application
echo Starting application from %ENTRY_POINT%...
start /B "" python "%ENTRY_POINT%"

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Open browser
start http://localhost:5000/

echo.
echo Smart Card Manager is now running!
echo You can close this window once you're finished using the application.
echo To shut down the server, press Ctrl+C in this window.

pause