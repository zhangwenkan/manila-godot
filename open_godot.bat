@echo off
setlocal
set "harbor_engine=%GODOT_EXE%"
if not defined harbor_engine set "harbor_engine=%USERPROFILE%\Desktop\Godot_v4.6.1-stable_win64.exe"
if not exist "%harbor_engine%" (
    echo Godot was not found. Set GODOT_EXE to your Godot 4.6 executable.
    pause
    exit /b 1
)
start "" "%harbor_engine%" --path "%~dp0." --editor "%~dp0demo\tropical_harbor_3d\fleet_harbor.tscn"
