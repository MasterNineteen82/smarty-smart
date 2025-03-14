REM filepath: x:\smarty-smart\SmartyCardManager.bat
@echo off
setlocal

:: Set script title
title Smart Card Manager Launcher

:: Define log file
set "LOG_FILE=launcher.log"

:: Check if running with admin privileges
fsutil dirty query %systemdrive% >nul 2>&1
if %errorlevel% equ 0 (
    echo Running with administrator privileges.
    echo [%DATE% %TIME%] - Running with administrator privileges. >> %LOG_FILE%
) else (
    echo WARNING: Not running with administrator privileges. Some features may be limited.
    echo [%DATE% %TIME%] - WARNING: Not running with administrator privileges. Some features may be limited. >> %LOG_FILE%
)

:: Check for Python installation
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo Python found.
    echo [%DATE% %TIME%] - Python found. >> %LOG_FILE%
    set "PYTHON_FOUND=true"
) else (
    echo WARNING: Python not found.
    echo [%DATE% %TIME%] - WARNING: Python not found. >> %LOG_FILE%
    set "PYTHON_FOUND=false"
)

:: Check Python version
if "%PYTHON_FOUND%"=="true" (
    for /f "tokens=2 delims=. " %%i in ('python --version 2^>^&1') do set "PY_MAJOR_VERSION=%%i"
    echo Python version %PY_MAJOR_VERSION% detected.
    if %PY_MAJOR_VERSION% LSS 3 (
        echo ERROR: Python version is too old.  Please install Python 3.8 or higher.
        echo [%DATE% %TIME%] - ERROR: Python version is too old.  Please install Python 3.8 or higher. >> %LOG_FILE%
        echo [%DATE% %TIME%] - Python %PY_MAJOR_VERSION% is insufficient.  Please install Python 3.8 or higher. Script will now continue but functionality may be limited. >> %LOG_FILE%
        set "PYTHON_VERSION_OK=false"
    ) else (
        echo [%DATE% %TIME%] - Python version %PY_MAJOR_VERSION% is sufficient >> %LOG_FILE%
        set "PYTHON_VERSION_OK=true"
    )
) else (
    echo WARNING: Python not found, skipping version check.
    echo [%DATE% %TIME%] - WARNING: Python not found, skipping version check. >> %LOG_FILE%
    set "PYTHON_VERSION_OK=false"
)

:: Check if virtual environment exists, activate if it does, and handle errors robustly
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    echo [%DATE% %TIME%] - Activating virtual environment... >> %LOG_FILE%
    call venv\Scripts\activate.bat || (
        echo ERROR: Failed to activate virtual environment. Attempting alternative activation...
        echo [%DATE% %TIME%] - ERROR: Failed to activate virtual environment. Attempting alternative activation... >> %LOG_FILE%
        
        :: Retry activation with a direct call to cmd /c to handle potential environment issues
        cmd /c call venv\Scripts\activate.bat || (
            echo FATAL ERROR: Failed to activate virtual environment using both methods.
            echo [%DATE% %TIME%] - FATAL ERROR: Failed to activate virtual environment using both methods. >> %LOG_FILE%
            echo [%DATE% %TIME%] - Check venv setup. Script execution halted. >> %LOG_FILE%
            exit /b 1
        )
    )
    echo [%DATE% %TIME%] - Virtual environment activated successfully >> %LOG_FILE%
    set "VENV_ACTIVE=true"
) else (
    echo Note: Virtual environment not found, running without it.
    echo [%DATE% %TIME%] - Note: Virtual environment not found, running without it. >> %LOG_FILE%
    set "VENV_ACTIVE=false"
)

:: Check and install required packages using pip if Python is available
echo Checking and installing required packages...
echo [%DATE% %TIME%] - Checking and installing required packages... >> %LOG_FILE%
if "%PYTHON_FOUND%"=="true" (
    echo [%DATE% %TIME%] - Running pip install to ensure all dependencies are installed... >> %LOG_FILE%
    python -m pip install --no-cache-dir --upgrade pip
    python -m pip install --no-cache-dir -r requirements.txt 2> install_errors.txt
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install required packages. See install_errors.txt for details.
        type install_errors.txt
        echo [%DATE% %TIME%] - ERROR: Failed to install required packages. See install_errors.txt for details. >> %LOG_FILE%
        set "APP_LAUNCHED=false"
        goto :app_launch_failed
    )
    echo [%DATE% %TIME%] - All required packages installed successfully >> %LOG_FILE%
    set "APP_LAUNCHED=true"
) else (
    echo WARNING: Python not found, skipping package installation.
    echo [%DATE% %TIME%] - WARNING: Python not found, skipping package installation. >> %LOG_FILE%
    set "APP_LAUNCHED=false"
    goto :app_launch_failed
)

