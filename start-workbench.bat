@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-workbench.ps1"
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
  echo.
  echo [workbench] Launcher stopped with error code %exit_code%.
  pause
)

exit /b %exit_code%
