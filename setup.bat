@echo off
setlocal
cd /d "%~dp0"
echo.
echo  Auto-Tracker setup (first time only, takes a few minutes)
echo  =======================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo  [!] Python not found. Install Python 3.10 from python.org,
  echo      tick "Add python.exe to PATH", restart the PC, then run this again.
  goto :fail
)
py -3.10 --version >nul 2>nul
if errorlevel 1 (
  echo  [!] Python 3.10 not found. Install it from:
  echo      https://www.python.org/downloads/release/python-31011/
  goto :fail
)
where npm >nul 2>nul
if errorlevel 1 (
  echo  [!] Node.js not found. Install the LTS version from nodejs.org,
  echo      restart the PC, then run this again.
  goto :fail
)

if not exist backend\.venv\Scripts\python.exe (
  echo  - Creating the Python environment...
  py -3.10 -m venv backend\.venv || goto :fail
)
set PY=backend\.venv\Scripts\python.exe

echo  - Installing Python packages (big download the first time)...
%PY% -m pip install --upgrade pip --quiet || goto :fail
%PY% -m pip install -r backend\requirements.txt --quiet || goto :fail

where nvidia-smi >nul 2>nul
if not errorlevel 1 (
  %PY% -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" >nul 2>nul
  if errorlevel 1 (
    echo  - NVIDIA card found: installing the GPU version of PyTorch...
    %PY% -m pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu124 --quiet || goto :fail
  )
)

echo  - Downloading face models and test videos...
%PY% backend\scripts\fetch_assets.py || goto :fail

echo  - Installing the web page dependencies...
pushd frontend
call npm install --no-fund --no-audit || (popd & goto :fail)
popd

echo.
echo  Done. Double-click start.bat to run the app.
echo.
pause
exit /b 0

:fail
echo.
echo  Setup did not finish. Read the message above, fix it, and run setup.bat again.
echo.
pause
exit /b 1
