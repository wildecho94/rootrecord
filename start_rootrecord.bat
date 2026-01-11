@echo off
title Rootrecord
color 0A

echo Starting Rootrecord system...
echo Press Ctrl+C to stop
echo.

echo [%date% %time%] Starting core.py ...
echo.

python core.py

echo.
echo [%date% %time%] Program stopped.
pause