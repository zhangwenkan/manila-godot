@echo off
setlocal
rem Captures the root project's single main scene, then closes automatically.
python "%~dp0tools\capture_art.py"
exit /b %errorlevel%
