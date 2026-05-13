# PolyVox Studio — Linux Installation Guide

Welcome! This guide walks you through installing PolyVox Studio on a modern Linux distribution using the provided `install_linux.sh` script. The installer creates an isolated Python environment named **PolyVox**, installs the correct PyTorch build for your GPU, and pulls in every Python dependency required by the app.

---

## Prerequisites

| Requirement | Recommended Version / Notes |
|-------------|----------------------------|
| Supported distros | Ubuntu 22.04+, Debian 12+, Fedora 39+, Arch (recent) |
| Python | 3.9 – 3.12 with the `venv` module available (`python3-venv` on Debian/Ubuntu) |
| NVIDIA GPU (optional) | Driver ≥ 520 for CUDA 11.8, ≥ 535 for CUDA 12.1, ≥ 570 for CUDA 12.8 (RTX 50-series). CPU-only installs are supported. |
| System packages | `build-essential` (or distro toolchain), `ffmpeg`, `tesseract-ocr`, `portaudio`/ALSA headers for audio playback |

> 💡 Tip: The installer doesn’t require root access, but you’ll use sudo to install the optional system packages.

### Install common system dependencies (Debian/Ubuntu example)

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg tesseract-ocr portaudio19-dev libsndfile1
```

On Fedora / RHEL:

```bash
sudo dnf install python3 python3-virtualenv python3-pip ffmpeg tesseract portaudio-devel libsndfile
```

---

## Quick start

```bash
chmod +x install_linux.sh
./install_linux.sh
```

The script prompts you for the PyTorch runtime (CUDA 12.8 for RTX 50-series, CUDA 12.1, CUDA 11.8, or CPU-only), builds the `PolyVox` virtual environment in the project root, and installs everything defined in `requirements_min.txt`. It also downloads the `en_core_web_md` spaCy model automatically.

If the exact PyTorch version for your Python build is unavailable (common with newer Python releases), the installer now retries with the latest compatible wheels for that runtime. If GPU wheels still fail, it automatically falls back to CPU wheels so setup can complete.

---

## Step-by-step walkthrough

1. **Choose the Python interpreter**  
   By default, the script uses `python3`. If you have multiple versions installed, set `PYTHON` before launching:
   ```bash
   PYTHON=/usr/bin/python3.11 ./install_linux.sh
   ```

2. **Select a PyTorch runtime**  
   The prompt suggests CUDA 12.8 (RTX 50-series Blackwell, driver ≥ 570), CUDA 12.1 (most cards with driver ≥ 535), CUDA 11.8 (legacy GPUs, driver ≥ 520), or CPU-only. The installer first attempts the project-tested wheel versions, then automatically retries with compatible latest wheels when needed.

3. **Core dependency install**  
   After PyTorch finishes, the script installs the rest of the stack from `requirements_min.txt` (Coqui XTTS, Transformers, spaCy, GUI/tooling utilities, etc.) and downloads the `en_core_web_md` model.

4. **Post-install summary**  
   When the script prints `✅ PolyVox environment ready!`, it shows activation instructions and optional system package hints.

---

## Running PolyVox Studio

Activate the virtual environment and launch the GUI:

```bash
source PolyVox/bin/activate
./run_gui.sh
```

In v2.5, `run_gui.sh` will also detect and use `PolyVox/bin/python` directly when the environment exists, so launching from an active `base` conda shell will not override the project interpreter.

You can deactivate the environment at any time with:

```bash
deactivate
```

To start fresh, remove the environment directory and re-run the installer:

```bash
rm -rf PolyVox
./install_linux.sh
```

---

## Optional GPU & performance checks

- Verify CUDA sees your GPU:
  ```bash
  nvidia-smi
  ```
- Confirm PyTorch is using CUDA:
  ```bash
  source PolyVox/bin/activate
  python - <<'PY'
  import torch
  print('CUDA available:', torch.cuda.is_available())
  print('Selected device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')
  PY
  ```
- For CPU-only installs, disable GPU features in the app’s Settings tab if you encounter warnings.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `python3: command not found` | Install Python (`sudo apt-get install python3 python3-venv`) or set `PYTHON=/path/to/python`. |
| `ModuleNotFoundError: spacy` after install | Ensure you ran the installer to completion. It downloads the spaCy model; if interrupted, reactivate the env and run `python -m spacy download en_core_web_md`. |
| PyTorch install fails with GPU wheel | The installer now retries with newer compatible wheel versions and then CPU wheels. If it still fails, update NVIDIA drivers (≥ 520 for CUDA 11.8, ≥ 535 for CUDA 12.1, ≥ 570 for CUDA 12.8) or run with Python 3.10/3.11. |
| `ModuleNotFoundError: PIL` on launch | Your env is incomplete (usually because installation stopped early). Re-run `./install_linux.sh` and let it finish. The launcher now reports missing modules before startup. |
| Launcher uses wrong Python environment | Use `./run_gui.sh` from the project root. v2.5 forces the project interpreter (`PolyVox/bin/python`) when available. |
| `ffmpeg` / `tesseract` missing at runtime | Install via your package manager (`sudo apt-get install ffmpeg tesseract-ocr`). |
| Need to proxy pip installs | Export `PIP_INDEX_URL` / `HTTPS_PROXY` before running the script. |

---

## Next steps & maintenance

- Keep the environment updated:
  ```bash
  source PolyVox/bin/activate
  pip install --upgrade pip
  pip install -r requirements_min.txt --upgrade
  ```
- Re-run `./install_linux.sh` if new dependency pins are added to the repository; the script will detect the existing environment and offer to recreate it.
- For headless servers, you can run the application without GUI by invoking individual processing scripts inside the environment.

Happy narrating! If you run into issues, open a GitHub issue with your distro, Python version, and the installer output attached.
