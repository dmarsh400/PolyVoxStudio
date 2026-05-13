# PolyVox Studio — Windows Installation Guide

Use this guide to install PolyVox Studio on Windows with the `install_windows.ps1` script. The installer builds a dedicated **PolyVox** virtual environment, selects the right PyTorch wheel for your GPU (or CPU-only setup), and installs all required Python dependencies automatically.

---

## Supported platforms & prerequisites

| Requirement | Recommended version / notes |
|-------------|-----------------------------|
| Operating system | Windows 10 (22H2) or Windows 11 (23H2), 64-bit |
| Python | CPython 3.9–3.12 (64-bit) from [python.org](https://www.python.org/downloads/) — tick **Add Python to PATH** during setup |
| PowerShell | 5.1 (built-in) or [PowerShell 7+](https://github.com/PowerShell/PowerShell) |
| NVIDIA GPU (optional) | Driver ≥ 520 for CUDA 11.8, ≥ 535 for CUDA 12.1, ≥ 570 for CUDA 12.8 (RTX 50-series). CPU installs are fully supported. |
| VC++ runtime | Latest [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist) |
| Optional tools | [FFmpeg](https://ffmpeg.org/download.html), [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki), audio interface drivers |

> ℹ️ Install Python **before** running the script. The installer searches for `python.exe` using both the PATH and the `py` launcher.

### Recommended downloads
- [Python 3.11.x (64-bit)](https://www.python.org/downloads/windows/)
- [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist)
- Optional: [PowerShell 7](https://github.com/PowerShell/PowerShell) for a nicer terminal experience

---

## Quick start

1. In File Explorer, double-click `install_windows.bat` (or right-click → **Run as administrator** if your IT policy requires it).  
   The batch file launches PowerShell with the correct execution-policy bypass, runs the full installer, and leaves the console open so you can review any messages.

2. Prefer the terminal? Run:

```powershell
.\install_windows.bat
```

The one-click installer will:

1. Locates your preferred Python interpreter (override with `$env:PYTHON` if needed).
2. Prompts for a PyTorch runtime (CUDA 12.8 for RTX 50-series, CUDA 12.1, CUDA 11.8, or CPU).
3. Creates or reuses the `PolyVox` virtual environment in the project root.
4. Installs PyTorch from the official wheel archive plus every dependency in `requirements_min.txt`.
5. Downloads the `en_core_web_md` spaCy language model.

If the exact PyTorch version for your Python build is unavailable (common with newer Python releases), the installer now retries with the latest compatible wheels for that runtime. If GPU wheels still fail, it automatically falls back to CPU wheels so setup can complete.

---

## Manual installation steps (PowerShell)

1. **Verify the Python installation**  
   Run `python --version` or `py --version`. You should see a 64-bit build between 3.9 and 3.12.
2. **Open PowerShell in the project directory**  
   Shift + Right-click the project folder → **Open PowerShell window here**, or run `cd "C:\\path\\to\\Polyvox Studio"`.
3. **(Optional) Pin a specific interpreter**  
   ```powershell
   $env:PYTHON = "C:\\Python311\\python.exe"
   ```
4. **Allow script execution for this session**  
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```
5. **Run the installer**  
   ```powershell
   .\install_windows.ps1
   ```
   Follow the prompt to pick the PyTorch runtime that matches your GPU.
6. **Review the summary**  
   When you see `✅ PolyVox environment ready!` the setup is complete.

---

## Launching the app

Use the bundled launcher:

```powershell
.\run_gui.bat
```

That batch file activates the `PolyVox` environment and runs `python -m app.main`.

### Manual activation (optional)

PowerShell:

```powershell
.\PolyVox\Scripts\Activate.ps1
python -m app.main
# When finished
deactivate
```

Command Prompt (cmd.exe):

```cmd
PolyVox\Scripts\activate.bat
python -m app.main
REM When finished
deactivate
```

---

## Optional verification & GPU checks

- Confirm the NVIDIA driver is visible:
  ```powershell
  nvidia-smi
  ```
- Verify PyTorch detects your accelerator (inside the environment):
  ```powershell
  .\PolyVox\Scripts\Activate.ps1
  python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
  deactivate
  ```

---

## Installing optional system extras

These tools unlock media processing and OCR features:

```powershell
# Using winget
winget install Gyan.FFmpeg
winget install UB-Mannheim.TesseractOCR

# Or using Chocolatey
choco install ffmpeg
choco install tesseract
```

Ensure their installation directories are on your PATH before launching PolyVox Studio.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `python` / `py` not recognized | Reinstall Python (64-bit) with "Add to PATH" enabled, or set `$env:PYTHON` to the desired interpreter. |
| Script blocked by execution policy | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` or launch with `powershell -ExecutionPolicy Bypass -File install_windows.ps1`. |
| PyTorch wheel download fails | Update NVIDIA drivers, temporarily disable VPN/firewall, or rerun and pick the CPU runtime. |
| PyTorch wheel version not found during install | Re-run the installer. v2.5 now retries with compatible wheel versions automatically. |
| pip reports SSL/proxy errors | Configure `%APPDATA%\pip\pip.ini` or set `$env:PIP_INDEX_URL` / `$env:HTTPS_PROXY` before running the installer. |
| Missing FFmpeg/Tesseract warnings | Install the tools via winget/Chocolatey and restart PowerShell so the PATH refreshes. |

---

## Maintenance & reinstallation

- **Update dependencies:** activate the environment then run `pip install --upgrade pip` followed by `pip install -r requirements_min.txt --upgrade`.
- **Recreate the environment:** delete the `PolyVox` directory and rerun `install_windows.ps1`; the script will rebuild everything.
- **Switch PyTorch runtimes:** rerun the installer and select a different CUDA/CPU option to reinstall the matching wheels.

If you hit a snag, capture a transcript with `Start-Transcript` / `Stop-Transcript` and include it when opening a GitHub issue.
