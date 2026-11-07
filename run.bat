@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\streamlit.exe" (
  echo ERROR: .venv not found or incomplete.
  echo Create it with Python 3.12:
  echo   "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo Stopping any old Streamlit on ports 8501-8503...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8501 :8502 :8503" ^| findstr LISTENING') do (
  taskkill /PID %%P /F >nul 2>&1
)

echo Starting AI Food ^& Nutrition Assistant...
echo Browser will open at http://localhost:8502
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8502"
".venv\Scripts\streamlit.exe" run app.py --server.port 8502 --server.headless false
