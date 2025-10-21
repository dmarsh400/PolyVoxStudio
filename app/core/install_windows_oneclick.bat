@echo off
REM ======================================================================
REM PolyVox Studio - One-Click Windows Installer
REM ======================================================================
setlocal enabledelayedexpansion

:: Set colors for output
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "MAGENTA=[95m"
set "CYAN=[96m"
set "WHITE=[97m"
set "RESET=[0m"

cls
echo %CYAN%======================================================================%RESET%
echo %MAGENTA%    PolyVox Studio - One-Click Windows Installer%RESET%
echo %CYAN%    Many voices, one story%RESET%
echo %CYAN%======================================================================%RESET%
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo %YELLOW%Note: Running without administrator privileges%RESET%
    echo %YELLOW%Some features may require manual setup%RESET%
    echo.
)

:: Get installation directory
set "INSTALL_DIR=%~dp0"
set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"
echo %GREEN%Installation directory: %INSTALL_DIR%%RESET%
echo.

:: Check for Python
echo %BLUE%Checking Python installation...%RESET%
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo %RED%ERROR: Python not found!%RESET%
    echo Please install Python 3.8 or higher from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%Python %PYTHON_VERSION% found%RESET%

:: Check for conda/miniconda
echo %BLUE%Checking for Conda...%RESET%
conda --version >nul 2>&1
if %errorLevel% neq 0 (
    echo %YELLOW%Conda not found. Proceeding with pip installation...%RESET%
    set USE_CONDA=false
) else (
    echo %GREEN%Conda found%RESET%
    set USE_CONDA=true
)

echo.
echo %CYAN%======================================================================%RESET%
echo %MAGENTA%Setting up PolyVox Studio environment...%RESET%
echo %CYAN%======================================================================%RESET%

if "%USE_CONDA%"=="true" (
    :: Use conda environment
    echo %BLUE%Creating conda environment 'polyvox'...%RESET%
    call conda env create -f environment.yml -n polyvox 2>nul
    if !errorLevel! neq 0 (
        echo %YELLOW%Environment may already exist. Updating...%RESET%
        call conda env update -f environment.yml -n polyvox
    )
    
    echo %BLUE%Activating environment...%RESET%
    call conda activate polyvox
    if !errorLevel! neq 0 (
        echo %RED%ERROR: Could not activate conda environment%RESET%
        pause
        exit /b 1
    )
    
    set "ENV_ACTIVATION=call conda activate polyvox"
) else (
    :: Use pip with virtual environment
    echo %BLUE%Creating Python virtual environment...%RESET%
    python -m venv polyvox_env
    if !errorLevel! neq 0 (
        echo %RED%ERROR: Could not create virtual environment%RESET%
        pause
        exit /b 1
    )
    
    echo %BLUE%Activating virtual environment...%RESET%
    call polyvox_env\Scripts\activate.bat
    if !errorLevel! neq 0 (
        echo %RED%ERROR: Could not activate virtual environment%RESET%
        pause
        exit /b 1
    )
    
    echo %BLUE%Installing dependencies...%RESET%
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if !errorLevel! neq 0 (
        echo %RED%ERROR: Failed to install dependencies%RESET%
        pause
        exit /b 1
    )
    
    set "ENV_ACTIVATION=call "%INSTALL_DIR%\polyvox_env\Scripts\activate.bat""
)

:: Download spaCy models
echo %BLUE%Downloading spaCy language models...%RESET%
python -m spacy download en_core_web_md || python -m spacy download en_core_web_sm
if !errorLevel! neq 0 (
    echo %YELLOW%Warning: spaCy model download failed. You may need to run this manually later.%RESET%
)

echo.
echo %CYAN%======================================================================%RESET%
echo %MAGENTA%Creating desktop shortcut and start menu entry...%RESET%
echo %CYAN%======================================================================%RESET%

:: Call PowerShell script to create shortcuts
powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcuts.ps1" -InstallDir "%INSTALL_DIR%" -EnvActivation "%ENV_ACTIVATION%"
if !errorLevel! neq 0 (
    echo %YELLOW%Warning: Could not create shortcuts via PowerShell. Creating basic shortcuts...%RESET%
    call :CreateBasicShortcuts
)

:: Create uninstaller
echo %BLUE%Creating uninstaller...%RESET%
call :CreateUninstaller

echo.
echo %CYAN%======================================================================%RESET%
echo %GREEN%Installation Complete!%RESET%
echo %CYAN%======================================================================%RESET%
echo.
echo %GREEN%✓ PolyVox Studio has been installed successfully%RESET%
echo %GREEN%✓ Desktop shortcut created%RESET%
echo %GREEN%✓ Start menu entry created%RESET%
echo %GREEN%✓ Uninstaller created%RESET%
echo.
echo %BLUE%You can now:%RESET%
echo   • Double-click the desktop icon to launch PolyVox Studio
echo   • Find it in your Start Menu under "PolyVox Studio"
echo   • Run uninstall.bat to remove the installation
echo.
echo %YELLOW%Press any key to launch PolyVox Studio now...%RESET%
pause >nul

:: Launch the application
%ENV_ACTIVATION% && python -m app.main
exit /b 0

:CreateBasicShortcuts
:: Create basic batch file shortcut
echo @echo off > "%USERPROFILE%\Desktop\PolyVox Studio.bat"
echo cd /d "%INSTALL_DIR%" >> "%USERPROFILE%\Desktop\PolyVox Studio.bat"
echo %ENV_ACTIVATION% >> "%USERPROFILE%\Desktop\PolyVox Studio.bat"
echo python -m app.main >> "%USERPROFILE%\Desktop\PolyVox Studio.bat"
echo pause >> "%USERPROFILE%\Desktop\PolyVox Studio.bat"
echo %GREEN%Basic desktop shortcut created%RESET%
goto :eof

:CreateUninstaller
echo @echo off > uninstall.bat
echo echo Uninstalling PolyVox Studio... >> uninstall.bat
if "%USE_CONDA%"=="true" (
    echo conda env remove -n polyvox >> uninstall.bat
) else (
    echo rmdir /s /q polyvox_env >> uninstall.bat
)
echo del /q "%USERPROFILE%\Desktop\PolyVox Studio.lnk" 2^>nul >> uninstall.bat
echo del /q "%USERPROFILE%\Desktop\PolyVox Studio.bat" 2^>nul >> uninstall.bat
echo rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\PolyVox Studio" 2^>nul >> uninstall.bat
echo echo PolyVox Studio uninstalled. >> uninstall.bat
echo del /q uninstall.bat >> uninstall.bat
goto :eof