@echo off
cd /d D:\code\psy-analysis
if not exist logs mkdir logs
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8503 > logs\streamlit_run.log 2>&1
