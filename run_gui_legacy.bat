@echo off
REM Launcher for VOX Audiobook Generator (Legacy GPU Environment)

echo Starting VOX Audiobook Generator (Legacy GPU Mode)...
echo Using environment: vox_legacy
echo.

call conda activate vox_legacy

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: vox_legacy environment not found!
    echo Please run install_legacy_gpu.bat first
    pause
    exit /b 1
)

python app\main.py
