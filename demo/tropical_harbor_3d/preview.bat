@echo off
setlocal
rem Runs the independent water study, then closes automatically.
python "%~dp0tools\capture_desktop.py" --demo
exit /b %errorlevel%
