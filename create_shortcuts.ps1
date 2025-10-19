# PolyVox Studio - Shortcut Creation Script
param(
    [string]$InstallDir,
    [string]$EnvActivation
)

# Function to create shortcuts
function Create-Shortcut {
    param(
        [string]$TargetPath,
        [string]$ShortcutPath,
        [string]$Arguments = "",
        [string]$WorkingDirectory = "",
        [string]$IconLocation = "",
        [string]$Description = ""
    )
    
    try {
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = $TargetPath
        if ($Arguments) { $Shortcut.Arguments = $Arguments }
        if ($WorkingDirectory) { $Shortcut.WorkingDirectory = $WorkingDirectory }
        if ($IconLocation) { $Shortcut.IconLocation = $IconLocation }
        if ($Description) { $Shortcut.Description = $Description }
        $Shortcut.Save()
        return $true
    }
    catch {
        Write-Host "Error creating shortcut: $_" -ForegroundColor Red
        return $false
    }
}

# Create launcher script
$LauncherScript = Join-Path $InstallDir "launch_polyvox.bat"
$LauncherContent = @"
@echo off
cd /d "$InstallDir"
$EnvActivation
python -m app.main
"@

Set-Content -Path $LauncherScript -Value $LauncherContent -Encoding ASCII

# Desktop shortcut path
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = Join-Path $DesktopPath "PolyVox Studio.lnk"

# Start Menu folder
$StartMenuPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PolyVox Studio"
if (!(Test-Path $StartMenuPath)) {
    New-Item -ItemType Directory -Path $StartMenuPath -Force | Out-Null
}
$StartMenuShortcut = Join-Path $StartMenuPath "PolyVox Studio.lnk"

# Icon path
$IconPath = Join-Path $InstallDir "assets\polyvox_splash.png"
if (!(Test-Path $IconPath)) {
    $IconPath = "shell32.dll,21"  # Default audio icon
}

# Create desktop shortcut
Write-Host "Creating desktop shortcut..." -ForegroundColor Blue
$DesktopSuccess = Create-Shortcut -TargetPath $LauncherScript -ShortcutPath $DesktopShortcut -WorkingDirectory $InstallDir -IconLocation $IconPath -Description "PolyVox Studio - Professional Audiobook Generation"

# Create start menu shortcut
Write-Host "Creating start menu entry..." -ForegroundColor Blue
$StartMenuSuccess = Create-Shortcut -TargetPath $LauncherScript -ShortcutPath $StartMenuShortcut -WorkingDirectory $InstallDir -IconLocation $IconPath -Description "PolyVox Studio - Professional Audiobook Generation"

# Create uninstaller shortcut in start menu
$UninstallerPath = Join-Path $InstallDir "uninstall.bat"
$UninstallerShortcut = Join-Path $StartMenuPath "Uninstall PolyVox Studio.lnk"
$UninstallerSuccess = Create-Shortcut -TargetPath $UninstallerPath -ShortcutPath $UninstallerShortcut -WorkingDirectory $InstallDir -Description "Uninstall PolyVox Studio"

# Report results
if ($DesktopSuccess) {
    Write-Host "✓ Desktop shortcut created successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create desktop shortcut" -ForegroundColor Red
}

if ($StartMenuSuccess) {
    Write-Host "✓ Start menu entry created successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create start menu entry" -ForegroundColor Red
}

if ($UninstallerSuccess) {
    Write-Host "✓ Uninstaller shortcut created successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create uninstaller shortcut" -ForegroundColor Red
}

# Create a nice README for the user
$ReadmePath = Join-Path $InstallDir "WINDOWS_INSTALLATION.md"
$ReadmeContent = @"
# PolyVox Studio - Windows Installation

## Installation Complete! 🎉

PolyVox Studio has been successfully installed on your system.

### How to Launch

1. **Desktop Icon**: Double-click the "PolyVox Studio" icon on your desktop
2. **Start Menu**: Search for "PolyVox Studio" in the Start Menu
3. **Manual Launch**: Run `launch_polyvox.bat` in the installation directory

### Installation Details

- **Installation Directory**: $InstallDir
- **Environment**: $($EnvActivation -replace 'call ', '')
- **Python Environment**: $(if ($EnvActivation -match 'conda') { 'Conda (polyvox)' } else { 'Virtual Environment (polyvox_env)' })

### Files Created

- Desktop shortcut: `$DesktopShortcut`
- Start menu entry: `$StartMenuPath`
- Launcher script: `$LauncherScript`
- Uninstaller: `$UninstallerPath`

### Troubleshooting

If you encounter issues:

1. **Environment Problems**: 
   - Ensure Python 3.8+ is installed and in PATH
   - For conda: `conda activate polyvox`
   - For venv: Run `polyvox_env\Scripts\activate.bat`

2. **Missing Dependencies**: 
   - Run: `pip install -r requirements.txt`
   - For spaCy models: `python -m spacy download en_core_web_sm`

3. **GPU Issues**: 
   - Check GPU compatibility in `GPU_COMPATIBILITY.md`
   - Use legacy installation if needed: `install_legacy_gpu.bat`

### Uninstalling

To remove PolyVox Studio:
- Run `uninstall.bat` in the installation directory
- Or use "Uninstall PolyVox Studio" from the Start Menu

### Support

- Documentation: See `docs/` folder
- User Guide: `PolyVox user guide.pdf`
- Issues: Check GitHub repository for support

---
*Generated on $(Get-Date)*
"@

Set-Content -Path $ReadmePath -Value $ReadmeContent -Encoding UTF8
Write-Host "✓ Installation guide created: WINDOWS_INSTALLATION.md" -ForegroundColor Green

exit 0