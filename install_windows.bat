@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_windows.ps1" %*
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
    echo PolyVox Studio installer finished with exit code %EXITCODE%.
) else (
    echo PolyVox Studio installer completed successfully.
)

echo.
pause

exit /b %EXITCODE%
