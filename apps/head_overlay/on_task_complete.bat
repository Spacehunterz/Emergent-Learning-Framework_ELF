@echo off
REM Example Hook Script for Claude Code
REM Place this in your project and call it when a task completes.

echo [Hook] Task Complete - Triggering Overlay...

REM Path to the python executable (adjust if using a venv)
set PYTHON_EXE=python

REM Send "Task Complete" audio to the overlay
"%PYTHON_EXE%" "%~dp0overlay\overlay_control.py" "play_sync %~dp0characters\female\voice\samples\done_01.wav"
