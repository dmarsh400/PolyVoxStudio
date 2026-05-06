@echo off
setlocal

set "ENV_DIR=%~dp0PolyVox"
if not exist "%ENV_DIR%\Scripts\python.exe" (
	echo PolyVox environment not found. Please run install_windows.ps1 first.
	exit /b 1
)

call "%ENV_DIR%\Scripts\activate.bat"
python -m app.main

endlocal
