@echo off
setlocal
cd /d "%~dp0"

if not exist backend\.venv\Scripts\python.exe goto :needsetup
if not exist frontend\node_modules goto :needsetup

netstat -ano | findstr /r /c:"127.0.0.1:8000 .*LISTENING" >nul
if errorlevel 1 (
  start "Auto-Tracker backend  (close this window to stop)" cmd /k "cd /d "%~dp0backend" && set PYTHONFAULTHANDLER=1 && .venv\Scripts\python.exe -X faulthandler -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
) else (
  echo  Backend already running on port 8000.
)

netstat -ano | findstr /r /c:":5173 .*LISTENING" >nul
if errorlevel 1 (
  start "Auto-Tracker frontend  (close this window to stop)" cmd /k "cd /d "%~dp0frontend" && npm run dev"
) else (
  echo  Frontend already running on port 5173.
)

echo  Opening http://localhost:5173 ...
timeout /t 6 /nobreak >nul
start "" http://localhost:5173
exit /b 0

:needsetup
echo.
echo  First run setup.bat (once), then start.bat.
echo.
pause
exit /b 1
