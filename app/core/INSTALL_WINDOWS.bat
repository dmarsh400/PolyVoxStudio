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
echo %YELLOW%[6] Enable GPU (CUDA 11.8)%RESET% - For modern NVIDIA GPUs (RTX/Turing/Ampere/Ada)
echo       • Uses Python venv created by Simple/Advanced install
echo       • Installs CUDA 11.8 wheels for torch/torchvision/torchaudio
echo       • Verifies GPU availability; falls back to CPU if needed
echo.
echo %BLUE%Troubleshooting:%RESET%
echo %YELLOW%[T] Test Python Installation%RESET% - Detect Python on your system
echo %YELLOW%[H] Help%RESET% - View troubleshooting guide
echo.
echo %YELLOW%[Q] Quit%RESET%
echo.

:choice
set /p choice=%BLUE%Enter your choice (1-6, T, H, Q): %RESET%

if /i "%choice%"=="1" goto simple
if /i "%choice%"=="2" goto advanced  
if /i "%choice%"=="3" goto conda
if /i "%choice%"=="4" goto manual
if /i "%choice%"=="5" goto legacy
if /i "%choice%"=="6" goto gpu
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

:gpu
cls
echo.
echo %GREEN%========================================%RESET%
echo %GREEN% Enabling GPU (CUDA 11.8) in venv%RESET%
echo %GREEN%========================================%RESET%
echo.
rem Ensure venv exists
if not exist "venv\Scripts\python.exe" (
    echo %RED%ERROR: Python virtual environment not found!%RESET%
    echo %YELLOW%Please run option [1] Simple Installation first to create venv.%RESET%
    echo %YELLOW%After that, return here to enable GPU support.%RESET%
    pause
    goto choice
)

echo %BLUE%Detecting NVIDIA GPU...%RESET%
where nvidia-smi >nul 2>&1
if %errorLevel% equ 0 (
    for /f "usebackq tokens=*" %%A in (`nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2^>nul`) do (
        echo   NVIDIA GPU detected: %%A
        goto :gpu_prompt
    )
)
wmic path win32_VideoController get Name | find /i "NVIDIA" >nul 2>&1
if %errorLevel% equ 0 (
    echo   NVIDIA GPU detected (via WMI)
) else (
    echo   %YELLOW%No NVIDIA GPU detected automatically. You can still install CUDA wheels if you know you have one.%RESET%
)

:gpu_prompt
set /p gpuyes=%BLUE%Proceed to install CUDA 11.8 PyTorch wheels into venv? (Y/N): %RESET%
if /i "%gpuyes%" NEQ "Y" (
    echo Operation cancelled.
    goto choice
)

echo.
echo %BLUE%Activating virtual environment...%RESET%
call venv\Scripts\activate.bat
if %errorLevel% neq 0 (
    echo %RED%ERROR: Could not activate virtual environment%RESET%
    pause
    goto choice
)

echo %BLUE%Removing existing torch/vision/audio (if present)...%RESET%
pip uninstall -y torch torchvision torchaudio >nul 2>&1

echo %BLUE%Installing CUDA 11.8 wheels for torch/vision/audio...%RESET%
pip install --index-url https://download.pytorch.org/whl/cu118 ^
  torch==2.1.0+cu118 torchvision==0.16.0+cu118 torchaudio==2.1.0+cu118
if %errorLevel% neq 0 (
    echo %RED%ERROR: Failed to install CUDA 11.8 wheels.%RESET%
    echo %YELLOW%Falling back to CPU-only wheels...%RESET%
    pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0
)

echo.
echo %BLUE%Verifying GPU availability...%RESET%
python -c "import torch;print('torch',torch.__version__);print('cuda available',torch.cuda.is_available());print('device count',torch.cuda.device_count());print('cuda',getattr(torch.version,'cuda',None))" 2>&1
if %errorLevel% neq 0 (
    echo %YELLOW%Warning: Verification encountered an issue. The installation may still be usable.%RESET%
)

echo.
echo %GREEN%GPU enablement step complete.%RESET%
echo %YELLOW%If cuda_available=False above, update NVIDIA drivers and try again.%RESET%
echo.
set /p launchnow=%BLUE%Launch PolyVox Studio now? (Y/N): %RESET%
if /i "%launchnow%"=="Y" (
    if exist PolyVoxStudio.bat (
        call PolyVoxStudio.bat
    ) else (
        echo Launcher not found. You can run: call venv\Scripts\activate.bat ^&^& python -m app.main
        pause
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
