@echo off
rem Double-click to open the results dashboard in your browser (read-only).
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m easyboard
) else (
  py -3 -m easyboard
)
if errorlevel 1 (
  echo.
  echo Could not start. Install Python 3 from python.org, then double-click again.
  pause
)
