@echo off
setlocal
title Quick Downloader - Register Native Host

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0installer\quick_downloader_updater.py" --mode register
    goto :result
)

where python >nul 2>&1
if not errorlevel 1 (
    python "%~dp0installer\quick_downloader_updater.py" --mode register
    goto :result
)

echo.
echo ERROR: Python 3 was not found.
echo Install Python 3 and run this file again.
set "EXIT_CODE=1"
goto :finish

:result
set "EXIT_CODE=%ERRORLEVEL%"

:finish
echo.
if "%EXIT_CODE%"=="0" (
    echo Quick Downloader native host registration finished.
) else (
    echo Quick Downloader native host registration failed. Error code: %EXIT_CODE%
)
pause
exit /b %EXIT_CODE%
