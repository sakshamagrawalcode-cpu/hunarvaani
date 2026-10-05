@echo off
rem Double-click to install everything HunarVaani needs (Python, Git, Ollama, the models and the voice).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
