@echo off
title Rootrecord
color 0A
echo Starting Rootrecord system...
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0rootrecord"

echo [%date% %time%] Running publish_rootrecord.py...
python ..\publish_rootrecord.py

echo [%date% %time%] Starting core.py ...
echo.

python core.py

echo.
echo [%date% %time%] Program stopped.
pause