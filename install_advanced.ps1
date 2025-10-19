# Advanced PolyVox Studio Installer
# This PowerShell script creates a complete installation with proper shortcuts and icons

param(
    [switch]$Silent,
    [string]$InstallPath = $PSScriptRoot
)

# Set colors for console output
$Colors = @{
    Red = "Red"
    Green = "Green" 
    Yellow = "Yellow"
    Blue = "Cyan"
    Magenta = "Magenta"
}

function Write-ColorText {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Test-Prerequisites {
    Write-ColorText "`n🔍 Checking prerequisites..." -Color $Colors.Blue
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorText "✅ Python found: $pythonVersion" -Color $Colors.Green
        } else {
            throw "Python not found"
        }
    } catch {
        Write-ColorText "❌ Python not found or not in PATH" -Color $Colors.Red
        Write-ColorText "Please install Python 3.8+ from https://python.org" -Color $Colors.Yellow
        return $false
    }
    
    # Check pip
    try {
        python -m pip --version | Out-Null
        Write-ColorText "✅ Pip is available" -Color $Colors.Green
    } catch {
        Write-ColorText "❌ Pip not available" -Color $Colors.Red
        return $false
    }
    
    return $true
}

function Install-Dependencies {
    Write-ColorText "`n📦 Setting up environment..." -Color $Colors.Blue
    
    # Create virtual environment
    Write-ColorText "Creating virtual environment..." -Color $Colors.Blue
    python -m venv polyvox_env
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "❌ Failed to create virtual environment" -Color $Colors.Red
        return $false
    }
    
    # Activate environment
    $activateScript = Join-Path $InstallPath "polyvox_env\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
    } else {
        Write-ColorText "❌ Could not activate virtual environment" -Color $Colors.Red
        return $false
    }
    
    # Upgrade pip
    Write-ColorText "Upgrading pip..." -Color $Colors.Blue
    python -m pip install --upgrade pip --quiet
    
    # Install requirements
    $reqFile = Join-Path $InstallPath "requirements_min.txt"
    if (Test-Path $reqFile) {
        Write-ColorText "Installing minimal requirements..." -Color $Colors.Blue
        python -m pip install -r $reqFile --quiet
    } else {
        $reqFile = Join-Path $InstallPath "requirements.txt"
        Write-ColorText "Installing full requirements..." -Color $Colors.Blue
        python -m pip install -r $reqFile --quiet
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "❌ Failed to install requirements" -Color $Colors.Red
        return $false
    }
    
    # Download spaCy model
    Write-ColorText "Downloading spaCy language model..." -Color $Colors.Blue
    python -m spacy download en_core_web_sm --quiet
    
    Write-ColorText "✅ Environment setup complete" -Color $Colors.Green
    return $true
}

function New-Icon {
    param([string]$SourceImage, [string]$OutputIcon)
    
    # Create a simple icon converter using .NET
    try {
        Add-Type -AssemblyName System.Drawing
        $img = [System.Drawing.Image]::FromFile($SourceImage)
        $icon = [System.Drawing.Icon]::FromHandle(([System.Drawing.Bitmap]$img).GetHicon())
        $fileStream = [System.IO.File]::Create($OutputIcon)
        $icon.Save($fileStream)
        $fileStream.Close()
        $icon.Dispose()
        $img.Dispose()
        return $true
    } catch {
        Write-ColorText "Warning: Could not create icon file" -Color $Colors.Yellow
        return $false
    }
}

