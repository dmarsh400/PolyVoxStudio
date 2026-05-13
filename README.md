<div align="center">

# 🎭 PolyVox Studio
**Many voices, one story.**  
Professional audiobook creation with AI character voices.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/downloads/)
[![GPU Support](https://img.shields.io/badge/GPU-CUDA%2012.8%20%7C%2012.1%20%7C%2011.8%20%7C%20CPU-green)](GPU_COMPATIBILITY.md)

<img src="docs/screenshots/main_interface.png" alt="PolyVox Studio UI" width="720"/>

</div>

---

## ✨ What is PolyVox Studio?
PolyVox Studio turns books into audiobooks with **distinct voices per character**. It detects characters and dialogue, lets you assign voices (or clone your own), and renders polished audio via an intuitive desktop GUI.

**Highlights**
- 🤖 Character & dialogue detection (BookNLP + heuristics)  
- 🎤 Built-in voices & **voice cloning** (XTTS v2 / Coqui TTS)  
- 🗂️ Chapter handling, line-level editing & attribution fixes  
- ⚙️ GPU acceleration with selectable **CUDA 12.8 (RTX 50-series) / CUDA 12.1 / CUDA 11.8 / CPU** modes  
- 🖥️ Modern CustomTkinter UI with progress & logs

---

## 🚀 Installation

Clone the repo and run the platform installer. Each script creates a `PolyVox` virtual environment, installs the right PyTorch wheel (CUDA 12.8, CUDA 12.1, CUDA 11.8, or CPU), and pulls the remaining dependencies.

### 🆕 v2.5 install & startup improvements

- Linux installer now retries with the latest compatible PyTorch wheels if pinned wheels are unavailable for your Python version.
- Linux installer now falls back to CPU PyTorch automatically if GPU wheel install fails.
- Linux launcher now uses the `PolyVox/bin/python` interpreter directly (prevents accidental use of base/conda Python).
- Linux launcher now auto-checks core dependencies and attempts repair from `requirements_min.txt` when something is missing.

### 🐧 Linux (and advanced macOS setups)

```bash
git clone https://github.com/dmarsh400/PolyVoxStudio.git
cd PolyVoxStudio
chmod +x install_linux.sh
./install_linux.sh
```

The installer will prompt for your preferred GPU runtime. See [`INSTALL_LINUX.md`](INSTALL_LINUX.md) for prerequisites, optional system packages (FFmpeg/Tesseract), and troubleshooting tips.

### 🪟 Windows (one click)

```powershell
git clone https://github.com/dmarsh400/PolyVoxStudio.git
cd PolyVoxStudio
.\install_windows.bat
```

You can also double-click `install_windows.bat` in Explorer. The batch file launches PowerShell with execution-policy bypass, then runs the full installer. Detailed notes live in [`INSTALL_WINDOWS.md`](INSTALL_WINDOWS.md).

> Need CPU-only? Choose the CPU option when prompted. Unsure which CUDA runtime to pick? Check the **GPU Support** section below.

---

## ⚡ Quick Start

1) **Launch the app**
```bash
./run_gui.sh          # Linux / macOS
```

On Linux, `run_gui.sh` automatically uses the local `PolyVox` environment if present and prints which Python executable is being used.

```powershell
./run_gui.bat        # Windows (double-click works too)
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

Both installers prompt for a PyTorch runtime. Pick the option that matches your hardware:

| GPU Series / Setup           | Runtime choice in installer | Notes |
|------------------------------|-----------------------------|-------|
| RTX 50-series (Blackwell)    | **CUDA 12.8**               | Required for GB202/GB203 (RTX 5090/5080/5070/5060); driver ≥ 570 |
| RTX 40 / 30 / 20, GTX 16     | **CUDA 12.1**               | Latest features and fastest inference |
| RTX 10 / GTX 10 & older RTX  | **CUDA 11.8**               | Best fit for earlier CUDA-capable cards |
| No NVIDIA GPU / Virtualized  | **CPU only**                | Works everywhere (slower) |

**Driver baseline (NVIDIA):** Ensure your driver supports the selected CUDA version (≥ 520 for CUDA 11.8, ≥ 535 for CUDA 12.1, ≥ 570 for CUDA 12.8). If in doubt, choose CPU to finish the install, then upgrade drivers and rerun the installer later.

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
- **GPU OOM or slow:** Lower batch size in Settings or rerun the installer with a different runtime (CUDA 11.8 or CPU) after updating drivers.  
- **Audio cut-offs / robotic output:** Use higher-quality/longer (10–20 s) voice samples; check FFmpeg install.
- **PyTorch wheel version not found during install:** Re-run the installer. v2.5 now retries with compatible wheel versions automatically.
- **Launch uses wrong Python environment:** Use `./run_gui.sh` from the project root. v2.5 pins startup to the project interpreter and reports the active executable.

---

## 🛡️ Hallucination Guard (optional)

PolyVox can now self-check XTTS lines before finalizing them. The guard synthesizes a segment, transcribes it with Whisper (prefers `faster-whisper`), and compares the transcript with the expected text. If the similarity drops below a threshold, it can retry—falling back to the deterministic XTTS preset on later attempts.

**Enable it** by exporting an environment variable before launching the app:

```bash
export POLYVOX_TTS_GUARD=on
```

Available modes:

- `on` / `true` — guard every XTTS line.
- `auto` *(default)* — guard narrator lines only.
- `narrator` — identical to `auto`, explicit for readability.
- `off` / `false` — disable the guard entirely.

Fine-tune behavior with optional overrides:

```bash
export POLYVOX_TTS_GUARD_THRESHOLD=0.9      # similarity target (0..1)
export POLYVOX_TTS_GUARD_RETRIES=2          # additional attempts if under threshold
export POLYVOX_TTS_GUARD_MODEL=base         # Whisper size: base, small, medium, etc.
```

Voice definitions (e.g., JSON entries) can opt in/out per character using:

- `"hallucination_guard": true | false`
- `"guard_threshold": 0.88`
- `"guard_max_retries": 2`
- `"guard_model_size": "base.en"`

> Dependencies: install `faster-whisper` and `rapidfuzz` for the fast path. The guard falls back gracefully if the packages are missing.

---

## �📚 Documentation

- **Linux Installation Guide** — prerequisites, installer walkthrough, troubleshooting  
  → `INSTALL_LINUX.md`
- **Windows Installation Guide** — one-click batch installer and manual PowerShell steps  
  → `INSTALL_WINDOWS.md`
- **GPU Compatibility Guide** — supported cards, drivers, and runtime recommendations  
  → `GPU_COMPATIBILITY.md`
- **Contributing guide** — dev setup, testing, PR flow  
  → `CONTRIBUTING.md`
- **PDF Chapter Detection Guide** — font-size analysis, formatting detection, false-positive filtering  
  → `PDF_CHAPTER_DETECTION.md`

---

## 📖 PDF Chapter Detection (v2.0)

PolyVox now includes **advanced PDF chapter detection** with:
- 🔤 Font-size detection (configurable 1.2x, 1.3x, 1.5x sensitivity)
- **🔨 Bold text detection** for chapter headers  
- 🛡️ False-positive filtering (bankruptcy context, paragraph boundaries, duplicates)
- ⚡ Background threading prevents UI freezing on large PDFs

👉 **[Full PDF Chapter Detection guide →](PDF_CHAPTER_DETECTION.md)**

---

## 🤝 Contributing
PRs welcome! See **CONTRIBUTING.md** for style, tests, and PR checklist.

---

## 📜 License
MIT — see `LICENSE`.
