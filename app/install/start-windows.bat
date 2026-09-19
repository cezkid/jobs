@echo off
cd /d "%~dp0..\.."
set "PATH=%USERPROFILE%\.local\bin;%LOCALAPPDATA%\Programs\Microsoft VS Code\bin;%PATH%"
:: one line: update swaps this file mid-run, cmd re-reads it by byte offset
uv run app/jobs.py update & uv run app/jobs.py launch & exit /b
