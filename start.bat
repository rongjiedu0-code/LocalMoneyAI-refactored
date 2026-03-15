@echo off
setlocal
chcp 65001 >nul
title Local AI Money Portable

echo ========================================
echo   Local AI Money Portable
echo ========================================
echo.

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python is not found in PATH.
    echo   Please install Python 3.10+ and retry.
    pause
    exit /b 1
)
echo   Python OK

echo [2/4] Checking virtual environment...
if not exist ".venv\Scripts\activate.bat" (
    echo   Creating .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo   ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo   Virtual environment OK

set "VENV_PYTHON=.venv\Scripts\python.exe"
set "VENV_PIP=.venv\Scripts\pip.exe"

echo [3/4] Checking dependencies...
%VENV_PYTHON% -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo   Installing requirements...
    %VENV_PIP% install -r requirements.txt
    if errorlevel 1 (
        echo   ERROR: Failed to install requirements.
        pause
        exit /b 1
    )
)
echo   Dependencies OK

echo [4/4] Checking Ollama service...
call check_ollama.bat
if errorlevel 1 (
    echo.
    echo WARNING: Ollama is not running.
    echo The app can still start, but AI features may be unavailable.
    echo.
    choice /C YN /M "Continue startup"
    if errorlevel 2 exit /b 0
)

echo.
echo Select startup mode:
echo [1] Web mode (browser)
echo [2] Desktop mode
choice /C 12 /M "Choose mode"

if errorlevel 2 (
    %VENV_PYTHON% desktop_app.py
) else (
    %VENV_PYTHON% -m streamlit run app.py --server.headless true
)

if errorlevel 1 (
    echo.
    echo ERROR: App failed to start.
    echo Check app.log for details.
    pause
)
