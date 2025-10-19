@echo off
REM ======================================================================
REM PolyVox Studio - Simple Windows Installer
REM This installer creates a virtual environment and installs PolyVox Studio
REM ======================================================================
setlocal enabledelayedexpansion

:: Set colors
set "GREEN=[92m"
set "YELLOW=[93m" 
set "BLUE=[94m"
set "RED=[91m"
set "RESET=[0m"

cls
echo.
echo %BLUE%========================================%RESET%
echo %BLUE%  PolyVox Studio Windows Installer%RESET%
echo %BLUE%========================================%RESET%
echo.

:: Check Python
echo %BLUE%Checking Python...%RESET%
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo %RED%ERROR: Python not found!%RESET%
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%✓ Python %PYTHON_VERSION% found%RESET%

:: Get installation directory  
set "INSTALL_DIR=%~dp0"
set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"
echo %GREEN%✓ Installing to: %INSTALL_DIR%%RESET%

:: Create virtual environment
echo.
echo %BLUE%Creating virtual environment...%RESET%
python -m venv venv
if %errorLevel% neq 0 (
    echo %RED%ERROR: Could not create virtual environment%RESET%
    pause
    exit /b 1
)
echo %GREEN%✓ Virtual environment created%RESET%

:: Activate and install
echo %BLUE%Installing packages...%RESET%
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements_min.txt --quiet
if %errorLevel% neq 0 (
    echo %RED%ERROR: Package installation failed%RESET%
    echo Trying with full requirements...
    python -m pip install -r requirements.txt --quiet
)
echo %GREEN%✓ Packages installed%RESET%

:: Download spaCy model
echo %BLUE%Downloading language model...%RESET%
python -m spacy download en_core_web_sm --quiet >nul 2>&1
echo %GREEN%✓ Language model ready%RESET%

:: Create launcher
echo %BLUE%Creating launcher...%RESET%
echo @echo off > PolyVoxStudio.bat
echo cd /d "%INSTALL_DIR%" >> PolyVoxStudio.bat
echo call venv\Scripts\activate.bat >> PolyVoxStudio.bat
echo python -m app.main >> PolyVoxStudio.bat
echo pause >> PolyVoxStudio.bat

:: Create desktop shortcut
set "DESKTOP=%USERPROFILE%\Desktop"
copy PolyVoxStudio.bat "%DESKTOP%\PolyVox Studio.bat" >nul
echo %GREEN%✓ Desktop shortcut created%RESET%

:: Create simple uninstaller
echo @echo off > uninstall.bat
echo echo Removing PolyVox Studio... >> uninstall.bat
echo rmdir /s /q venv >> uninstall.bat
echo del /q "%DESKTOP%\PolyVox Studio.bat" >> uninstall.bat
echo del /q uninstall.bat >> uninstall.bat
echo %GREEN%✓ Uninstaller created%RESET%

echo.
echo %GREEN%========================================%RESET%
echo %GREEN%  Installation Complete! %RESET%
echo %GREEN%========================================%RESET%
echo.
echo %YELLOW%Launch Options:%RESET%
echo   • Double-click "PolyVox Studio" on desktop
echo   • Run PolyVoxStudio.bat in this folder
echo   • Use uninstall.bat to remove
echo.
echo %BLUE%Press any key to launch PolyVox Studio...%RESET%
pause >nul

:: Launch the app
call venv\Scripts\activate.bat
python -m app.main