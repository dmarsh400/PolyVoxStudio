<div align="center">

# 🎭 PolyVox Studio
**Many voices, one story.**  
Professional audiobook creation with AI character voices.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/downloads/)
[![GPU Support](https://img.shields.io/badge/GPU-Standard%20%7C%20Legacy-green)](GPU_COMPATIBILITY.md)

<img src="docs/screenshots/main_interface.png" alt="PolyVox Studio UI" width="720"/>

</div>

---

## ✨ What is PolyVox Studio?
PolyVox Studio turns books into audiobooks with **distinct voices per character**. It detects characters and dialogue, lets you assign voices (or clone your own), and renders polished audio via an intuitive desktop GUI.

**Highlights**
- 🤖 Character & dialogue detection (BookNLP + heuristics)  
- 🎤 Built-in voices & **voice cloning** (XTTS v2 / Coqui TTS)  
- 🗂️ Chapter handling, line-level editing & attribution fixes  
- ⚙️ GPU acceleration with **Standard** and **Legacy** setups  
- 🖥️ Modern CustomTkinter UI with progress & logs

---

## 🚀 Installation (pick one)

### Option A — Standard (modern NVIDIA GPUs or CPU)
Works on RTX 20xx/30xx/40xx and GTX 16xx. CPU-only is fine (slower).

```bash
git clone https://github.com/dmarsh400/PolyVoxStudio.git
cd PolyVoxStudio

# Linux / macOS
conda create -n PolyVox python=3.9
conda activate PolyVox
Python install.py

Windows install:
Double-click INSTALL_WINDOWS.bat
Choose:
[1] Simple Installation (recommended)
[5] Legacy GPU Installation (older NVIDIA GPUs)
Launch:
New install: use the desktop shortcut “PolyVox Studio.bat” (or PolyVoxStudio.bat in the folder)
Legacy GPU: use run_gui_legacy.bat
Note: run_gui.bat is for an older conda-based setup and isn’t used by the new installer.
```

Launch:
```bash
# Linux / macOS
./run_gui.sh

# Windows
PolyVox_Studio.bat (created after install, Shortcut should be sent to desktop)
```

### Option B — Legacy (older NVIDIA GPUs)
For K80, GTX 700/900/1000 series, Quadro K-series. Uses PyTorch 1.13.1 + CUDA 11.6 and compatible TTS.

```bash
git clone https://github.com/dmarsh400/PolyVoxStudio.git
cd PolyVoxStudio

# Linux / macOS
./install_legacy_gpu.sh
./run_gui_legacy.sh

# Windows
Double Click
INSTALL_WINDOWS.bat (Select Option 5)
run_gui_legacy.bat
```

> Not sure which to choose? See **GPU Compatibility** below.

---

## ⚡ Quick Start

1) **Launch the app**
```bash
# Standard
./run_gui.sh         # or run_gui.bat

# Legacy
./run_gui_legacy.sh  # or run_gui_legacy.bat
```

2) **Book Processing**  
**Import Book** → select `.txt` / `.pdf` / `.epub` → **Detect Chapters** → (optionally) select 1–3 chapters to process first for best attribution.

3) **Characters**  
Click **Detect Characters** → review/merge/rename characters → fix split/merged lines using split/merge tools.

4) **Voices**  
**Refresh Characters** → assign built-in voices or **Clone Voice** using a clean 6–20 s sample → **Send to Audio Processing**.

5) **Audio Processing**  
Select chapters/batches → choose output (defaults to `/output/audio`) → **Export** (per-chapter or **M4B** full audiobook).

> Tip: Start with a few chapters to dial in detection & voices, then run the whole book.

---

## 🖥️ GPU Support & Decision Guide

**Use Standard install if:** RTX 20xx/30xx/40xx or GTX 16xx (CUDA 12.x + PyTorch 2.x).  
**Use Legacy install if:** GTX 10xx/900/700, Tesla K80/K40, Quadro K (CUDA 11.6 + PyTorch 1.13).

| GPU Series                  | Install  | CUDA  | PyTorch |
|----------------------------|----------|-------|---------|
| RTX 40 / 30 / 20, GTX 16   | Standard | 12.1+ | 2.1+    |
| GTX 10 / 900 / 700, K80/K40| Legacy   | 11.6  | 1.13    |

**Driver baseline (NVIDIA):** Kepler/Maxwell legacy stacks generally need 450.80.02+ on Linux (470.x recommended).

**Why Legacy exists:** Newer stacks dropped older compute capabilities; the legacy env pins versions known to work and provides matching launch scripts.

---

## 🧩 Requirements

**Minimum**
- Python **3.9+**  
- Windows 10+/Ubuntu 20.04+/macOS 11+  
- 8 GB RAM (16 GB recommended)  
- Optional NVIDIA GPU (see table above)

**Nice to have**
- FFmpeg in PATH for audio enhancement/export niceties.

---

## 🔧 Troubleshooting (fast fixes)

- **No characters detected:** Ensure the text uses standard `"` quotes; try processing 1–3 chapters.  
- **GPU OOM or slow:** Lower batch size in Settings or confirm GPU drivers/CUDA; legacy GPUs should use the legacy launcher.  
- **Audio cut-offs / robotic output:** Use higher-quality/longer (10–20 s) voice samples; check FFmpeg install.

---

## 📚 Documentation

- **GPU Compatibility Guide** — supported cards, drivers, and decision tree  
  → `GPU_COMPATIBILITY.md`  
- **Legacy GPU Installation** — full instructions & expectations  
  → `LEGACY_GPU_INSTALL.md`  
- **Legacy GPU Summary** — what scripts exist & why  
  → `LEGACY_GPU_SUMMARY.md`  
- **Contributing guide** — dev setup, testing, PR flow  
  → `CONTRIBUTING.md`

---

## 🤝 Contributing
PRs welcome! See **CONTRIBUTING.md** for style, tests, and PR checklist.

---

## 📜 License
MIT — see `LICENSE`.
