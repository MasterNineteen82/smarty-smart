REM filepath: x:\smarty-smart\SmartyCardManager.bat
@echo off
:: filepath: x:\smarty-smart\SmartyCardManager.bat
title Smart Card Manager Launcher
echo Starting Smart Card Manager...

:: Set the path to the application directory - change this if installed elsewhere
set "APP_DIR=x:\smarty-smart"

:: Log file setup
set "LOG_FILE=SmartCardManager.log"
echo [%DATE% %TIME%] - Starting Smart Card Manager >> %LOG_FILE%

:: Function to log messages
:log_message
echo [%DATE% %TIME%] - %~1 >> %LOG_FILE%
exit /b 0

:: Change to the application directory
echo [%DATE% %TIME%] - Attempting to change directory to %APP_DIR%
pushd "%APP_DIR%" || (
    echo ERROR: Could not change directory to %APP_DIR%. Ensure the path is correct.
    echo ERROR: Could not change directory to %APP_DIR%. Ensure the path is correct. >> %LOG_FILE%
    echo [%DATE% %TIME%] - ERROR: Could not change directory to %APP_DIR%.  Script will now continue but functionality may be limited. >> %LOG_FILE%
    set "APP_DIR_OK=false"
    goto :check_python
)
echo [%DATE% %TIME%] - Changed directory to %APP_DIR% >> %LOG_FILE%
set "APP_DIR_OK=true"

:check_python
:: Check if Python exists
echo [%DATE% %TIME%] - Checking for Python in PATH... >> %LOG_FILE%
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from python.org
    echo and ensure "Add Python to PATH" is checked during installation.
    echo [%DATE% %TIME%] - ERROR: Python is not installed or not in PATH. >> %LOG_FILE%
    echo [%DATE% %TIME%] - Please install Python 3.8 or higher and ensure it's in your PATH. Script will now continue but functionality may be limited. >> %LOG_FILE%
    set "PYTHON_FOUND=false"
    goto :check_python_version
) else (
    set "PYTHON_FOUND=true"
    echo [%DATE% %TIME%] - Python executable found in PATH >> %LOG_FILE%
)

:check_python_version
:: Check if Python version is sufficient
echo [%DATE% %TIME%] - Checking Python version... >> %LOG_FILE%
if "%PYTHON_FOUND%"=="true" (
    for /f "tokens=2 delims=. " %%a in ('python -V 2^>^&1') do (
        set "PY_MAJOR_VERSION=%%a"
        goto :version_check_done
    )
    :version_check_done

    if "%PY_MAJOR_VERSION%"=="" (
        echo ERROR: Could not determine Python version.
        echo [%DATE% %TIME%] - ERROR: Could not determine Python version. >> %LOG_FILE%
        set "PYTHON_VERSION_OK=false"
        goto :activate_venv
    )

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

:activate_venv
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

:check_packages
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
        type install_errors.txt >> %LOG_FILE%
        echo [%DATE% %TIME%] - Please resolve the installation issues and try again. Script will now continue but functionality may be limited. >> %LOG_FILE%
        set "PACKAGES_OK=false"
    ) else (
        echo [%DATE% %TIME%] - All required packages are successfully installed. >> %LOG_FILE%
        set "PACKAGES_OK=true"
    )
) else (
    echo WARNING: Python not found, skipping package installation.
    echo [%DATE% %TIME%] - WARNING: Python not found, skipping package installation. >> %LOG_FILE%
    set "PACKAGES_OK=false"
)

