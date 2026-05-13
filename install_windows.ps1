<#!
.SYNOPSIS
    PolyVox Studio Windows installer.
.DESCRIPTION
    Creates a virtual environment named "PolyVox", installs an appropriate
    PyTorch wheel for the selected GPU runtime (including legacy CUDA 11.8),
    and fetches the remaining Python dependencies.
#>

param(
    [string]$Python = "py",
    [switch]$AutoTorch
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envName = "PolyVox"
$envDir = Join-Path $projectRoot $envName
$pythonArgs = @("-3")

function Ensure-Python {
    param([string]$Executable)

    $minimum = 'import sys; assert sys.version_info >= (3,9)'
    $candidates = @()

    if ($Executable -eq "py") {
        $candidates += ,@("py", "-3")
        $candidates += ,@("py", "-3.11")
        $candidates += ,@("py", "-3.10")
        $candidates += ,@("py", "-3.9")
    } elseif ($Executable) {
        $candidates += ,@($Executable)
    }

    $candidates += ,@("python")
    $candidates += ,@("python3")
    $candidates += ,@("python3.11")
    $candidates += ,@("python3.10")
    $candidates += ,@("python3.9")

    $unique = @()
    $seen = @{}
    foreach ($entry in $candidates) {
        if (-not $entry) { continue }
        $key = $entry -join ' '
        if (-not $seen.ContainsKey($key)) {
            $seen[$key] = $true
            $unique += ,$entry
        }
    }

    if (-not $unique) {
        Write-Error "No Python executables to test. Install Python 3.9+ from https://python.org" -ErrorAction Stop
    }

    $preferredKey = $unique[0] -join ' '
    foreach ($entry in $unique) {
        $exe = $entry[0]
        $args = @()
        if ($entry.Count -gt 1) {
            $args = $entry[1..($entry.Count - 1)]
        }

        $testArgs = $args + @("-c", $minimum)
        try {
            & $exe @($testArgs)
            $returnValue = @($exe) + $args
            if (($entry -join ' ') -ne $preferredKey) {
                Write-Host "Python launcher 'py -3' unavailable; using '$($entry -join ' ')'." -ForegroundColor Yellow
            }
            return $returnValue
        } catch {
            continue
        }
    }

    $attempted = ($unique | ForEach-Object { "'" + ($_ -join ' ') + "'" }) -join ', '
    Write-Error "Python 3.9+ not found. Tried: $attempted. Install a supported version from https://python.org/downloads" -ErrorAction Stop
}

function Get-RuntimeOption {
    param([string]$Choice)

    switch ($Choice) {
        "2" { return @{ Choice = 2; Label = "CUDA 12.1  (recent NVIDIA, driver >= 535)"; Suffix = "cu121"; Index = "https://download.pytorch.org/whl/cu121"; TorchVersion = "2.1.0"; TorchvisionVersion = "0.16.0"; TorchaudioVersion = "2.1.0" } }
        "3" { return @{ Choice = 3; Label = "CUDA 12.8  (RTX 50-series Blackwell, driver >= 570)"; Suffix = "cu128"; Index = "https://download.pytorch.org/whl/cu128"; TorchVersion = "2.7.0"; TorchvisionVersion = "0.22.0"; TorchaudioVersion = "2.7.0" } }
        "4" { return @{ Choice = 4; Label = "CPU only   (no NVIDIA GPU)"; Suffix = "cpu"; Index = "https://download.pytorch.org/whl/cpu"; TorchVersion = "2.1.0"; TorchvisionVersion = "0.16.0"; TorchaudioVersion = "2.1.0" } }
        default { return @{ Choice = 1; Label = "CUDA 11.8  (legacy NVIDIA, driver >= 520)"; Suffix = "cu118"; Index = "https://download.pytorch.org/whl/cu118"; TorchVersion = "2.1.0"; TorchvisionVersion = "0.16.0"; TorchaudioVersion = "2.1.0" } }
    }
}

function Detect-TorchRuntime {
    $detectedChoice = "3"
    $reason = "No NVIDIA GPU detected; defaulting to CPU wheel."
    $gpuName = $null
    $driver = $null

    try {
        $controllers = Get-CimInstance Win32_VideoController -ErrorAction Stop
    } catch {
        $controllers = @()
    }

    $nvidia = $controllers | Where-Object { $_.Name -like "*NVIDIA*" }

    if ($nvidia -and $nvidia.Count -gt 0) {
        $gpuName = $nvidia[0].Name
        try {
            $smi = Get-Command "nvidia-smi.exe" -ErrorAction Stop
            $driver = (& $smi "--query-gpu=driver_version" "--format=csv,noheader" 2>$null | Select-Object -First 1)
        } catch {
            if ($nvidia[0].DriverVersion) {
                $driver = $nvidia[0].DriverVersion
            }
        }

        $driverMajor = $null
        if ($driver -and ($driver -match "(\d{3})")) {
            $driverMajor = [int]$matches[1]
        }

        if ($driverMajor -and $driverMajor -ge 570) {
            $detectedChoice = "3"
            $reason = "Detected NVIDIA driver $driverMajor (>= 570); selecting CUDA 12.8 wheel (RTX 50-series Blackwell)."
        } elseif ($driverMajor -and $driverMajor -ge 535) {
            $detectedChoice = "2"
            $reason = "Detected NVIDIA driver $driverMajor (>= 535); selecting CUDA 12.1 wheel."
        } else {
            $detectedChoice = "1"
            if ($driverMajor) {
                $reason = "Detected NVIDIA driver $driverMajor (< 535); selecting CUDA 11.8 wheel."
            } else {
                $reason = "Detected NVIDIA GPU; selecting CUDA 11.8 wheel."
            }
        }
    }

    $runtime = Get-RuntimeOption -Choice $detectedChoice
    $runtime.Reason = $reason
    if ($gpuName) { $runtime.GPUName = $gpuName }
    if ($driver) { $runtime.DriverVersion = $driver.Trim() }
    return $runtime
}

function Prompt-TorchRuntime {
    param($Detected)

    Write-Host "Select the PyTorch runtime for your GPU:" -ForegroundColor Cyan
    Write-Host "  [1] CUDA 11.8  (legacy NVIDIA, driver >= 520)"
    Write-Host "  [2] CUDA 12.1  (recent NVIDIA, driver >= 535)"
    Write-Host "  [3] CUDA 12.8  (RTX 50-series Blackwell, driver >= 570)"
    Write-Host "  [4] CPU only   (no NVIDIA GPU)"

    $defaultChoice = "1"
    if ($Detected) {
        $defaultChoice = [string]$Detected.Choice
        if ($Detected.GPUName) {
            $gpuInfo = "Detected GPU: $($Detected.GPUName)"
            if ($Detected.DriverVersion) { $gpuInfo += " (driver $($Detected.DriverVersion))" }
            Write-Host $gpuInfo -ForegroundColor Cyan
        }
        if ($Detected.Reason) {
            Write-Host $Detected.Reason -ForegroundColor DarkCyan
        }
    }

    while ($true) {
        $choice = Read-Host "Enter choice [1-4] (default $defaultChoice)"
        if ([string]::IsNullOrWhiteSpace($choice)) {
            $choice = $defaultChoice
        }
        switch ($choice) {
            "1" { return Get-RuntimeOption -Choice "1" }
            "2" { return Get-RuntimeOption -Choice "2" }
            "3" { return Get-RuntimeOption -Choice "3" }
            "4" { return Get-RuntimeOption -Choice "4" }
            default { Write-Host "Please enter 1, 2, 3, or 4." -ForegroundColor Yellow }
        }
    }
}

function New-Venv {
    param($PyCmd)
    if (Test-Path $envDir) {
        $answer = Read-Host "Existing environment detected at $envDir. Recreate? [y/N]"
        if ($answer -match '^[Yy]$') {
            Remove-Item -Recurse -Force $envDir
        } else {
            Write-Host "Using existing environment." -ForegroundColor Yellow
            return
        }
    }

    $parts = @()
    if ($PyCmd -is [System.Array]) {
        $parts = @($PyCmd)
    } elseif ($PyCmd) {
        $parts = @($PyCmd)
    }

    if (-not $parts -or -not $parts[0]) {
        Write-Error "Python command not resolved. Install Python 3.9+ from https://python.org/downloads" -ErrorAction Stop
    }

    $exe = $parts[0]
    $args = @()
    if ($parts.Count -gt 1) {
        $args = $parts[1..($parts.Count - 1)]
    }

    $venvArgs = $args + @("-m", "venv", $envDir)
    & $exe @($venvArgs)
}

function Invoke-InEnv {
    param([string]$Module, [string[]]$Arguments)
    $pythonExe = Join-Path $envDir "Scripts/python.exe"
    & $pythonExe "-m" $Module @Arguments
}

function Install-Torch {
    param($Runtime)
    Write-Host "Installing PyTorch $($Runtime.TorchVersion) ($($Runtime.Suffix))" -ForegroundColor Green
    
    # Try pinned versions first
    $pythonExe = Join-Path $envDir "Scripts/python.exe"
    & $pythonExe -m pip install `
        "torch==$($Runtime.TorchVersion)+$($Runtime.Suffix)" `
        "torchvision==$($Runtime.TorchvisionVersion)+$($Runtime.Suffix)" `
        "torchaudio==$($Runtime.TorchaudioVersion)+$($Runtime.Suffix)" `
        "--index-url" $Runtime.Index 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ Exact PyTorch wheel set not available for this Python/runtime combination." -ForegroundColor Yellow
        Write-Host "   Retrying with the latest compatible wheels from $($Runtime.Index)..." -ForegroundColor Yellow
        
        & $pythonExe -m pip install `
            "torch" `
            "torchvision" `
            "torchaudio" `
            "--index-url" $Runtime.Index 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0 -and $Runtime.Suffix -ne "cpu") {
            Write-Host "⚠️ GPU wheel installation failed. Falling back to CPU wheels so setup can complete." -ForegroundColor Yellow
            & $pythonExe -m pip install `
                "torch" `
                "torchvision" `
                "torchaudio" `
                "--index-url" "https://download.pytorch.org/whl/cpu" 2>&1 | Out-Null
            
            if ($LASTEXITCODE -ne 0) {
                Write-Error "❌ Unable to install PyTorch automatically for this environment. Try a different Python version (3.10/3.11 are safest) or re-run and select CPU mode." -ErrorAction Stop
            }
        } elseif ($LASTEXITCODE -ne 0) {
            Write-Error "❌ PyTorch installation failed. Check your Python version and try again." -ErrorAction Stop
        }
    }
}

