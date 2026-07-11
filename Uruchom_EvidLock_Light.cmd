@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" ".\run_gui.py"
) else (
  echo Brak .venv. Uruchom najpierw setup_dev.ps1.
  pause
)
endlocal
