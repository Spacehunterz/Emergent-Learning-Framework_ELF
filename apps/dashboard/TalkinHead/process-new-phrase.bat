@echo off
REM Process new phrase videos for TalkinHead
REM Usage: process-new-phrase.bat [phrase_folder]
REM
REM Examples:
REM   process-new-phrase.bat              - Process all unprocessed videos
REM   process-new-phrase.bat completed    - Process only 'completed' folder
REM   process-new-phrase.bat --status     - Show what's processed

cd /d "%~dp0"

if "%1"=="" (
    echo Processing all unprocessed phrase videos...
    rembg_env\Scripts\python process_phrases.py --all
) else if "%1"=="--status" (
    rembg_env\Scripts\python process_phrases.py --status
) else if "%1"=="--all" (
    rembg_env\Scripts\python process_phrases.py --all
) else if "%1"=="--force" (
    rembg_env\Scripts\python process_phrases.py --all --force
) else (
    echo Processing phrase folder: %1
    rembg_env\Scripts\python process_phrases.py --phrase %1
)

echo.
echo Done! PNG sequences created in Phrases/[name]/[video]_frames/
pause
