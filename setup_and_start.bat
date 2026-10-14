@echo off
REM ============================================================================
REM  AI GOVERNANCE AND ETHICS PLATFORM
REM  Ethical Guideline and Governance Framework for AI Use in Nigerian Tech
REM  Startups
REM ----------------------------------------------------------------------------
REM  setup_and_start.bat
REM
REM  Complete hands-free start-up:
REM     1. Chooses the Python interpreter (reuses your existing myenv)
REM     2. Reuses or creates a virtual environment
REM     3. Installs every dependency in requirements.txt
REM     4. Creates and seeds the SQLite database (setup_db.py)
REM     5. Starts the Streamlit server
REM     6. Opens the browser automatically
REM
REM  Interpreter priority
REM     a) an already-activated virtual environment in this window
REM     b) ..\myenv          (the shared environment next to this project)
REM     c) .\venv            (this project's own environment)
REM     d) a brand new .\venv created from the system Python 3
REM
REM  Usage:
REM     setup_and_start.bat            normal start
REM     setup_and_start.bat reset      wipe and re-seed the demo database first
REM     setup_and_start.bat fresh      ignore myenv and build a clean local venv
REM ============================================================================

setlocal EnableExtensions EnableDelayedExpansion
title AI Governance and Ethics Platform
color 0B

cd /d "%~dp0"
set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "SHARED_PY=%PROJECT_DIR%..\myenv\Scripts\python.exe"
set "APP_PORT=8501"
set "BASE_URL=http://localhost:%APP_PORT%"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "RESET_FLAG="
if /i "%~1"=="reset" set "RESET_FLAG=--reset"

set "FORCE_FRESH="
if /i "%~1"=="fresh" set "FORCE_FRESH=1"
if /i "%~2"=="fresh" set "FORCE_FRESH=1"

echo.
echo ============================================================================
echo   AI GOVERNANCE AND ETHICS PLATFORM
echo   Ethical Guideline and Governance Framework for Artificial Intelligence
echo   Use in Nigerian Tech Startups
echo ============================================================================
echo.
echo   Project folder : %PROJECT_DIR%
echo   Platform URL   : %BASE_URL%
echo.

REM ============================================================================
REM  STEP 1 - verify the project files are present
REM ============================================================================
for %%F in (app.py setup_db.py requirements.txt run_server.bat auth.py db.py risk_calculator.py audit_logger.py reports.py) do (
    if not exist "%PROJECT_DIR%%%F" (
        echo [ERROR] %%F was not found in this folder.
        echo         Please keep setup_and_start.bat inside the project folder.
        goto :fatal
    )
)

REM ============================================================================
REM  STEP 2 - choose the Python interpreter
REM ============================================================================
echo [1/6] Choosing the Python interpreter...

set "RUN_PY="
set "ENV_KIND="

if not defined FORCE_FRESH (
    if defined VIRTUAL_ENV (
        if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
            set "RUN_PY=%VIRTUAL_ENV%\Scripts\python.exe"
            set "ENV_KIND=activated virtual environment"
        )
    )
    if not defined RUN_PY (
        if exist "%SHARED_PY%" (
            set "RUN_PY=%SHARED_PY%"
            set "ENV_KIND=shared myenv environment"
        )
    )
    if not defined RUN_PY (
        if exist "%VENV_PY%" (
            set "RUN_PY=%VENV_PY%"
            set "ENV_KIND=project venv"
        )
    )
)

if not defined RUN_PY (
    echo       No usable virtual environment found - creating one.
    set "SYSTEM_PY="
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "SYSTEM_PY=py -3"
    if not defined SYSTEM_PY (
        python --version >nul 2>&1
        if not errorlevel 1 set "SYSTEM_PY=python"
    )
    if not defined SYSTEM_PY (
        echo.
        echo [ERROR] Python 3 was not found on this computer.
        echo         Install Python 3.10 or newer from https://www.python.org/downloads/
        echo         IMPORTANT: tick "Add python.exe to PATH" during installation.
        goto :fatal
    )
    echo       Creating a new virtual environment in .\venv ...
    %SYSTEM_PY% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        goto :fatal
    )
    set "RUN_PY=%VENV_PY%"
    set "ENV_KIND=newly created project venv"
)

