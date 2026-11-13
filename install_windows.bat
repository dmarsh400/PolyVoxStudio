@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "INSTALLER=%SCRIPT_DIR%install_windows.ps1"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%INSTALLER%" (
    echo ERROR: Cannot find "%INSTALLER%".
    echo Extract all PolyVox Studio files before running the installer.
    set "EXITCODE=1"
    goto :finish
)

if not exist "%POWERSHELL%" (
    echo ERROR: Windows PowerShell was not found at "%POWERSHELL%".
    set "EXITCODE=1"
    goto :finish
)

pushd "%SCRIPT_DIR%"
if errorlevel 1 (
    echo ERROR: Cannot access the PolyVox Studio directory.
    set "EXITCODE=1"
    goto :finish
)

"%POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%INSTALLER%" %*
set "EXITCODE=%ERRORLEVEL%"
popd

:finish
echo.
if not "%EXITCODE%"=="0" (
    echo PolyVox Studio installer finished with exit code %EXITCODE%.
) else (
    echo PolyVox Studio installer completed successfully.
)

echo.
pause

exit /b %EXITCODE%
