@echo off
REM TalkinHead Launcher for Windows
REM Launches PyQt5 overlay in a way that preserves GUI display

cd /d "%~dp0"

REM Use pythonw (windowless) to avoid console, or python if pythonw not available
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw main.py
) else (
    start "" python main.py
)
