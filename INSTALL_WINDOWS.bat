@echo off
REM ======================================================================
REM PolyVox Studio - Windows Installation Launcher  
REM ======================================================================
setlocal

:: Set colors for output
set "GREEN=[92m"
set "BLUE=[94m"
set "YELLOW=[93m"
set "MAGENTA=[95m"
set "CYAN=[96m"
set "RESET=[0m"

cls
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
echo %BLUE%This installer will:%RESET%
echo   • Create a Python virtual environment
echo   • Install all required dependencies  
echo   • Create desktop and Start Menu shortcuts
echo   • Set up an easy uninstaller
echo.
echo %GREEN%Choose your installation method:%RESET%
echo.
echo %YELLOW%[1] Simple Installation%RESET% - Quick setup with basic features
echo %YELLOW%[2] Advanced Installation%RESET% - Full features with custom icon
echo %YELLOW%[3] Conda Installation%RESET% - Use existing conda environment
echo %YELLOW%[4] Manual Installation%RESET% - Run Python installer directly
echo.
echo %YELLOW%[Q] Quit%RESET%
echo.

:choice
set /p choice=%BLUE%Enter your choice (1-4, Q): %RESET%

if /i "%choice%"=="1" goto simple
if /i "%choice%"=="2" goto advanced  
if /i "%choice%"=="3" goto conda
if /i "%choice%"=="4" goto manual
if /i "%choice%"=="q" goto quit

echo %YELLOW%Invalid choice. Please enter 1, 2, 3, 4, or Q%RESET%
goto choice

:simple
echo.
echo %GREEN%Starting Simple Installation...%RESET%
call install_simple.bat
goto end

:advanced
echo.
echo %GREEN%Starting Advanced Installation...%RESET%
powershell -ExecutionPolicy Bypass -File "install_advanced.ps1"
if %errorLevel% neq 0 (
    echo %YELLOW%PowerShell installation failed. Trying simple method...%RESET%
    call install_simple.bat
)
goto end

:conda
echo.
echo %GREEN%Starting Conda Installation...%RESET%
call install_windows_oneclick.bat
goto end

:manual
echo.
echo %GREEN%Running Python Installer...%RESET%
python install.py
goto end

:quit
echo.
echo %YELLOW%Installation cancelled.%RESET%
goto end

:end
echo.
echo %CYAN%================================================================%RESET%
echo %GREEN%Thank you for choosing PolyVox Studio!%RESET%
echo.
pause