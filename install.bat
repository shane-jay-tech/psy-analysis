@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"

title Psy-Analysis 安装程序

echo ========================================
echo   Psy-Analysis 一键安装
echo ========================================
echo.

:: --- 确保 logs 目录存在 ---
if not exist "logs" mkdir logs

:: --- 1. 检查 Python ---
echo [1/5] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python。
    echo   请从 https://python.org 下载 Python 3.10+
    echo   安装时务必勾选 "Add Python to PATH"
    echo.
    (echo === Install Diagnosis === & echo Date: %date% %time% & echo Error: Python not found in PATH) > logs\install_diagnosis.txt
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo   Python %PY_VER% - OK
echo.

:: --- 2. 创建虚拟环境 ---
echo [2/5] 创建虚拟环境...
if exist ".venv\Scripts\python.exe" (
    echo   .venv 已存在 - 跳过
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
    echo   .venv 创建成功
)
call .venv\Scripts\activate.bat
echo.

:: --- 3. 安装依赖 ---
echo [3/5] 安装依赖（可能需要 2-5 分钟）...
pip install --upgrade pip -q 2>nul
pip install -r requirements.txt -q 2>logs\install.log
if errorlevel 1 (
    echo [警告] 部分依赖安装可能有问题，尝试继续...
    echo   详情见 logs\install.log
) else (
    echo   依赖安装完成
)
echo.

:: --- 4. 验证核心模块 ---
echo [4/5] 验证核心模块...
python -c "import streamlit; import pandas; import scipy; import statsmodels; print('核心模块 OK')" 2>logs\verify.log
if errorlevel 1 (
    echo [错误] 核心模块验证失败。
    echo   详情见 logs\verify.log 和 logs\install_diagnosis.txt
    type logs\verify.log
    (echo === Install Diagnosis === & echo Date: %date% %time% & echo Python: %PY_VER% & echo Error: Core module import failed & echo. & echo --- pip freeze --- & pip freeze & echo. & echo --- verify.log --- & type logs\verify.log) > logs\install_diagnosis.txt 2>&1
    echo.
    pause
    exit /b 1
)
echo   核心统计模块加载正常
echo.

:: --- 5. 检查可选模块 ---
echo [5/5] 检查可选模块...
python -c "import semopy; print('  semopy (SEM) - OK')" 2>nul || echo   semopy (SEM) - 未安装（可选）
python -c "import factor_analyzer; print('  factor_analyzer (EFA) - OK')" 2>nul || echo   factor_analyzer (EFA) - 未安装（可选）
python -c "import jieba; print('  jieba (中文分词) - OK')" 2>nul || echo   jieba (中文分词) - 未安装（可选）
echo.

echo ========================================
echo   安装完成！
echo.
echo   启动方式：双击 run.bat
echo   或命令行：.venv\Scripts\streamlit run app.py
echo ========================================
echo.
pause
