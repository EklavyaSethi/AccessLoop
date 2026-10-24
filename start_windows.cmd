@echo off
rem Start AccessLoop on Windows after setup_windows.cmd. Opens http://localhost:8501
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.cmd first.
  exit /b 1
)
set PYTHONUTF8=1
".venv\Scripts\python.exe" -m streamlit run app.py %*
