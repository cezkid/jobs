@echo off
:: start-windows.bat runs this when launch fails: its own console closes, nothing else says why
title CEZ Job Finder
findstr /i /c:"4551" /c:"Application Control" .data\launch-errors.log >nul 2>&1 && goto blocked
echo CEZ Job Finder could not start.
echo Open it again from the Desktop icon. If it fails twice, send a photo of this window to whoever shared CEZ Job Finder with you.
echo.
type .data\launch-errors.log 2>nul
echo.
pause
exit /b
:blocked
echo Windows blocked CEZ Job Finder from starting.
echo.
echo CEZ Job Finder runs on Python, and Windows' Smart App Control blocks programs their makers have not signed.
echo Windows can switch Smart App Control on by itself, so a computer where it worked before can block it now.
echo.
echo To use CEZ Job Finder here, Smart App Control has to be off: open Windows Security, then
echo App ^& browser control, then Smart App Control settings, and choose Off. Then open CEZ Job Finder again.
echo Turning it off removes one of Windows' protections, and Windows may not let you turn it back on without resetting the computer. It is your choice.
echo On a work or school computer, its IT team sets this - ask them instead.
echo.
pause
