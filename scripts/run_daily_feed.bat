@echo off
REM run_daily_feed.bat - Literature feed daily runner for Windows Task Scheduler
REM
REM Schedule via:
REM   schtasks /Create /SC DAILY /TN "PsyLiteratureFeed" /TR "D:\code\psy-analysis\scripts
un_daily_feed.bat" /ST 09:00
REM
REM Logs to data\literature_feed\logs\daily_runner.log

setlocal

REM Force ASCII-friendly codepage to avoid GBK/UTF-8 mojibake in logs.
chcp 65001 >/dev/null 2>&1

set "REPO=D:\code\psy-analysis"
set "PY=python"

cd /d "%REPO%" || (
  echo [ERROR] cannot cd to %REPO%
  exit /b 2
)

if not exist "%REPO%\data\literature_feed\logs" mkdir "%REPO%\data\literature_feed\logs"

set "LOG=%REPO%\data\literature_feed\logs\daily_runner.log"
echo. >> "%LOG%"
echo === %DATE% %TIME% === >> "%LOG%"

set "PYTHONIOENCODING=utf-8"
REM DeepSeek #5: append rather than clobber so user-installed venvs stay reachable
if defined PYTHONPATH (
  set "PYTHONPATH=%REPO%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%REPO%"
)

"%PY%" -m src.literature_feed.scheduler --json-summary --log-level INFO >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%

echo === exit=%RC% === >> "%LOG%"

endlocal & exit /b %RC%
