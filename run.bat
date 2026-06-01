@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

title Psychology Research Tool

echo ========================================
echo   Psychology Research Tool
echo ========================================
echo.

:: --- 1. Kill old process on port 8501 ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
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
start "" /b cmd /c "streamlit run app.py --server.headless true > logs\streamlit_run.log 2>&1"

:: --- 4. Wait for port 8501 to be ready (max 30s) ---
set /a WAIT=0
:WAIT_LOOP
netstat -ano | findstr ":8501" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 goto READY
set /a WAIT+=1
if !WAIT! geq 30 goto TIMEOUT
timeout /t 1 /nobreak >nul
goto WAIT_LOOP

:READY
echo Server ready. Opening browser...
timeout /t 1 /nobreak >nul
start "" http://localhost:8501

echo.
echo ========================================
echo   Server is running at http://localhost:8501
echo   Close this window to stop the app.
echo ========================================
echo.

:: --- 5. Keep window open; closing it kills streamlit too ---
:HOLD
timeout /t 30 /nobreak >nul
netstat -ano | findstr ":8501" | findstr "LISTENING" >nul 2>&1
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
pause
goto END

:END
:: Best-effort cleanup
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
endlocal