function Install-Dependencies {
    Write-Host "Installing PolyVox core dependencies" -ForegroundColor Green
    Invoke-InEnv "pip" @("install", "-r", (Join-Path $projectRoot "requirements_min.txt"))
    Write-Host "Downloading spaCy model (en_core_web_md)" -ForegroundColor Green
    Invoke-InEnv "spacy" @("download", "en_core_web_md")
}

function Show-Notes {
    param($Runtime)
    Write-Host "`n✅ PolyVox environment ready!" -ForegroundColor Green
    Write-Host "`nInstalled PyTorch runtime:`n  $($Runtime.Suffix) ($($Runtime.Index))`n" -ForegroundColor Cyan
    Write-Host "To activate the environment in this shell:" -ForegroundColor Cyan
    Write-Host "  `"$envDir\Scripts\activate.ps1`"`n"
    Write-Host "Launch the UI with:`n  .\run_gui.bat" -ForegroundColor Cyan
    Write-Host "`nIf FFmpeg or Tesseract are missing, install them via:`n  winget install ffmpeg.ffmpeg`n  winget install UB-Mannheim.TesseractOCR" -ForegroundColor Yellow
}

Write-Host "==========================================="
Write-Host " PolyVox Studio Windows Installer" -ForegroundColor Cyan
Write-Host "==========================================="

$pyCmd = Ensure-Python -Executable $Python
$detectedRuntime = Detect-TorchRuntime
if ($AutoTorch) {
    Write-Host "Auto-selecting PyTorch runtime: $($detectedRuntime.Label)" -ForegroundColor Cyan
    if ($detectedRuntime.Reason) {
        Write-Host $detectedRuntime.Reason -ForegroundColor DarkCyan
    }
    $runtime = $detectedRuntime
} else {
    $runtime = Prompt-TorchRuntime -Detected $detectedRuntime
}
New-Venv -PyCmd $pyCmd
Invoke-InEnv "pip" @("install", "--upgrade", "pip", "setuptools", "wheel")
Install-Torch -Runtime $runtime
Install-Dependencies
Show-Notes -Runtime $runtime
