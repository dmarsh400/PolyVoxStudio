<#!
.SYNOPSIS
    PolyVox Studio Windows installer.
.DESCRIPTION
    Creates a virtual environment named "PolyVox", installs an appropriate
    PyTorch wheel for the selected GPU runtime (including legacy CUDA 11.8),
    and fetches the remaining Python dependencies.
!>

param(
    [string]$Python = "py"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envName = "PolyVox"
$envDir = Join-Path $projectRoot $envName
$pythonArgs = @("-3")

function Ensure-Python {
    param([string]$Executable)
    if ($Executable -eq "py") {
        try {
            & $Executable @("-3", "-c", "import sys; assert sys.version_info >= (3,9)")
            return @($Executable, "-3")
        } catch {
            Write-Error "Python launcher 'py -3' not found or too old. Install Python 3.9+ from https://python.org" -ErrorAction Stop
        }
    }

    try {
        & $Executable "-c" "import sys; assert sys.version_info >= (3,9)"
        return @($Executable)
    } catch {
        Write-Error "Python executable '$Executable' not found or version < 3.9." -ErrorAction Stop
    }
}

function Prompt-TorchRuntime {
    Write-Host "Select the PyTorch runtime for your GPU:" -ForegroundColor Cyan
    Write-Host "  [1] CUDA 11.8  (legacy NVIDIA, driver >= 520)"
    Write-Host "  [2] CUDA 12.1  (recent NVIDIA, driver >= 535)"
    Write-Host "  [3] CPU only   (no NVIDIA GPU)"
    $choice = Read-Host "Enter choice [1-3] (default 1)"
    switch ($choice) {
        "2" { return @{ Suffix = "cu121"; Index = "https://download.pytorch.org/whl/cu121" } }
        "3" { return @{ Suffix = "cpu"; Index = "https://download.pytorch.org/whl/cpu" } }
        default { return @{ Suffix = "cu118"; Index = "https://download.pytorch.org/whl/cu118" } }
    }
}

function New-Venv {
    param([string[]]$PyCmd)
    if (Test-Path $envDir) {
        $answer = Read-Host "Existing environment detected at $envDir. Recreate? [y/N]"
        if ($answer -match '^[Yy]$') {
            Remove-Item -Recurse -Force $envDir
        } else {
            Write-Host "Using existing environment." -ForegroundColor Yellow
            return
        }
    }
    & $PyCmd "-m" "venv" $envDir
}

function Invoke-InEnv {
    param([string]$Module, [string[]]$Arguments)
    $pythonExe = Join-Path $envDir "Scripts/python.exe"
    & $pythonExe "-m" $Module @Arguments
}

function Install-Torch {
    param($Runtime)
    Write-Host "Installing PyTorch ($($Runtime.Suffix))" -ForegroundColor Green
    Invoke-InEnv "pip" @(
        "install",
        "torch==2.1.0+$($Runtime.Suffix)",
        "torchvision==0.16.0+$($Runtime.Suffix)",
        "torchaudio==2.1.0+$($Runtime.Suffix)",
        "--index-url", $Runtime.Index
    )
}

function Install-Dependencies {
    Write-Host "Installing PolyVox core dependencies" -ForegroundColor Green
    Invoke-InEnv "pip" @("install", "-r", (Join-Path $projectRoot "requirements_min.txt"))
    Write-Host "Downloading spaCy model (en_core_web_sm)" -ForegroundColor Green
    Invoke-InEnv "spacy" @("download", "en_core_web_sm")
}

function Show-Notes {
    Write-Host "`n✅ PolyVox environment ready!" -ForegroundColor Green
    Write-Host "`nTo activate the environment in this shell:" -ForegroundColor Cyan
    Write-Host "  `"$envDir\Scripts\activate.ps1`"`n"
    Write-Host "Launch the UI with:`n  .\run_gui.bat" -ForegroundColor Cyan
    Write-Host "`nIf FFmpeg or Tesseract are missing, install them via:`n  winget install ffmpeg.ffmpeg`n  winget install UB-Mannheim.TesseractOCR" -ForegroundColor Yellow
}

Write-Host "==========================================="
Write-Host " PolyVox Studio Windows Installer" -ForegroundColor Cyan
Write-Host "==========================================="

$pyCmd = Ensure-Python -Executable $Python
$runtime = Prompt-TorchRuntime
New-Venv -PyCmd $pyCmd
Invoke-InEnv "pip" @("install", "--upgrade", "pip", "setuptools", "wheel")
Install-Torch -Runtime $runtime
Install-Dependencies
Show-Notes
