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

:: Check Python in multiple locations
echo %BLUE%Checking Python installation...%RESET%

:: Try common Python commands
set "PYTHON_CMD="
for %%p in (python python3 py) do (
    %%p --version >nul 2>&1
    if !errorLevel! equ 0 (
        set "PYTHON_CMD=%%p"
        goto :python_found
    )
)

:: Try Windows Python Launcher first (most reliable)
where py >nul 2>&1
if !errorLevel! equ 0 (
    py --version >nul 2>&1
    if !errorLevel! equ 0 (
        set "PYTHON_CMD=py"
        goto :python_found
    )
)

:: Try common installation paths
set "SEARCH_PATHS=%LOCALAPPDATA%\Programs\Python %PROGRAMFILES%\Python %PROGRAMFILES(X86)%\Python %APPDATA%\Local\Programs\Python"

for %%d in (%SEARCH_PATHS%) do (
    if exist "%%d" (
        for /f "delims=" %%f in ('dir /b /s "%%d\python.exe" 2^>nul') do (
            "%%f" --version >nul 2>&1
            if !errorLevel! equ 0 (
                set "PYTHON_CMD=%%f"
                goto :python_found
            )
        )
    )
)

:: Python not found anywhere
cls
echo.
echo %RED%========================================%RESET%
echo %RED%  Python Not Found!%RESET%
echo %RED%========================================%RESET%
echo.
echo %YELLOW%Python is required but could not be found.%RESET%
echo.
echo %BLUE%Please try the following:%RESET%
echo.
echo %YELLOW%Option 1: Add Python to PATH (Recommended)%RESET%
echo   1. Open Command Prompt and type: where python
echo   2. If you see a path, copy it
echo   3. Search for "Environment Variables" in Windows
echo   4. Edit "Path" and add Python's location
echo.
echo %YELLOW%Option 2: Install/Reinstall Python%RESET%
echo   1. Download from: https://python.org/downloads/
echo   2. Run installer
echo   3. CHECK "Add Python to PATH" during installation
echo   4. Restart this installer
echo.
echo %YELLOW%Option 3: Use Python Launcher%RESET%
echo   Open Command Prompt and type:
echo   py --version
echo.
echo %YELLOW%Option 4: Manual Check%RESET%
echo   Look for Python in these locations:
echo   - %LOCALAPPDATA%\Programs\Python
echo   - %PROGRAMFILES%\Python
echo   - %APPDATA%\Local\Programs\Python
echo.
echo %BLUE%For detailed help, see WINDOWS_INSTALL_README.md%RESET%
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%✓ %PYTHON_VERSION% found using: %PYTHON_CMD%%RESET%

:: Check Python version is 3.8+
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if !errorLevel! neq 0 (
    echo %RED%ERROR: Python 3.8 or higher is required%RESET%
    echo %YELLOW%Current version: %PYTHON_VERSION%%RESET%
    echo Please upgrade Python from https://python.org/downloads/
    pause
    exit /b 1
)

:: Get installation directory  
set "INSTALL_DIR=%~dp0"
set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"
echo %GREEN%✓ Installing to: %INSTALL_DIR%%RESET%

:: Create virtual environment
echo.
echo %BLUE%Creating virtual environment...%RESET%
%PYTHON_CMD% -m venv venv
if %errorLevel% neq 0 (
    echo %RED%ERROR: Could not create virtual environment%RESET%
    echo %YELLOW%Try: %PYTHON_CMD% -m pip install --upgrade virtualenv%RESET%
    pause
    exit /b 1
)
echo %GREEN%✓ Virtual environment created%RESET%

:: Activate and install
echo %BLUE%Installing packages (this may take a few minutes)...%RESET%
call venv\Scripts\activate.bat
%PYTHON_CMD% -m pip install --upgrade pip --quiet
%PYTHON_CMD% -m pip install -r requirements_min.txt --quiet
if %errorLevel% neq 0 (
    echo %YELLOW%Minimal requirements failed. Trying full requirements...%RESET%
    %PYTHON_CMD% -m pip install -r requirements.txt --quiet
    if !errorLevel! neq 0 (
        echo %RED%ERROR: Package installation failed%RESET%
        echo %YELLOW%Check your internet connection and try again%RESET%
        pause
        exit /b 1
    )
)
echo %GREEN%✓ Packages installed%RESET%

:: Download spaCy model
echo %BLUE%Downloading language model...%RESET%
%PYTHON_CMD% -m spacy download en_core_web_md --quiet >nul 2>&1
if %errorLevel% equ 0 (
    echo %GREEN%✓ Language model ready%RESET%
) else (
    echo %YELLOW%⚠ Language model download had issues (will retry on first run)%RESET%
)

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
echo del /q PolyVoxStudio.bat >> uninstall.bat
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
