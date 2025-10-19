@echo off
REM ======================================================================
REM Quick Fix for "Python Not Found" Error
REM ======================================================================

color 0B
cls
echo.
echo  ================================================================
echo   PYTHON NOT FOUND - QUICK FIX TOOL
echo  ================================================================
echo.
echo  This tool will help you fix Python detection issues.
echo.
echo  [Scanning your system...]
echo.

timeout /t 2 >nul

:: Try to find Python
set "FOUND=0"

echo  Checking 'python' command...
python --version >nul 2>&1
if %errorLevel% equ 0 (
    echo  [32m [OK] 'python' command works[0m
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo       Version: %%v
    set "FOUND=1"
) else (
    echo  [31m [X] 'python' command not found[0m
)

echo.
echo  Checking 'py' command (Python Launcher)...
py --version >nul 2>&1
if %errorLevel% equ 0 (
    echo  [32m [OK] 'py' command works[0m
    for /f "tokens=*" %%v in ('py --version 2^>^&1') do echo       Version: %%v
    set "FOUND=1"
) else (
    echo  [31m [X] 'py' command not found[0m
)

echo.
echo  ================================================================
echo.

if %FOUND% equ 1 (
    color 0A
    echo  [32mGOOD NEWS: Python IS installed on your system![0m
    echo.
    echo  The installer should work. If it doesn't:
    echo.
    echo  SOLUTION 1: Run installer as Administrator
    echo    - Right-click INSTALL_WINDOWS.bat
    echo    - Select "Run as Administrator"
    echo.
    echo  SOLUTION 2: Use the working Python command
    echo    Try these in Command Prompt:
    py --version
    if %errorLevel% equ 0 (
        echo    - py -m venv venv
        echo    - venv\Scripts\activate.bat  
        echo    - pip install -r requirements.txt
        echo    - python -m app.main
    ) else (
        echo    - python -m venv venv
        echo    - venv\Scripts\activate.bat
        echo    - pip install -r requirements.txt
        echo    - python -m app.main
    )
    echo.
    echo  SOLUTION 3: Restart your computer
    echo    Sometimes Windows needs a restart to update PATH
    echo.
) else (
    color 0C
    echo  [31mPROBLEM: Python is not detected on your system[0m
    echo.
    echo  SOLUTION: Install or reinstall Python
    echo.
    echo  Step 1: Download Python
    echo    - Go to: https://www.python.org/downloads/
    echo    - Download Python 3.8 or higher
    echo.
    echo  Step 2: Install Python
    echo    - Run the installer
    echo    - [IMPORTANT] Check "Add Python to PATH"
    echo    - Click "Install Now"
    echo.
    echo  Step 3: Verify Installation
    echo    - Open NEW Command Prompt
    echo    - Type: python --version
    echo    - Should show: Python 3.x.x
    echo.
    echo  Step 4: Run PolyVox installer
    echo    - Double-click: INSTALL_WINDOWS.bat
    echo.
)

echo  ================================================================
echo.
echo  For detailed help, see: PYTHON_NOT_FOUND_FIX.md
echo.
echo  Press any key to open detailed diagnostic tool...
pause >nul

if exist "find_python.bat" (
    call find_python.bat
) else (
    echo.
    echo  Diagnostic tool not found. Here's what to check:
    echo.
    echo  1. Open Command Prompt and try these commands:
    echo     - python --version
    echo     - py --version  
    echo     - where python
    echo     - where py
    echo.
    echo  2. Check Environment Variables:
    echo     - Search Windows for "Environment Variables"
    echo     - Look for Python in the PATH variable
    echo.
    pause
)
