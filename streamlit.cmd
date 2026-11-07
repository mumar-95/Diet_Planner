@echo off
REM Project-local Streamlit shim — always uses .venv (Python 3.12).
REM Usage from this folder:  streamlit run app.py
REM Or:                       .\streamlit.cmd run app.py
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\streamlit.exe" (
  echo ERROR: .venv\Scripts\streamlit.exe not found.
  echo Run:  run.bat   or create the venv with Python 3.12 first.
  exit /b 1
)
".venv\Scripts\streamlit.exe" %*
