@echo off
REM ============================================================================
REM  run_server.bat
REM  Starts the Streamlit server for the AI Governance and Ethics Platform.
REM  Called automatically by setup_and_start.bat - you normally never run this
REM  file by hand.
REM
REM  Usage:  run_server.bat [port]
REM  The Python interpreter is passed in through AI_GOV_PYTHON.
REM ============================================================================

setlocal EnableExtensions
cd /d "%~dp0"

set "APP_PORT=%~1"
if "%APP_PORT%"=="" set "APP_PORT=8501"

title AI Governance Platform - Server
color 0A
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ============================================================================
echo   AI GOVERNANCE AND ETHICS PLATFORM - SERVER
echo ============================================================================
echo.
echo   Keep this window OPEN while demonstrating the platform.
echo   Closing it stops the application.
echo.
echo   Platform URL : http://localhost:%APP_PORT%
echo   Interpreter  : %AI_GOV_PYTHON%
echo.
echo   Accounts
echo     admin@startup.ng       admin123    Administrator
echo     governance@startup.ng  gov123      AI Governance Officer
echo     dev@startup.ng         dev123      Startup Developer
echo     auditor@startup.ng     audit123    Auditor (read-only)
echo     reporter@startup.ng    rep123      Reporter (any employee)
echo.
echo ============================================================================
echo.

if not defined AI_GOV_PYTHON (
    echo [ERROR] AI_GOV_PYTHON is not set. Please run setup_and_start.bat instead.
    goto :hold
)

if not exist "%AI_GOV_PYTHON%" (
    echo [ERROR] Python interpreter not found: %AI_GOV_PYTHON%
    goto :hold
)

REM --server.address=0.0.0.0 makes the platform reachable from a phone on the
REM same Wi-Fi, so the responsive mobile layout can be demonstrated on a real
REM handset as well as in a desktop browser.
"%AI_GOV_PYTHON%" -m streamlit run "%~dp0app.py" ^
    --server.port=%APP_PORT% ^
    --server.address=0.0.0.0 ^
    --server.headless=true ^
    --browser.gatherUsageStats=false

echo.
echo ============================================================================
echo   The server has stopped.
echo ============================================================================
echo.

:hold
pause
endlocal
exit /b 0
