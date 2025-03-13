@echo off
echo Updating project...
pushd "%~dp0"
if exist gitupdate.py (
    echo Running gitupdate.py...
    python gitupdate.py
    if %errorlevel% neq 0 (
        echo Error: gitupdate.py failed with error code %errorlevel%.
        echo Please check the script for errors.
        pause
        exit /b %errorlevel%
    )
    echo gitupdate.py completed successfully.
) else (
    echo Error: gitupdate.py not found in %~dp0.
    echo Please make sure the script exists in the same directory as this batch file.
    pause
    exit /b 1
)
popd
echo Project updated.
pause
exit /b 0