@echo off
REM ======================================================================
REM PolyVox Studio - Windows Installation Launcher  
REM ======================================================================
setlocal enabledelayedexpansion

:: Enable ANSI color support on Windows 10+
reg add HK
echo.
echo %CYAN%██████╗  ██████╗ ██╗  ██╗   ██╗██╗   ██╗ ██████╗ ██╗  ██╗%RESET%
echo %CYAN%██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝██║   ██║██╔═══██╗╚██╗██╔╝%RESET%
echo %CYAN%██████╔╝██║   ██║██║   ╚████╔╝ ██║   ██║██║   ██║ ╚███╔╝ %RESET%
echo %CYAN%██╔═══╝ ██║   ██║██║    ╚██╔╝  ╚██╗ ██╔╝██║   ██║ ██╔██╗ %RESET%
echo %CYAN%██║     ╚██████╔╝███████╗██║    ╚████╔╝ ╚██████╔╝██╔╝ ██╗%RESET%
echo %CYAN%╚═╝      ╚═════╝ ╚══════╝╚═╝     ╚═══╝   ╚═════╝ ╚═╝  ╚═╝%RESET%
echo.
echo %MAGENTA%                    PolyVox Studio%RESET%
echo %BLUE%                Professional Audiobook Generation%RESET%
echo %CYAN%================================================================%RESET%
echo.
echo %YELLOW%Welcome to the PolyVox Studio installer!%RESET%
echo.

:: Quick Python check
python --version >nul 2>&1
if %errorLevel% neq 0 (
    py --version >nul 2>&1
    if !errorLevel! neq 0 (
        echo %RED%⚠ WARNING: Python may not be properly installed or in PATH%RESET%
        echo.
        echo %YELLOW%[T] Test Python Installation%RESET% - Run diagnostic tool
        echo %YELLOW%[H] Help with Python Setup%RESET% - Show installation guide
        echo.
    )
)

echo %BLUE%This installer will:%RESET%
echo   • Create a Python virtual environment
echo   • Install all required dependencies  
echo   • Create desktop and Start Menu shortcuts
echo   • Set up an easy uninstaller
echo.
echo %GREEN%Choose your installation method:%RESET%
echo.
echo %YELLOW%[1] Simple Installation%RESET% - Quick setup (RECOMMENDED)
echo       • Uses Python virtual environment
echo       • Creates desktop shortcut  
echo       • 5-10 minute install
echo.
echo %YELLOW%[2] Advanced Installation%RESET% - Full features (PowerShell)
echo       • Custom icon support
echo       • Start Menu integration
echo       • Requires PowerShell execution
echo.
echo %YELLOW%[3] Conda Installation%RESET% - For Anaconda users
echo       • Uses conda environment
echo       • Better dependency management
echo       • Requires conda/miniconda
echo.
echo %YELLOW%[4] Manual Installation%RESET% - Python script (cross-platform)
echo       • Direct Python installer
echo       • More control over setup
echo.
echo %YELLOW%[5] Legacy GPU Installation%RESET% - For older NVIDIA GPUs
echo       • Uses legacy CUDA/Torch pins
echo       • Runs install_legacy_gpu.bat
echo       • Pair with run_gui_legacy.bat
echo.
echo %BLUE%Troubleshooting:%RESET%
echo %YELLOW%[T] Test Python Installation%RESET% - Detect Python on your system
echo %YELLOW%[H] Help%RESET% - View troubleshooting guide
echo.
echo %YELLOW%[Q] Quit%RESET%
echo.

:choice
set /p choice=%BLUE%Enter your choice (1-5, T, H, Q): %RESET%

if /i "%choice%"=="1" goto simple
if /i "%choice%"=="2" goto advanced  
if /i "%choice%"=="3" goto conda
if /i "%choice%"=="4" goto manual
if /i "%choice%"=="5" goto legacy
if /i "%choice%"=="t" goto test
if /i "%choice%"=="h" goto help
if /i "%choice%"=="q" goto quit

echo %YELLOW%Invalid choice. Please try again.%RESET%
echo.
goto choice

:simple
cls
echo.
echo %GREEN%========================================%RESET%
echo %GREEN% Starting Simple Installation%RESET%
echo %GREEN%========================================%RESET%
echo.
if not exist "install_simple.bat" (
    echo %RED%ERROR: install_simple.bat not found!%RESET%
    pause
    goto choice
)
call install_simple.bat
goto end

