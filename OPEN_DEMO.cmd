@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing. See docs/DEMO_EDITING_GUIDE.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" demo_viewer.py %*
if errorlevel 1 pause
endlocal
