@echo off
cd /d "%~dp0..\.."
set "PATH=%USERPROFILE%\.local\bin;%LOCALAPPDATA%\Programs\Microsoft VS Code\bin;%PATH%"
:: one line: update swaps this file mid-run, cmd re-reads it by byte offset
:: loading splash first, from a copy in .data (update renames app\); launch failed => ready signal closes it
(if not exist .data mkdir .data) & copy /y app\install\splash-windows.ps1 .data\ >nul & start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File .data\splash-windows.ps1 "%CD%" & uv run app/jobs.py update & uv run app/jobs.py launch || type nul > .data\window-ready & exit /b