:launch_app
:: Start the application
if "%PYTHON_FOUND%"=="true" (
    echo Starting Smart Card Manager...
    echo [%DATE% %TIME%] - Starting Smart Card Manager... >> %LOG_FILE%
    
    :: Start the application in the background
    start "" python smart.py --port 8765 --frontend-port 5678
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to start the application.
        echo [%DATE% %TIME%] - ERROR: Failed to start the application. >> %LOG_FILE%
        echo [%DATE% %TIME%] - Failed to start the application.  Check app\smart.py. >> %LOG_FILE%
        type install_errors.txt >> %LOG_FILE%
        set "APP_LAUNCHED=false"
        goto :app_launch_failed
    )
    echo [%DATE% %TIME%] - Smart Card Manager launched in the background >> %LOG_FILE%
    set "APP_LAUNCHED=true"
) else (
    echo WARNING: Python not found, skipping application launch.
    echo [%DATE% %TIME%] - WARNING: Python not found, skipping application launch. >> %LOG_FILE%
    set "APP_LAUNCHED=false"
    goto :app_launch_failed
)

:app_launch_failed
echo Application launch failed, some functionality may be unavailable
echo [%DATE% %TIME%] - Application launch failed, some functionality may be unavailable >> %LOG_FILE%

:wait_and_open
:: Wait for the server to start
echo Waiting for server to start...
echo [%DATE% %TIME%] - Waiting for server to start... >> %LOG_FILE%
timeout /t 3 /nobreak >nul

:: Open the browser to the application
echo Opening browser...
echo [%DATE% %TIME%] - Opening browser... >> %LOG_FILE%
start http://localhost:5678/ || (
    echo WARNING: Could not open the browser.  Please navigate to http://localhost:5678/ manually.
    echo [%DATE% %TIME%] - WARNING: Could not open the browser.  Please navigate to http://localhost:5678/ manually. >> %LOG_FILE%
    set "BROWSER_OPENED=false"
    goto :browser_open_failed
)
echo [%DATE% %TIME%] - Browser opened (or attempt made) to http://localhost:5678/ >> %LOG_FILE%
set "BROWSER_OPENED=true"
goto :success_message

:browser_open_failed
echo Browser failed to open, please navigate to http://localhost:5678/ manually
echo [%DATE% %TIME%] - Browser failed to open, please navigate to http://localhost:5678/ manually >> %LOG_FILE%

:success_message
:: Display success message
echo.
echo Smart Card Manager is now running!
echo You can close this window once you're finished using the application.
echo To shut down the server, press Ctrl+C in this window before closing.
echo [%DATE% %TIME%] - Smart Card Manager is now running! >> %LOG_FILE%

:keep_running
:: Keep the window open so the server keeps running, check every 5 seconds if the server is still running
timeout /t 5 /nobreak >nul
if "%APP_LAUNCHED%"=="true" (
    tasklist /FI "WindowTitle eq Smart Card Manager Launcher" | find /I "python" > nul
    if %ERRORLEVEL% NEQ 0 (
        echo Server process not found. Exiting...
        echo [%DATE% %TIME%] - Server process not found. Exiting... >> %LOG_FILE%
        goto :cleanup
    )
    goto :keep_running
) else (
    echo Application was not launched, skipping server process check.
    echo [%DATE% %TIME%] - Application was not launched, skipping server process check. >> %LOG_FILE%
    goto :cleanup
)
:cleanup
echo Smart Card Manager has been closed.
echo [%DATE% %TIME%] - Smart Card Manager has been closed. >> %LOG_FILE%

:: Deactivate virtual environment if it was activated
if "%VENV_ACTIVE%"=="true" (
    echo [%DATE% %TIME%] - Deactivating virtual environment... >> %LOG_FILE%
    call venv\Scripts\deactivate.bat || (
        echo ERROR: Failed to deactivate virtual environment.
        echo [%DATE% %TIME%] - ERROR: Failed to deactivate virtual environment. >> %LOG_FILE%
    )
    echo [%DATE% %TIME%] - Virtual environment deactivated >> %LOG_FILE%
)

:end_script
echo [%DATE% %TIME%] - Script execution finished >> %LOG_FILE%
echo Script completed.  Check %LOG_FILE% for details.
pause
exit /b 0