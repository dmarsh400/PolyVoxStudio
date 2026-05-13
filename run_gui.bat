@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "ENV_DIR=%SCRIPT_DIR%PolyVox"
set "PYTHON_EXE=%ENV_DIR%\Scripts\python.exe"

if not exist "!PYTHON_EXE!" (
	echo ❌ PolyVox environment not found at !ENV_DIR!.
	echo    Please run install_windows.ps1 first.
	exit /b 1
)

for /f "delims=" %%i in ('"!PYTHON_EXE!" -c "import sys; print(sys.executable)"') do set "PYTHON_PATH=%%i"
echo ℹ️ Using Python: !PYTHON_PATH!

REM Check for missing dependencies and attempt auto-repair
"!PYTHON_EXE!" -c ^
  "import importlib.util; ^
   checks = {'Pillow': 'PIL', 'spaCy': 'spacy', 'PyTorch': 'torch', 'CustomTkinter': 'customtkinter'}; ^
   missing = [m for m in checks.items() if importlib.util.find_spec(m[1]) is None]; ^
   exit(len(missing))" >nul 2>&1

if errorlevel 1 (
	echo ℹ️ Missing required Python modules. Attempting automatic repair...
	"!PYTHON_EXE!" -m pip install -r "!SCRIPT_DIR!requirements_min.txt" --upgrade
	if errorlevel 1 (
		echo ❌ Failed to repair dependencies.
		echo    Recommended fix: run install_windows.ps1 again and let it finish.
		exit /b 1
	)
)

"!PYTHON_EXE!" -m app.main

endlocal
