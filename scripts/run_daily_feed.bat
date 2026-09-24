@echo off
REM run_daily_feed.bat - Literature feed daily runner for Windows Task Scheduler
REM
REM Schedule via: <ROOT> stands for the folder that holds this repo, i.e. the parent
REM of the folder this script sits in (the script derives its own root from %~dp0).
REM   schtasks /Create /SC DAILY /TN "PsyLiteratureFeed" /TR "<ROOT>\scripts\run_daily_feed.bat" /ST 09:00
REM
REM Logs to data\literature_feed\logs\daily_runner.log

setlocal

REM Force ASCII-friendly codepage to avoid GBK/UTF-8 mojibake in logs.
REM s924-14 (2026-09-25): the POSIX bit-bucket idiom used here before is not valid
REM under cmd, so the redirect could not be opened and chcp never actually ran.
REM The cmd null device is NUL, hence the form below.
chcp 65001 >nul 2>&1

REM s924-14 (2026-09-25): the repo root is now derived from the location of this
REM script itself instead of a hardcoded drive letter, so a moved checkout or another
REM drive cannot point the daily job at a different tree (same rationale as the .venv
REM pin right below). The %%~fI qualifier normalizes the "%~dp0.." tail so that the
REM LOG and PYTHONPATH values stay plain absolute paths.
for %%I in ("%~dp0..") do set "REPO=%%~fI"
REM s923-11 (2026-09-23): pin the interpreter to THIS repo's .venv instead of whatever
REM "python" happens to resolve to on PATH. The supported env is the one built from
REM requirements.txt / requirements-lock.txt; the global interpreter here already drifts
REM (sklearn 1.5.2 in .venv vs 1.9.1 globally), so a PATH-based run executes the
REM extraction/analysis face on unlocked versions -- silent drift is worse than a loud
REM failure. %~dp0 keeps the anchor relative to this file, so a repo move or a drive
REM letter change cannot quietly point the daily job at another tree.
REM Exit code 3 = wrapper-level failure (the CLI itself uses 0/1/2; the cd guard uses 2).
for %%I in ("%~dp0..\.venv\Scripts\python.exe") do set "VENV_PY=%%~fI"
if not exist "%VENV_PY%" (
  echo [ERROR] venv python not found: %VENV_PY%
  echo Fix: python -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 3
)
set "PY=%VENV_PY%"

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
