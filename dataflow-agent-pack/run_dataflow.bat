@echo off
setlocal EnableDelayedExpansion

title DATAFLOW v1.0.0 - Local KP Data Pipeline
cd /d "%~dp0"

echo =======================================================
echo    DATAFLOW v1.0.0 - Automated KP Data Pipeline
echo    Starting local privacy-preserving application...
echo =======================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dataflow.ps1" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application terminated with error code %ERRORLEVEL%.
    pause
)

endlocal
