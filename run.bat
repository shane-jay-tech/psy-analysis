@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

title Psychology Research Tool

echo ========================================
echo   Psychology Research Tool
echo ========================================
echo.

:: --- 1. Kill old process on port 8503 ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8503" ^| findstr "LISTENING"') do (
    echo Stopping previous instance, PID %%a...
    taskkill /f /pid %%a >nul 2>&1
)

:: --- 2. Ensure venv ---
if not exist ".venv\Scripts\python.exe" (
    echo First run: creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies, this may take 2-5 minutes...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo Starting server... (please wait)
echo.

:: --- 3. Launch streamlit in background, log to file ---
if not exist "logs" mkdir logs
start "" /b cmd /c "streamlit run app.py --server.headless true --server.port 8503 > logs\streamlit_run.log 2>&1"

:: --- 4. Wait for port 8503 to be ready (max 30s) ---
set /a WAIT=0
:WAIT_LOOP
netstat -ano | findstr ":8503" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 goto READY
set /a WAIT+=1
if !WAIT! geq 30 goto TIMEOUT
timeout /t 1 /nobreak >nul
goto WAIT_LOOP

:READY
echo Server ready. Opening browser...
timeout /t 1 /nobreak >nul
start "" http://localhost:8503

echo.
echo ========================================
echo   Server is running at http://localhost:8503
echo   Close this window to stop the app.
echo ========================================
echo.

:: --- 5. Keep window open; closing it kills streamlit too ---
:HOLD
timeout /t 30 /nobreak >nul
netstat -ano | findstr ":8503" | findstr "LISTENING" >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo Streamlit stopped. Press any key to exit.
    pause >nul
    goto END
)
goto HOLD

:TIMEOUT
echo.
echo ERROR: server did not become ready within 30 seconds.
echo Check logs\streamlit_run.log for details.
echo.
echo Writing diagnostic info to logs\startup_diagnosis.txt ...
(
    echo === Startup Diagnosis ===
    echo Date: %date% %time%
    echo.
    echo --- Python ---
    python --version 2>&1
    echo Path:
    where python 2>&1
    echo.
    echo --- Venv ---
    .venv\Scripts\python.exe --version 2>&1
    echo.
    echo --- Streamlit ---
    .venv\Scripts\python.exe -c "import streamlit; print(f'streamlit {streamlit.__version__}')" 2>&1
    echo.
    echo --- Port 8503 ---
    netstat -ano | findstr ":8503" 2>&1
    echo.
    echo --- Last 20 lines of streamlit_run.log ---
    if exist logs\streamlit_run.log (
        powershell -command "Get-Content logs\streamlit_run.log -Tail 20" 2>&1
    ) else (
        echo [log file not found]
    )
) > logs\startup_diagnosis.txt 2>&1
echo Done. See logs\startup_diagnosis.txt
pause
goto END

:END
:: Best-effort cleanup
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8503" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
endlocal
