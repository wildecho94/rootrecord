@echo off
title Rootrecord
color 0A
echo Starting Rootrecord system...
echo Press Ctrl+C to stop
echo.

cd /d "C:\Users\Alexrs94\Desktop\programfiles\rootrecord"

echo [%date% %time%] Running publish_rootrecord.py...
python "C:\Users\Alexrs94\Desktop\programfiles\publish_rootrecord.py"

echo [%date% %time%] Starting Web Server + Cloudflare Tunnel in new window...
start "Web + Tunnel" cmd /k "cd /d C:\Users\Alexrs94\Desktop\programfiles\rootrecord\web && python app.py & cloudflared.exe tunnel --config cloudflared-config.yml run"
timeout /t 10 >nul

echo [%date% %time%] Starting core.py ...
echo.

python core.py

echo.
echo [%date% %time%] Program stopped.
pause