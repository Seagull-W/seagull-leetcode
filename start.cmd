@echo off
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel% equ 0 (
    python -X utf8 server.py --open %*
) else (
    py -3 -X utf8 server.py --open %*
)
if errorlevel 1 pause