function New-Shortcuts {
    Write-ColorText "`n🔗 Creating shortcuts..." -Color $Colors.Blue
    
    # Create launcher script
    $launcherPath = Join-Path $InstallPath "launch.bat"
    $launcherContent = @"
@echo off
cd /d "$InstallPath"
call polyvox_env\Scripts\activate.bat
python -m app.main
pause
"@
    Set-Content -Path $launcherPath -Value $launcherContent
    
    # Try to create icon from PNG
    $iconSource = Join-Path $InstallPath "assets\polyvox_splash.png"
    $iconPath = Join-Path $InstallPath "polyvox.ico"
    
    if ((Test-Path $iconSource) -and (New-Icon -SourceImage $iconSource -OutputIcon $iconPath)) {
        Write-ColorText "✅ Custom icon created" -Color $Colors.Green
    } else {
        $iconPath = "shell32.dll,21"  # Default audio icon
    }
    
    # Desktop shortcut
    try {
        $WshShell = New-Object -ComObject WScript.Shell
        $desktopPath = $WshShell.SpecialFolders("Desktop")
        $shortcut = $WshShell.CreateShortcut("$desktopPath\PolyVox Studio.lnk")
        $shortcut.TargetPath = $launcherPath
        $shortcut.WorkingDirectory = $InstallPath
        $shortcut.IconLocation = $iconPath
        $shortcut.Description = "PolyVox Studio - Professional Audiobook Generation"
        $shortcut.Save()
        Write-ColorText "✅ Desktop shortcut created" -Color $Colors.Green
    } catch {
        Write-ColorText "⚠️  Could not create desktop shortcut" -Color $Colors.Yellow
    }
    
    # Start Menu shortcut
    try {
        $startMenuPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
        $polyvoxFolder = Join-Path $startMenuPath "PolyVox Studio"
        New-Item -ItemType Directory -Path $polyvoxFolder -Force | Out-Null
        
        $startShortcut = $WshShell.CreateShortcut("$polyvoxFolder\PolyVox Studio.lnk")
        $startShortcut.TargetPath = $launcherPath
        $startShortcut.WorkingDirectory = $InstallPath
        $startShortcut.IconLocation = $iconPath
        $startShortcut.Description = "PolyVox Studio - Professional Audiobook Generation"
        $startShortcut.Save()
        
        # Uninstaller shortcut
        $uninstallerPath = Join-Path $InstallPath "uninstall.bat"
        $uninstallShortcut = $WshShell.CreateShortcut("$polyvoxFolder\Uninstall.lnk")
        $uninstallShortcut.TargetPath = $uninstallerPath
        $uninstallShortcut.WorkingDirectory = $InstallPath
        $uninstallShortcut.Save()
        
        Write-ColorText "✅ Start Menu entries created" -Color $Colors.Green
    } catch {
        Write-ColorText "⚠️  Could not create Start Menu shortcuts" -Color $Colors.Yellow
    }
}

function New-Uninstaller {
    Write-ColorText "`n🗑️  Creating uninstaller..." -Color $Colors.Blue
    
    $uninstallerContent = @"
@echo off
echo Uninstalling PolyVox Studio...
echo.

REM Remove virtual environment
if exist polyvox_env rmdir /s /q polyvox_env

REM Remove desktop shortcut
del /q "%USERPROFILE%\Desktop\PolyVox Studio.lnk" 2>nul

REM Remove start menu entries
rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\PolyVox Studio" 2>nul

REM Remove generated files
del /q launch.bat 2>nul
del /q polyvox.ico 2>nul

echo.
echo PolyVox Studio has been uninstalled.
echo You can manually delete this folder if desired: $InstallPath
pause

REM Self-delete
del /q "%~f0"
"@
    
    $uninstallerPath = Join-Path $InstallPath "uninstall.bat"
    Set-Content -Path $uninstallerPath -Value $uninstallerContent
    Write-ColorText "✅ Uninstaller created" -Color $Colors.Green
}

function New-ReadMe {
    $readmePath = Join-Path $InstallPath "INSTALLATION_INFO.txt"
    $readmeContent = @"
PolyVox Studio - Installation Information
=======================================

Installation completed on: $(Get-Date)
Installation path: $InstallPath

How to Launch:
- Desktop: Double-click "PolyVox Studio" icon
- Start Menu: Search for "PolyVox Studio"  
- Manual: Run launch.bat in installation folder

Environment: Python Virtual Environment (polyvox_env)

To uninstall: Run uninstall.bat or use Start Menu shortcut

For support, see the docs folder or user guide PDF.
"@
    Set-Content -Path $readmePath -Value $readmeContent
}

# Main installation process
Write-ColorText "`n🚀 PolyVox Studio Advanced Installer" -Color $Colors.Magenta
Write-ColorText "=====================================" -Color $Colors.Magenta

if (-not (Test-Prerequisites)) {
    Write-ColorText "`n❌ Prerequisites not met. Installation aborted." -Color $Colors.Red
    if (-not $Silent) { Read-Host "Press Enter to exit" }
    exit 1
}

Write-ColorText "`n📁 Installation path: $InstallPath" -Color $Colors.Blue

if (-not (Install-Dependencies)) {
    Write-ColorText "`n❌ Installation failed." -Color $Colors.Red
    if (-not $Silent) { Read-Host "Press Enter to exit" }
    exit 1
}

New-Shortcuts
New-Uninstaller
New-ReadMe

Write-ColorText "`n✅ Installation Complete!" -Color $Colors.Green
Write-ColorText "=========================" -Color $Colors.Green
Write-ColorText "`nPolyVox Studio is ready to use!" -Color $Colors.Blue
Write-ColorText "• Desktop shortcut available" -Color $Colors.Green
Write-ColorText "• Start Menu entry created" -Color $Colors.Green
Write-ColorText "• Uninstaller available" -Color $Colors.Green

if (-not $Silent) {
    $launch = Read-Host "`nWould you like to launch PolyVox Studio now? (y/N)"
    if ($launch -match '^[Yy]') {
        Write-ColorText "`n🎬 Launching PolyVox Studio..." -Color $Colors.Blue
        Set-Location $InstallPath
        & ".\polyvox_env\Scripts\Activate.ps1"
        python -m app.main
    }
}