:check_port
:: Check if port 5000 is in use
echo Checking if port 5000 is available...
echo [%DATE% %TIME%] - Checking if port 5000 is available... >> %LOG_FILE%
netstat -ano | find ":5000" | find /I "LISTENING" > nul
if %ERRORLEVEL% EQU 0 (
    echo Port 5000 is already in use.
    echo [%DATE% %TIME%] - Port 5000 is already in use. >> %LOG_FILE%
    choice /M "What do you want to do? (C=Change port, K=Kill process, E=Exit)" /C CKE
    if %ERRORLEVEL% EQU 1 (
        :: Change port
        echo Please specify a new port number:
        set /p "NEW_PORT="
        echo Using new port %NEW_PORT%
        echo [%DATE% %TIME%] - Using new port %NEW_PORT% >> %LOG_FILE%
        set "APP_PORT=%NEW_PORT%"
        goto :launch_app
    ) else if %ERRORLEVEL% EQU 2 (
        :: Kill process
        for /f "tokens=5" %%a in ('netstat -ano ^| find ":5000" ^| find /I "LISTENING"') do (
            set "PID=%%a"
            goto :kill_process
        )
    ) else if %ERRORLEVEL% EQU 3 (
        :: Exit
        echo Exiting script.
        echo [%DATE% %TIME%] - Exiting script. >> %LOG_FILE%
        goto :end_script
    )
) else (
    echo Port 5000 is available.
    echo [%DATE% %TIME%] - Port 5000 is available. >> %LOG_FILE%
    set "APP_PORT=5000"
    goto :launch_app
)

:kill_process
:: Kill the process using the PID
echo Killing process with PID %PID%...
echo [%DATE% %TIME%] - Killing process with PID %PID%... >> %LOG_FILE%
taskkill /F /PID %PID%
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to kill process with PID %PID%.
    echo [%DATE% %TIME%] - ERROR: Failed to kill process with PID %PID%. >> %LOG_FILE%
    echo Please kill the process manually and try again.
    echo [%DATE% %TIME%] - Please kill the process manually and try again. >> %LOG_FILE%
    goto :end_script
) else (
    echo Process with PID %PID% killed successfully.
    echo [%DATE% %TIME%] - Process with PID %PID% killed successfully. >> %LOG_FILE%
    timeout /t 2 /nobreak >nul
    set "APP_PORT=5000"
    goto :launch_app
)

:launch_app
:: Start the application in the background
echo Launching Smart Card Manager on port %APP_PORT%...
echo [%DATE% %TIME%] - Launching Smart Card Manager on port %APP_PORT%... >> %LOG_FILE%
if "%PYTHON_FOUND%"=="true" (
    start /B "" python app\smart.py --port %APP_PORT% || (
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
goto :wait_and_open

:app_launch_failed
echo Application launch failed, some functionality may be unavailable
echo [%DATE% %TIME%] - Application launch failed, some functionality may be unavailable >> %LOG_FILE%

:wait_and_open
:: Wait for the server to start
if "%APP_LAUNCHED%"=="true" (
    echo Waiting for server to start...
    echo [%DATE% %TIME%] - Waiting for server to start... >> %LOG_FILE%
    timeout /t 3 /nobreak >nul

    :: Open the browser to the application
    echo Opening browser...
    echo [%DATE% %TIME%] - Opening browser... >> %LOG_FILE%
    start http://localhost:%APP_PORT%/ || (
        echo WARNING: Could not open the browser.  Please navigate to http://localhost:%APP_PORT%/ manually.
        echo [%DATE% %TIME%] - WARNING: Could not open the browser.  Please navigate to http://localhost:%APP_PORT%/ manually. >> %LOG_FILE%
        set "BROWSER_OPENED=false"
        goto :browser_open_failed
    )
    echo [%DATE% %TIME%] - Browser opened (or attempt made) to http://localhost:%APP_PORT%/ >> %LOG_FILE%
    set "BROWSER_OPENED=true"
) else (
    echo WARNING: Application not launched, skipping browser open.
    echo [%DATE% %TIME%] - WARNING: Application not launched, skipping browser open. >> %LOG_FILE%
    set "BROWSER_OPENED=false"
    goto :browser_open_failed
)
goto :success_message

:browser_open_failed
echo Browser failed to open, please navigate to http://localhost:%APP_PORT%/ manually
echo [%DATE% %TIME%] - Browser failed to open, please navigate to http://localhost:%APP_PORT%/ manually >> %LOG_FILE%

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