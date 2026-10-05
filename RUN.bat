@echo off
rem Double-click to start HunarVaani. Keep this window open while you use it; close it to stop.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
pause
