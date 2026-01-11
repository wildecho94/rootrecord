@echo off
title Rootrecord - Auto-Restart Wrapper
color 0A

echo Starting Rootrecord system...
echo Press Ctrl+C to safely stop (will restart after a short delay)
echo.

:restart

    REM Clear screen for cleaner look (optional)
    cls

    echo [%date% %time%] Starting core.py ...
    echo.

    REM Actually run your main program
    python core.py

    REM If we reach here → program was stopped (Ctrl+C or crash)
    echo.
    echo [%date% %time%] Program stopped. Restarting in 5 seconds...
    echo (Press Ctrl+C again quickly to fully exit the batch)

    REM Short delay before restart (prevents super-fast spam-restarts)
    timeout /t 5 /nobreak >nul

    echo.
    goto restart