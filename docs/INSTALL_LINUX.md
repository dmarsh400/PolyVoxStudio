# PolyVox Studio — Linux Installation Guide

Welcome! This guide walks you through installing PolyVox Studio on a modern Linux distribution using the provided `install_linux.sh` script. The installer creates an isolated Python environment named **PolyVox**, installs the correct PyTorch build for your GPU, and pulls in every Python dependency required by the app.

---

## Prerequisites

| Requirement | Recommended Version / Notes |
|-------------|----------------------------|
| Supported distros | Ubuntu 22.04+, Debian 12+, Fedora 39+, Arch (recent) |
| Python | 3.9 – 3.12 with the `venv` module available (`python3-venv` on Debian/Ubuntu) |
| NVIDIA GPU (optional) | Driver ≥ 520 for CUDA 11.8, ≥ 535 for CUDA 12.1. CPU-only installs are supported. |
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

The script prompts you for the PyTorch runtime (CUDA 11.8, CUDA 12.1, or CPU-only), builds the `PolyVox` virtual environment in the project root, and installs everything defined in `requirements_min.txt`. It also downloads the `en_core_web_sm` SpaCy model automatically.

---

## Step-by-step walkthrough

1. **Choose the Python interpreter**  
   By default, the script uses `python3`. If you have multiple versions installed, set `PYTHON` before launching:
   ```bash
   PYTHON=/usr/bin/python3.11 ./install_linux.sh
   ```

2. **Select a PyTorch runtime**  
   The prompt suggests CUDA 11.8 (legacy GPUs), CUDA 12.1 (most cards shipping with driver 535+), or CPU-only. The installer pulls the matching `torch`, `torchvision`, and `torchaudio` wheels from the official PyTorch archive.

3. **Core dependency install**  
   After PyTorch finishes, the script installs the rest of the stack from `requirements_min.txt` (Coqui XTTS, Transformers, spaCy, GUI/tooling utilities, etc.) and downloads the `en_core_web_sm` model.

4. **Post-install summary**  
   When the script prints `✅ PolyVox environment ready!`, it shows activation instructions and optional system package hints.

---

## Running PolyVox Studio

Activate the virtual environment and launch the GUI:

```bash
source PolyVox/bin/activate
./run_gui.sh
```

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
| `ModuleNotFoundError: spacy` after install | Ensure you ran the installer to completion. It downloads the SpaCy model; if interrupted, reactivate the env and run `python -m spacy download en_core_web_sm`. |
| PyTorch install fails with GPU wheel | Update to the latest NVIDIA driver (≥ 520 for CUDA 11.8, ≥ 535 for CUDA 12.1) or re-run the installer and pick the CPU runtime. |
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
