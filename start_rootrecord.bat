@echo off
title RootRecord
color 0A
echo Starting RootRecord system...
echo Press Ctrl+C to stop
echo.

cd /d "I:\RootRecord"

:: Use your confirmed Python launcher
set PYTHON_LAUNCHER=C:\Users\Alexrs94\AppData\Local\Programs\Python\Launcher\py.exe

echo [%date% %time%] Running publish_rootrecord.py...
"%PYTHON_LAUNCHER%" publish_rootrecord.py

echo [%date% %time%] Starting core.py ...
echo.

"%PYTHON_LAUNCHER%" core.py

echo.
echo [%date% %time%] Program stopped.
pause