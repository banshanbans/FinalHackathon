@echo off
cd /d "%~dp0"
start "13110 Server" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0server-windows.ps1"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:13110/"
