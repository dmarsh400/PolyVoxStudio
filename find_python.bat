@echo off
REM ======================================================================
REM Python Detection and Troubleshooting Utility
REM ======================================================================
setlocal enabledelayedexpansion

set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RED=[91m"
set "RESET=[0m"

cls
echo.
echo %BLUE%========================================%RESET%
echo %BLUE%  Python Detection Tool%RESET%
echo %BLUE%========================================%RESET%
echo.

echo %BLUE%Searching for Python installations...%RESET%
echo.

set "FOUND_COUNT=0"

:: Method 1: Check PATH
echo %YELLOW%Method 1: Checking PATH...%RESET%
for %%p in (python python3 py) do (
    where %%p >nul 2>&1
    if !errorLevel! equ 0 (
        for /f "tokens=*" %%a in ('where %%p 2^>nul') do (
            echo   %GREEN%[FOUND]%RESET% %%p at: %%a
            for /f "tokens=*" %%v in ('%%p --version 2^>^&1') do echo          Version: %%v
            set /a FOUND_COUNT+=1
        )
    )
)

:: Method 2: Python Launcher
echo.
echo %YELLOW%Method 2: Checking Python Launcher (py)...%RESET%
py --version >nul 2>&1
if !errorLevel! equ 0 (
    for /f "tokens=*" %%v in ('py --version 2^>^&1') do (
        echo   %GREEN%[FOUND]%RESET% Python Launcher: %%v
        set /a FOUND_COUNT+=1
    )
    py -0 2>nul
) else (
    echo   %RED%[NOT FOUND]%RESET% Python Launcher not available
)

:: Method 3: Registry (Windows Store Python)
echo.
echo %YELLOW%Method 3: Checking Windows Store installations...%RESET%
where /R "%LOCALAPPDATA%\Microsoft\WindowsApps" python*.exe >nul 2>&1
if !errorLevel! equ 0 (
    for /f "tokens=*" %%a in ('where /R "%LOCALAPPDATA%\Microsoft\WindowsApps" python*.exe 2^>nul') do (
        echo   %GREEN%[FOUND]%RESET% %%a
        set /a FOUND_COUNT+=1
    )
) else (
    echo   %YELLOW%[INFO]%RESET% No Windows Store Python found
)

:: Method 4: Common install locations
echo.
echo %YELLOW%Method 4: Checking common install locations...%RESET%
set "SEARCH_LOCS=%LOCALAPPDATA%\Programs\Python;%PROGRAMFILES%\Python*;%PROGRAMFILES(X86)%\Python*;%APPDATA%\Local\Programs\Python"

for %%L in ("%LOCALAPPDATA%\Programs\Python" "%PROGRAMFILES%\Python" "%PROGRAMFILES(X86)%\Python" "%APPDATA%\Local\Programs\Python") do (
    if exist %%L (
        for /f "delims=" %%D in ('dir /b /ad %%L 2^>nul') do (
            if exist "%%L\%%D\python.exe" (
                echo   %GREEN%[FOUND]%RESET% %%L\%%D\python.exe
                for /f "tokens=*" %%v in ('"%%L\%%D\python.exe" --version 2^>^&1') do echo          Version: %%v
                set /a FOUND_COUNT+=1
            )
        )
    )
)

:: Summary
echo.
echo %BLUE%========================================%RESET%
if !FOUND_COUNT! gtr 0 (
    echo %GREEN%Found !FOUND_COUNT! Python installation(s)%RESET%
    echo.
    echo %YELLOW%If installer still fails:%RESET%
    echo 1. Try running installer as Administrator
    echo 2. Restart Command Prompt
    echo 3. Restart your computer
    echo 4. Reinstall Python with "Add to PATH" checked
) else (
    echo %RED%No Python installations found!%RESET%
    echo.
    echo %YELLOW%Installation Steps:%RESET%
    echo 1. Download from: https://www.python.org/downloads/
    echo 2. Run the installer
    echo 3. ✓ CHECK "Add Python to PATH"
    echo 4. ✓ CHECK "Install for all users" (optional)
    echo 5. Complete installation
    echo 6. Restart Command Prompt
    echo 7. Run this tool again to verify
)
echo %BLUE%========================================%RESET%
echo.

:: Environment variables check
echo %YELLOW%Current PATH variable includes:%RESET%
echo %PATH% | findstr /i "python" >nul
if !errorLevel! equ 0 (
    echo %PATH% | findstr /i "python"
) else (
    echo %RED%No Python paths found in PATH variable%RESET%
)

echo.
pause
