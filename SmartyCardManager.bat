@echo off
:: filepath: x:\smarty-smart\SmartyCardManager.bat
title Smart Card Manager Launcher
echo Starting Smart Card Manager...

:: Set the path to the application directory - change this if installed elsewhere
set APP_DIR=x:\smarty-smart

:: Change to the application directory
cd /d "%APP_DIR%" || (
    echo ERROR: Could not change directory to %APP_DIR%. Ensure the path is correct.
    pause
    exit /b 1
)

:: Check if Python exists
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from python.org
    echo and ensure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)

:: Check if Python version is sufficient
for /f "tokens=2 delims=. " %%a in ('python -V 2^>^&1') do (
  set PY_MAJOR_VERSION=%%a
  goto :version_check_done
)
:version_check_done

if %PY_MAJOR_VERSION% LSS 3 (
    echo ERROR: Python version is too old.  Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: First run the setup checker script to ensure all dependencies are installed
echo Checking required packages...
echo.
python setup_checker.py --quiet 2>checker_errors.txt
if %ERRORLEVEL% NEQ 0 (
    echo Setup checker reported issues. Please resolve before continuing.
    type checker_errors.txt
    pause
    exit /b 1
)
del checker_errors.txt

:: Check if virtual environment exists, activate if it does
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat || (
        echo ERROR: Failed to activate virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Note: Running without virtual environment
)

:: Start the application in the background
echo Launching Smart Card Manager...
start /B "" python app\smart.py || (
    echo ERROR: Failed to start the application.
    pause
    exit /b 1
)

:: Wait for the server to start
echo Waiting for server to start...
timeout /t 3 /nobreak >nul

:: Open the browser to the application
echo Opening browser...
start http://localhost:5000/ || echo WARNING: Could not open the browser.  Please navigate to http://localhost:5000/ manually.

:: Display success message
echo.
echo Smart Card Manager is now running!
echo You can close this window once you're finished using the application.
echo To shut down the server, press Ctrl+C in this window before closing.

:keep_running
:: Keep the window open so the server keeps running, check every 5 seconds if the server is still running
timeout /t 5 /nobreak >nul
tasklist /FI "WindowTitle eq Smart Card Manager Launcher" | find /I "python" > nul
if %ERRORLEVEL% NEQ 0 (
    echo Server process not found. Exiting...
    goto :cleanup
)
goto :keep_running

:cleanup
echo Smart Card Manager has been closed.

:: Deactivate virtual environment if it was activated
if exist venv\Scripts\activate.bat (
    call venv\Scripts\deactivate.bat
)
pause