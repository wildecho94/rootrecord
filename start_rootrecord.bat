@echo off
title Rootrecord
color 0A
echo Starting Rootrecord system...
echo Press Ctrl+C to stop
echo.

cd /d "C:\Users\Alexrs94\Desktop\programfiles\rootrecord"

echo [%date% %time%] Running publish_rootrecord.py...
python "C:\Users\Alexrs94\Desktop\programfiles\publish_rootrecord.py"

echo [%date% %time%] Starting Cloudflare Tunnel in new window...
start "Cloudflare Tunnel" cmd /k "cd /d C:\Users\Alexrs94\Desktop\programfiles\rootrecord\web && cloudflared.exe tunnel --config cloudflared-config.yml run"
timeout /t 5 >nul

echo [%date% %time%] Starting core.py ...
echo.

python core.py

echo.
echo [%date% %time%] Program stopped.
pause