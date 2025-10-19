# PolyVox Studio - Windows Installation Guide

## 🚀 One-Click Installation

**Simply double-click `INSTALL_WINDOWS.bat` and follow the prompts!**

## Installation Options

### 1. Simple Installation (Recommended)
- **File**: `install_simple.bat`
- **Best for**: Most users, quick setup
- **Features**: 
  - Creates Python virtual environment
  - Installs minimal required packages
  - Creates desktop shortcut
  - Simple uninstaller included

### 2. Advanced Installation  
- **File**: `install_advanced.ps1` 
- **Best for**: Users wanting full features
- **Features**:
  - All simple installation features
  - Custom desktop icon creation
  - Start Menu integration
  - Detailed installation report
  - Better error handling

### 3. Conda Installation
- **File**: `install_windows_oneclick.bat`
- **Best for**: Users with Anaconda/Miniconda
- **Features**:
  - Uses conda environment management
  - Supports both conda and pip fallback
  - Full environment isolation

### 4. Manual Installation
- **File**: `install.py`
- **Best for**: Developers and advanced users
- **Features**:
  - Cross-platform compatibility
  - Detailed control over installation
  - Custom configuration options

## Prerequisites

### Required
- **Python 3.8 or higher** - [Download from python.org](https://www.python.org/downloads/)
  - ⚠️ **Important**: Check "Add Python to PATH" during installation
- **At least 4GB free disk space**
- **Internet connection** for downloading dependencies

### Recommended
- **NVIDIA GPU** with CUDA support for faster processing
- **16GB RAM** for large audiobooks
- **SSD storage** for better performance

## Quick Start

1. **Download or clone** PolyVox Studio to your computer
2. **Double-click** `INSTALL_WINDOWS.bat`
3. **Choose** installation method (Simple recommended)
4. **Wait** for installation to complete
5. **Launch** from desktop icon or Start Menu

## Post-Installation

### Launching PolyVox Studio
- **Desktop**: Double-click "PolyVox Studio" icon
- **Start Menu**: Search for "PolyVox Studio"
- **Manual**: Run `launch.bat` in installation folder

### First Run Setup
1. The application will download additional language models
2. Configure your audio output preferences
3. Test with a small sample file first

## Troubleshooting

### Common Issues

**Python Not Found**
```
Solution: Install Python 3.8+ and ensure "Add to PATH" is checked
```

**Permission Errors**
```
Solution: Right-click installer and select "Run as Administrator"
```

**Package Installation Fails**
```
Solutions:
- Check internet connection
- Update pip: python -m pip install --upgrade pip
- Try different installation method
```

**GPU Not Detected**
```
Solutions:
- Install NVIDIA drivers
- Check GPU_COMPATIBILITY.md
- Use CPU mode if needed
```

**Audio Issues**
```
Solutions:
- Check Windows audio settings
- Install/update audio drivers
- Test with different audio formats
```

### Manual Installation Steps

If automated installers fail:

1. **Create virtual environment**:
   ```batch
   python -m venv polyvox_env
   ```

2. **Activate environment**:
   ```batch
   polyvox_env\Scripts\activate.bat
   ```

3. **Install dependencies**:
   ```batch
   pip install -r requirements.txt
   ```

4. **Download language model**:
   ```batch
   python -m spacy download en_core_web_sm
   ```

5. **Run application**:
   ```batch
   python -m app.main
   ```

## Uninstalling

### Automatic Uninstall
- Run `uninstall.bat` in installation folder
- Or use "Uninstall PolyVox Studio" from Start Menu

### Manual Uninstall
1. Delete installation folder
2. Remove desktop shortcut
3. Remove Start Menu entries:
   - `%APPDATA%\Microsoft\Windows\Start Menu\Programs\PolyVox Studio`

## File Structure After Installation

```
PolyVox Studio/
├── 📁 polyvox_env/          # Virtual environment
├── 📁 app/                  # Application code
├── 📁 assets/               # Icons and resources
├── 📁 docs/                 # Documentation
├── 📄 launch.bat            # Application launcher
├── 📄 uninstall.bat         # Uninstaller
├── 📄 requirements.txt      # Python dependencies
└── 📄 INSTALLATION_INFO.txt # Installation details
```

## Performance Tips

### For Better Speed
- Use NVIDIA GPU with CUDA
- Close other applications during processing
- Use SSD storage for output files
- Process smaller files for testing

### For Stability
- Ensure adequate free RAM (8GB+)
- Keep Python environment clean
- Regular system updates
- Monitor disk space

## Getting Help

### Documentation
- 📚 **User Guide**: `PolyVox user guide.pdf`
- 📖 **FAQ**: `docs/FAQ.md`
- 🔧 **GPU Guide**: `GPU_COMPATIBILITY.md`

### Support Resources
- 🐛 **Issues**: GitHub repository issues section
- 💬 **Community**: Check project forums
- 📧 **Contact**: See documentation for contact info

## Advanced Configuration

### Custom Python Location
If Python is not in PATH:
```batch
"C:\Path\To\Python\python.exe" -m app.main
```

### Different Environment Name
```batch
python -m venv my_custom_env
my_custom_env\Scripts\activate.bat
```

### Development Installation
For developers wanting to modify the code:
```batch
pip install -e .
```

## Security Notes

- Installation requires internet access for packages
- Some antivirus software may flag AI/ML packages
- All installations are local to your machine
- No data is sent to external servers during normal operation

---

**Version**: 1.0  
**Last Updated**: October 2024  
**Compatible**: Windows 10/11, Python 3.8+