if not exist "%RUN_PY%" (
    echo [ERROR] The chosen interpreter does not exist: %RUN_PY%
    goto :fatal
)

for /f "tokens=*" %%v in ('"%RUN_PY%" --version 2^>^&1') do set "PYVER=%%v"
echo       Using  : %RUN_PY%
echo       Source : !ENV_KIND!
echo       Version: !PYVER!

"%RUN_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo       pip missing - attempting to install it...
    "%RUN_PY%" -m ensurepip --upgrade >nul 2>&1
    "%RUN_PY%" -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] pip is not available. Run:  setup_and_start.bat fresh
        goto :fatal
    )
)

REM ============================================================================
REM  STEP 3 - install the dependencies
REM ============================================================================
echo [2/6] Installing dependencies (first run may take a few minutes)...
"%RUN_PY%" -m pip install -r "%PROJECT_DIR%requirements.txt" --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency installation failed. Check your internet connection.
    goto :fatal
)

"%RUN_PY%" -c "import streamlit, pandas, plotly" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] The required packages still cannot be imported.
    goto :fatal
)
echo       All dependencies are installed and importable.

REM ============================================================================
REM  STEP 4 - create and seed the database
REM ============================================================================
echo [3/6] Preparing the SQLite database (data\aigovtech.db)...
if defined RESET_FLAG (
    echo       RESET requested - rebuilding the database from scratch.
    "%RUN_PY%" "%PROJECT_DIR%setup_db.py" --reset
) else (
    "%RUN_PY%" "%PROJECT_DIR%setup_db.py"
)
if errorlevel 1 (
    echo.
    echo [ERROR] Database setup failed. See the messages above.
    goto :fatal
)

REM ============================================================================
REM  STEP 5 - find a free port
REM ============================================================================
echo [4/6] Checking that port %APP_PORT% is available...
set "PORT_BUSY="
for /f "tokens=*" %%a in ('netstat -ano ^| findstr /r /c:"LISTENING" ^| findstr /c:":%APP_PORT% "') do set "PORT_BUSY=1"

if defined PORT_BUSY (
    echo       [WARNING] Port %APP_PORT% is already in use - switching to 8502.
    set "APP_PORT=8502"
    set "BASE_URL=http://localhost:8502"
)

REM ============================================================================
REM  STEP 6 - launch the platform and open the browser
REM ============================================================================
echo [5/6] Starting the platform server...
set "AI_GOV_PYTHON=%RUN_PY%"
start "AI Governance Platform - Server" "%PROJECT_DIR%run_server.bat" %APP_PORT%

echo [6/6] Waiting for the server, then opening your browser...
timeout /t 12 /nobreak >nul
start "" "%BASE_URL%"

echo.
echo ============================================================================
echo   THE PLATFORM IS NOW RUNNING
echo ============================================================================
echo.
echo   URL : %BASE_URL%
echo.
echo   DEMONSTRATION ACCOUNTS (one for each role)
echo     Administrator          admin@startup.ng       admin123
echo     AI Governance Officer  governance@startup.ng  gov123
echo     Startup Developer      dev@startup.ng         dev123
echo     Auditor (read-only)    auditor@startup.ng     audit123
echo     Reporter (any staff)   reporter@startup.ng    rep123
echo.
echo   SUGGESTED DEMONSTRATION ORDER
echo     1. Sign in as the Administrator  -^> show the Compliance Dashboard
echo     2. Sign in as the Developer      -^> register an AI system
echo     3. Developer                     -^> complete the risk assessment
echo     4. Developer                     -^> complete the ethical assessment
echo     5. Sign in as the Governance Officer -^> Return the submission
echo     6. Sign in as the Reporter       -^> report an AI incident
echo     7. Sign in as the Auditor        -^> show the Audit Trail
echo.
echo   To stop     : close the "AI Governance Platform - Server" window,
echo                 then close this window.
echo   To reset    : setup_and_start.bat reset
echo.
echo ============================================================================
echo.

pause
endlocal
exit /b 0

:fatal
echo.
echo ============================================================================
echo   START-UP ABORTED
echo ============================================================================
echo.
echo   Read the error above, correct the problem and run this script again.
echo.
pause
endlocal
exit /b 1