:legacy
cls
echo.
echo %GREEN%========================================%RESET%
echo %GREEN% Starting Legacy GPU Installation%RESET%
echo %GREEN%========================================%RESET%
echo.
if not exist "install_legacy_gpu.bat" (
    echo %RED%ERROR: install_legacy_gpu.bat not found in this folder!%RESET%
    echo %YELLOW%Tip: Make sure you're running this from the PolyVox Studio folder.%RESET%
    pause
    goto choice
)
call install_legacy_gpu.bat
if %errorLevel% neq 0 (
    echo.
    echo %RED%Legacy GPU installation reported an error.%RESET%
    echo %YELLOW%Please review the output above and try again.%RESET%
    pause
    goto choice
)
echo.
echo %GREEN%Legacy GPU environment installed.%RESET%
echo.
if exist "run_gui_legacy.bat" (
    set /p runlegacy=%BLUE%Launch the Legacy GUI now? (Y/N): %RESET%
    if /i "!runlegacy!"=="Y" (
        call run_gui_legacy.bat
        goto end
    )
)
goto end

:advanced
cls
echo.
echo %GREEN%========================================%RESET%
echo %GREEN% Starting Advanced Installation%RESET%
echo %GREEN%========================================%RESET%
echo.
if not exist "install_advanced.ps1" (
    echo %YELLOW%install_advanced.ps1 not found. Using simple installation...%RESET%
    timeout /t 2 >nul
    call install_simple.bat
    goto end
)
powershell -ExecutionPolicy Bypass -File "install_advanced.ps1"
if %errorLevel% neq 0 (
    echo.
    echo %YELLOW%PowerShell installation encountered an issue.%RESET%
    echo %YELLOW%Falling back to simple installation...%RESET%
    timeout /t 3 >nul
    call install_simple.bat
)
goto end

:conda
cls
echo.
echo %GREEN%========================================%RESET%
echo %GREEN% Starting Conda Installation%RESET%
echo %GREEN%========================================%RESET%
echo.
conda --version >nul 2>&1
if %errorLevel% neq 0 (
    echo %RED%ERROR: Conda not found!%RESET%
    echo.
    echo %YELLOW%Conda/Miniconda is required for this installation method.%RESET%
    echo Download from: https://docs.conda.io/en/latest/miniconda.html
    echo.
    echo %BLUE%Falling back to simple installation...%RESET%
    timeout /t 3 >nul
    call install_simple.bat
    goto end
)
if not exist "install_windows_oneclick.bat" (
    echo %YELLOW%install_windows_oneclick.bat not found. Using simple installation...%RESET%
    timeout /t 2 >nul
    call install_simple.bat
    goto end
)
call install_windows_oneclick.bat
goto end

:manual
cls
echo.
echo %GREEN%========================================%RESET%
echo %GREEN% Starting Manual Installation%RESET%
echo %GREEN%========================================%RESET%
echo.
python install.py
if %errorLevel% neq 0 (
    py install.py
)
goto end

:test
cls
echo.
echo %BLUE%Running Python Detection Tool...%RESET%
echo.
if exist "find_python.bat" (
    call find_python.bat
) else (
    echo %YELLOW%Testing Python...%RESET%
    echo.
    python --version 2>&1
    echo.
    py --version 2>&1
    echo.
    where python 2>&1
    echo.
    pause
)
goto choice

:help
cls
echo.
echo %BLUE%========================================%RESET%
echo %BLUE% Installation Help%RESET%
echo %BLUE%========================================%RESET%
echo.
echo %YELLOW%Common Issues and Solutions:%RESET%
echo.
echo %GREEN%1. "Python not found" error:%RESET%
echo    - Install Python from https://www.python.org/downloads/
echo    - During installation, CHECK "Add Python to PATH"
echo    - Restart Command Prompt after installation
echo    - Run option [T] to test Python detection
echo.
echo %GREEN%2. Permission errors:%RESET%
echo    - Right-click this file and "Run as Administrator"
echo    - Close antivirus temporarily during installation
echo.
echo %GREEN%3. Package installation fails:%RESET%
echo    - Check internet connection
echo    - Disable VPN temporarily
echo    - Try option [1] Simple Installation
echo.
echo %GREEN%4. Already have Python but installer doesn't detect it:%RESET%
echo    - Open Command Prompt and type: where python
echo    - Copy the path shown
echo    - Add to System Environment Variables PATH
echo    - Or: Reinstall Python with "Add to PATH" checked
echo.
echo %GREEN%5. Need more help:%RESET%
echo    - Read WINDOWS_INSTALL_README.md in this folder
echo    - Check docs/FAQ.md
echo    - Visit GitHub repository for support
echo.
echo %BLUE%Press any key to return to menu...%RESET%
pause >nul
goto choice

:quit
cls
echo.
echo %YELLOW%Installation cancelled.%RESET%
echo.
echo %BLUE%Need help? Run this installer again and choose option [H]%RESET%
echo %BLUE%Or read WINDOWS_INSTALL_README.md%RESET%
echo.
timeout /t 3 >nul
exit /b 0

:end
echo.
echo %CYAN%================================================================%RESET%
echo %GREEN%Thank you for choosing PolyVox Studio!%RESET%
echo.
echo %BLUE%If you encountered issues:%RESET%
echo  - Run find_python.bat to diagnose Python problems
echo  - Read WINDOWS_INSTALL_README.md for detailed help
echo  - Try running as Administrator
echo.
pause
exit /b 0
