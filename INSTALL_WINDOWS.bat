@echo off
REM ======================================================================
REM PolyVox Studio - Complete Fixed Installer
REM Removes color codes and ensures proper package installation
REM ======================================================================
setlocal enabledelayedexpansion

cls
echo.
echo =================================================================
echo              PolyVox Studio - Windows Installer
echo                 Professional Audiobook Generation
echo =================================================================
echo.

:: Check Python
echo [1/6] Checking Python installation...

set "PYTHON_CMD="
for %%p in (python python3 py) do (
    %%p --version >nul 2>&1
    if !errorLevel! equ 0 (
        set "PYTHON_CMD=%%p"
        goto :python_found
    )
)

cls
echo.
echo =================================================================
echo                    ERROR: Python Not Found!
echo =================================================================
echo.
echo Python 3.8 or higher is required but was not found.
echo.
echo Please install Python from: https://python.org/downloads/
echo.
echo IMPORTANT: During installation, check "Add Python to PATH"
echo.
echo For detailed help, see: PYTHON_NOT_FOUND_FIX.md
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    %PYTHON_VERSION% found
echo.

:: Check Python version
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if !errorLevel! neq 0 (
    echo ERROR: Python 3.8 or higher required
    echo Current version: %PYTHON_VERSION%
    pause
    exit /b 1
)

:: Get installation directory
set "INSTALL_DIR=%~dp0"
set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

:: Create virtual environment
echo [2/6] Creating virtual environment...
if exist venv (
    echo    Virtual environment already exists, removing old one...
    rmdir /s /q venv
)

%PYTHON_CMD% -m venv venv
if !errorLevel! neq 0 (
    echo.
    echo ERROR: Could not create virtual environment
    echo Try running: %PYTHON_CMD% -m pip install virtualenv
    pause
    exit /b 1
)
echo    Virtual environment created
echo.

:: Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
if !errorLevel! neq 0 (
    echo ERROR: Could not activate virtual environment
    pause
    exit /b 1
)
echo    Environment activated
echo.

:: Upgrade pip
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo    Pip upgraded
echo.

:: Install packages
echo [5/6] Installing packages (this may take 5-10 minutes)...
echo    Please wait, downloading and installing dependencies...
echo.

:: Try minimal requirements first
if exist requirements_min.txt (
    echo    Trying minimal requirements...
    python -m pip install -r requirements_min.txt
    if !errorLevel! equ 0 (
        echo    Minimal requirements installed successfully
        goto :packages_done
    )
)

:: Fall back to full requirements
if exist requirements.txt (
    echo    Installing full requirements...
    python -m pip install -r requirements.txt
    if !errorLevel! neq 0 (
        echo.
        echo ERROR: Package installation failed
        echo Please check your internet connection and try again
        echo.
        pause
        exit /b 1
    )
    echo    Full requirements installed successfully
)

:packages_done
echo.

:: Verify critical packages
echo    Verifying installation...
python -c "import customtkinter" >nul 2>&1
if !errorLevel! neq 0 (
    echo    WARNING: customtkinter not found, installing...
    python -m pip install customtkinter
)

python -c "import spacy" >nul 2>&1
if !errorLevel! neq 0 (
    echo    WARNING: spacy not found, installing...
    python -m pip install spacy
)

:: Download spaCy model
echo [6/6] Downloading language model...
python -m spacy download en_core_web_sm >nul 2>&1
if !errorLevel! equ 0 (
    echo    Language model downloaded
) else (
    echo    Warning: Language model download failed (will retry on first run)
)
echo.

:: Create launcher script
echo Creating launcher script...
(
echo @echo off
echo REM PolyVox Studio Launcher
echo cd /d "%INSTALL_DIR%"
echo call venv\Scripts\activate.bat
echo if %%errorLevel%% neq 0 (
echo     echo ERROR: Could not activate environment
echo     pause
echo     exit /b 1
echo ^)
echo python -m app.main
echo if %%errorLevel%% neq 0 (
echo     echo.
echo     echo ERROR: Application failed to start
echo     echo Check that all packages are installed correctly
echo     pause
echo ^)
) > PolyVoxStudio.bat

:: Create desktop shortcut
set "DESKTOP=%USERPROFILE%\Desktop"
copy /y PolyVoxStudio.bat "%DESKTOP%\PolyVox Studio.bat" >nul 2>&1
if !errorLevel! equ 0 (
    echo Desktop shortcut created: "%DESKTOP%\PolyVox Studio.bat"
) else (
    echo Warning: Could not create desktop shortcut
)
echo.

:: Create uninstaller
(
echo @echo off
echo echo Uninstalling PolyVox Studio...
echo cd /d "%INSTALL_DIR%"
echo rmdir /s /q venv
echo del /q PolyVoxStudio.bat
echo del /q "%DESKTOP%\PolyVox Studio.bat" 2^>nul
echo echo Uninstall complete
echo pause
echo del /q "%%~f0"
) > uninstall.bat

echo =================================================================
echo                  Installation Complete!
echo =================================================================
echo.
echo PolyVox Studio has been installed successfully!
echo.
echo To launch the application:
echo   1. Double-click "PolyVox Studio.bat" on your desktop
echo   2. Or run PolyVoxStudio.bat from this folder
echo.
echo To uninstall: run uninstall.bat
echo.
echo =================================================================
echo.
set /p launch="Would you like to launch PolyVox Studio now? (Y/N): "
if /i "%launch%"=="Y" (
    echo.
    echo Launching PolyVox Studio...
    echo.
    call PolyVoxStudio.bat
) else (
    echo.
    echo You can launch PolyVox Studio anytime from your desktop.
    pause
)
