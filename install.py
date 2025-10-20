#!/usr/bin/env python3
"""
PolyVox Studio Installer
Cross-platform installation script with desktop icon creation
"""
import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def get_platform():
    """Detect the operating system."""
    system = platform.system().lower()
    if system == 'darwin':
        return 'mac'
    elif system == 'windows':
        return 'windows'
    else:
        return 'linux'

def run_command(cmd, shell=False):
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd.split(),
            shell=shell,
            check=True,
            capture_output=True,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing dependencies...")
    success, output = run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_min.txt'])
    if success:
        print("✅ Dependencies installed successfully!")
    else:
        print(f"❌ Error installing dependencies:\n{output}")
        return False
    return True

def download_spacy_model():
    """Download required spaCy model."""
    print("\n📚 Downloading spaCy language model...")
    success, _ = run_command([sys.executable, '-m', 'spacy', 'download', 'en_core_web_sm'])
    if success:
        print("✅ spaCy model downloaded!")
    else:
        print("⚠️  spaCy model download failed. You may need to run manually:")
        print("   python -m spacy download en_core_web_sm")
    return True

def create_desktop_icon_linux(install_dir):
    """Create desktop icon for Linux."""
    desktop_file = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=PolyVox Studio
Comment=Professional Audiobook Generation
Exec={sys.executable} -m app.main
Path={install_dir}
Icon={install_dir}/assets/polyvox_splash.png
Terminal=false
Categories=AudioVideo;Audio;Utility;
"""
    
    # User desktop directory
    desktop_dir = Path.home() / "Desktop"
    desktop_path = desktop_dir / "PolyVoxStudio.desktop"
    
    # Applications directory
    apps_dir = Path.home() / ".local" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    apps_path = apps_dir / "polyvox-studio.desktop"
    
    try:
        # Write to applications directory
        with open(apps_path, 'w') as f:
            f.write(desktop_file)
        os.chmod(apps_path, 0o755)
        
        # Write to desktop if it exists
        if desktop_dir.exists():
            with open(desktop_path, 'w') as f:
                f.write(desktop_file)
            os.chmod(desktop_path, 0o755)
            print(f"✅ Desktop icon created: {desktop_path}")
        
        print(f"✅ Application menu entry created: {apps_path}")
        return True
    except Exception as e:
        print(f"⚠️  Could not create desktop icon: {e}")
        return False

def create_desktop_icon_mac(install_dir):
    """Create desktop icon for macOS."""
    app_name = "PolyVox Studio.app"
    app_dir = Path.home() / "Applications" / app_name
    
    try:
        # Create app bundle structure
        contents_dir = app_dir / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"
        
        macos_dir.mkdir(parents=True, exist_ok=True)
        resources_dir.mkdir(parents=True, exist_ok=True)
        
        # Create launcher script
        launcher_script = f"""#!/bin/bash
cd "{install_dir}"
{sys.executable} -m app.main
"""
        launcher_path = macos_dir / "PolyVoxStudio"
        with open(launcher_path, 'w') as f:
            f.write(launcher_script)
        os.chmod(launcher_path, 0o755)
        
        # Create Info.plist
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>PolyVoxStudio</string>
    <key>CFBundleIdentifier</key>
    <string>com.polyvox.studio</string>
    <key>CFBundleName</key>
    <string>PolyVox Studio</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
</dict>
</plist>
"""
        with open(contents_dir / "Info.plist", 'w') as f:
            f.write(plist_content)
        
        # Copy icon if available
        icon_path = Path(install_dir) / "assets" / "polyvox_splash.png"
        if icon_path.exists():
            shutil.copy(icon_path, resources_dir / "icon.png")
        
        print(f"✅ Application bundle created: {app_dir}")
        print("   You can drag this to your Dock or Applications folder")
        return True
    except Exception as e:
        print(f"⚠️  Could not create application bundle: {e}")
        return False

def create_desktop_icon_windows(install_dir):
    """Create desktop shortcut for Windows."""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "PolyVox Studio.lnk")
        target = sys.executable
        wDir = install_dir
        icon = os.path.join(install_dir, "assets", "polyvox_splash.png")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.Arguments = f'-m app.main'
        shortcut.WorkingDirectory = wDir
        if os.path.exists(icon):
            shortcut.IconLocation = icon
        shortcut.save()
        
        print(f"✅ Desktop shortcut created: {path}")
        return True
    except ImportError:
        print("⚠️  winshell or pywin32 not installed. Creating batch file instead...")
        try:
            batch_file = os.path.join(os.path.expanduser("~"), "Desktop", "PolyVox Studio.bat")
            with open(batch_file, 'w') as f:
                f.write(f'@echo off\ncd /d "{install_dir}"\n"{sys.executable}" -m app.main\n')
            print(f"✅ Batch file created: {batch_file}")
            return True
        except Exception as e:
            print(f"⚠️  Could not create batch file: {e}")
            return False
    except Exception as e:
        print(f"⚠️  Could not create desktop shortcut: {e}")
        return False

def main():
    print("=" * 60)
    print("    PolyVox Studio Installer")
    print("    Many voices, one story")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Detect platform
    platform_type = get_platform()
    print(f"✅ Platform: {platform_type}")
    
    # Get installation directory
    install_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"✅ Installation directory: {install_dir}")
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Installation failed!")
        sys.exit(1)
    
    # Download spaCy model
    download_spacy_model()
    
    # Ask about desktop icon
    print("\n" + "=" * 60)
    create_icon = input("Create desktop icon/shortcut? (y/n): ").strip().lower()
    
    if create_icon == 'y':
        print("\n🎨 Creating desktop icon...")
        if platform_type == 'linux':
            create_desktop_icon_linux(install_dir)
        elif platform_type == 'mac':
            create_desktop_icon_mac(install_dir)
        elif platform_type == 'windows':
            create_desktop_icon_windows(install_dir)
    
    print("\n" + "=" * 60)
    print("✅ Installation Complete!")
    print("=" * 60)
    print("\nTo run PolyVox Studio:")
    print(f"  cd {install_dir}")
    if platform_type == 'windows':
        print("  run_gui.bat")
    else:
        print("  ./run_gui.sh")
    print("\nOr use the desktop icon if you created one.")
    print("\n📚 See USER_GUIDE.pdf for detailed instructions.")
    print("=" * 60)

if __name__ == "__main__":
    main()
