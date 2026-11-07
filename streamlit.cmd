@echo off
REM Project-local Streamlit shim — always uses .venv (Python 3.12).
REM Usage from this folder:  .\streamlit.cmd run app.py
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\streamlit.exe" (
  echo ERROR: .venv\Scripts\streamlit.exe not found.
  echo Run:  run.bat   or create the venv with Python 3.12 first.
  exit /b 1
)

REM Force a browser tab for local runs (config.toml keeps headless=true for Cloud).
set "EXTRA="
echo %* | findstr /I /C:"run " >nul
if not errorlevel 1 (
  echo %* | findstr /I /C:"--server.headless" >nul
  if errorlevel 1 set "EXTRA=--server.headless false"
)

".venv\Scripts\streamlit.exe" %* %EXTRA%
