# Python Not Found - Troubleshooting Guide

## The Problem
You're seeing this error:
```
ERROR: Python not found
Please install Python 3.8 or higher from https://python.org/
Make sure to check "Add Python to PATH" during installation
```

But you **already have Python installed**.

---

## Quick Diagnosis

Run the Python detection tool:
```batch
find_python.bat
```

This will scan your system and show you:
- ✅ Where Python is installed
- ✅ Which Python commands work
- ✅ Whether Python is in your PATH

---

## Solutions (Try in Order)

### Solution 1: Use Python Launcher (Easiest)
Windows includes a Python Launcher (`py`) that should work even if Python isn't in PATH.

**Test it:**
1. Open Command Prompt
2. Type: `py --version`
3. If this works, Python is installed!

**Fix the installer:**
The installer should automatically try `py` if `python` doesn't work. If it doesn't, please report this issue.

---

### Solution 2: Add Python to PATH (Recommended)

**Find Python location:**
1. Open Command Prompt
2. Type: `where python` or `where py`
3. Copy the path shown (e.g., `C:\Users\YourName\AppData\Local\Programs\Python\Python311`)

**Add to PATH:**
1. Search Windows for "Environment Variables"
2. Click "Environment Variables" button
3. Under "System variables" or "User variables", find "Path"
4. Click "Edit"
5. Click "New"
6. Paste the Python path
7. Also add: `[Python Path]\Scripts` (e.g., `C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts`)
8. Click "OK" on all dialogs
9. **Restart Command Prompt** (important!)
10. Test: `python --version`

**Video guides:**
- Search YouTube for: "add python to path windows 10"
- Or: "add python to environment variables windows"

---

### Solution 3: Reinstall Python

If Python is installed but you can't find it or PATH isn't working:

1. **Download Python:**
   - Go to https://www.python.org/downloads/
   - Download latest Python 3.8 or higher

2. **Run installer:**
   - ✅ **CHECK "Add Python to PATH"** (at the bottom of first screen)
   - ✅ **CHECK "Add Python to environment variables"**
   - Choose "Install for all users" if prompted
   - Click "Install Now"

3. **Verify:**
   - Open **NEW** Command Prompt
   - Type: `python --version`
   - Should show: `Python 3.x.x`

4. **Run installer again:**
   - Double-click `INSTALL_WINDOWS.bat`

---

### Solution 4: Run as Administrator

Sometimes Windows permission issues prevent detection:

1. **Right-click** `INSTALL_WINDOWS.bat`
2. Select **"Run as Administrator"**
3. Click "Yes" when prompted

---

### Solution 5: Use Specific Python Path

If you know where Python is installed but can't add to PATH:

1. Find Python location (e.g., `C:\Python311\python.exe`)
2. Create a custom launcher:

Create file: `install_custom.bat`
```batch
@echo off
REM Replace this path with your Python location:
set PYTHON_CMD=C:\Python311\python.exe

cd /d "%~dp0"
%PYTHON_CMD% -m venv venv
call venv\Scripts\activate.bat
%PYTHON_CMD% -m pip install -r requirements.txt
%PYTHON_CMD% -m spacy download en_core_web_sm
echo Installation complete!
pause
```

3. Edit the `PYTHON_CMD` line with your Python path
4. Run `install_custom.bat`

---

## Still Not Working?

### Check Windows Store Python
If you installed Python from Microsoft Store:
- It may be in: `%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe`
- This version sometimes has issues
- Recommendation: Uninstall and install from python.org instead

### Check Multiple Python Installations
You might have multiple Python versions:
```batch
where python
py -0p
```

This shows all installed versions. Use the latest one (3.8+).

### Completely Start Over

1. **Uninstall all Python versions:**
   - Settings → Apps → Uninstall Python
   - Remove all versions found

2. **Clean up PATH:**
   - Remove old Python entries from Environment Variables

3. **Fresh install:**
   - Download from python.org
   - ✅ Check "Add Python to PATH"
   - Install for all users

4. **Restart computer**

5. **Verify:**
   ```batch
   python --version
   py --version
   where python
   ```

6. **Run installer**

---

## Getting More Help

### Run Diagnostics
```batch
find_python.bat
```

### Check Installation Guide
```
WINDOWS_INSTALL_README.md
```

### Manual Installation
If automated installers continue failing:
```batch
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m app.main
```

### Contact Support
- Include output from `find_python.bat`
- Include Windows version
- Include error messages
- Check GitHub repository issues

---

## Prevention for Next Time

When installing Python:
- ✅ Always check "Add Python to PATH"
- ✅ Install for all users
- ✅ Use python.org installer (not Microsoft Store)
- ✅ Install latest stable version (3.11+ recommended)
- ✅ Restart terminal after installation

---

## Quick Reference Commands

```batch
# Test Python
python --version
py --version
python3 --version

# Find Python
where python
where py

# Test pip
python -m pip --version
py -m pip --version

# List Python installations (Python Launcher)
py -0
py -0p

# Run Python even without PATH
py -m app.main

# Check environment variables
echo %PATH%
```

---

**Last Updated:** October 2024
