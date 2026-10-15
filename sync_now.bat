@echo off
REM Helper script to trigger an immediate PriceTable sync on Windows
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] python is not installed or not in your PATH.
    pause
    exit /b 1
)

python main.py --sync
echo.
pause
