<div align="center">

# 🎭 PolyVox Studio
**Many voices, one story.**  
Professional audiobook creation with AI character voices.

[![Version](https://img.shields.io/badge/version-3.0-blue)](#-whats-new-in-v30)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/downloads/)
[![GPU Support](https://img.shields.io/badge/GPU-CUDA%2012.8%20%7C%2012.1%20%7C%2011.8%20%7C%20CPU-green)](GPU_COMPATIBILITY.md)

<img src="docs/screenshots/main_interface.png" alt="PolyVox Studio UI" width="720"/>

</div>

---

## ✨ What is PolyVox Studio?
PolyVox Studio turns books into audiobooks with **distinct voices per character**. It detects characters and dialogue, lets you assign voices (or clone your own), and renders polished audio via an intuitive desktop GUI.

**Highlights**
- 🤖 Character & dialogue detection (BookNLP + heuristics), with book-level main-character/POV persistence across chapters  
- 🎤 Built-in voices & **voice cloning** ([F5-TTS](https://github.com/SWivid/F5-TTS))  
- 🗂️ Chapter handling, line-level editing & attribution fixes  
- ⚙️ GPU acceleration with selectable **CUDA 12.8 (RTX 50-series) / CUDA 12.1 / CUDA 11.8 / CPU** modes  
- 🖥️ Modern PySide6 desktop UI with progress & logs (CustomTkinter UI retained under `app/ui` during migration)

---

## 🚀 Installation

Clone the repo and run the platform installer. Each script creates a `PolyVox` virtual environment, installs the right PyTorch wheel (CUDA 12.8, CUDA 12.1, CUDA 11.8, or CPU), and pulls the remaining dependencies.

### Installer & launcher behavior

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

## 🛡️ Hallucination Guard (optional, planned)

PolyVox can self-check synthesized lines before finalizing them. The guard synthesizes a segment, transcribes it with Whisper (prefers `faster-whisper`), and compares the transcript with the expected text. If the similarity drops below a threshold, it can retry.

**Enable it** by exporting an environment variable before launching the app:

```bash
export POLYVOX_TTS_GUARD=on
```

Available modes:

- `on` / `true` — guard every line.
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

## 📚 Documentation

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

## 🆕 What's New in v3.0

### 🎙️ F5-TTS engine & PySide6 UI
- **XTTS v2 / Coqui TTS has been replaced by [F5-TTS](https://github.com/SWivid/F5-TTS)**, the only synthesis engine, for faster inference and higher-fidelity cloning. `coqui-tts` is no longer a dependency; `f5-tts` and `PySide6` are (see `requirements_min.txt`).
- F5-TTS needs a transcript of each voice's reference clip (`ref_text`). Existing voices can be migrated with `scripts/migrate_voices_to_f5.py` (uses `faster-whisper`); new clones are transcribed once at clone time.
- **PySide6 is the primary UI** (`app/ui_qt`, launched by `app/main.py`). The CustomTkinter UI (`app/ui`) remains only for reference.
- Custom click-anywhere dropdowns replace `QComboBox` popups (which fail to render on some Linux window managers). The Split Line dialog now inserts a newline on **Enter** and confirms with **Ctrl+Enter**.

### 🧠 Much better character detection & attribution
- **BookNLP is arbitrated, not trusted blindly.** Its quote speaker is checked against local dialogue structure and overridden when the quote addresses or names that person, when that person isn't taking part in the scene (scenes reset at `* * *`), or when tag/continuation cues point elsewhere.
- **Turn-taking cues:** `"…," said X. "…"` continuation, "went on/continued", action beats, vocative replies (`"Charlie, …"` is answered by Charlie), and short answers to tagged questions.
- Vocatives are detected without needing "you" (`"Why, Zack?"`).
- Chapter subtitles and inline scare quotes (e.g. "quaint") are treated as narration instead of dialogue.
- Book-level main-character/POV selection persists across chapters; narration-only characters can appear in the cast, with a `booknlp_character_debug` diagnostics block explaining inclusions.

### 😠 Automatic emotional speech (EmoSteer)
- Based on [EmoSteer-TTS](https://arxiv.org/abs/2508.03543) (training-free activation steering). Emotion is parsed **automatically from narration cues** such as "screamed Alice", "laughed bitterly" or "in a leaden voice" (`app/core/emotion_cues.py`), with adverbs scaling intensity. Supported: angry, fearful, happy, sad, surprised, disgusted.
- No setup: on the first emotional line, steering vectors are built once from the public [RAVDESS](https://zenodo.org/records/1188976) speech corpus (~200 MB download, a few minutes) and cached in `app/core/data/emosteer/`. RAVDESS is licensed CC BY-NC-SA 4.0 (non-commercial). If anything fails, lines fall back to neutral synthesis.
- Tune strength with `BASE_ALPHA` in `app/core/emosteer.py` (default 8; values of ~16 and above degrade audio).

### 🔊 Audio quality & pacing
- **No more phantom phrases:** reference clips over ~11.5 s are trimmed at a pause and re-transcribed, so the transcript matches what F5-TTS actually hears (previously the unheard tail was spoken at the start of lines).
- **Long lines are no longer cut off** (an old 500-character limit was removed; F5-TTS chunks text itself).
- **Speech-rate governor:** lines synthesized too fast are regenerated at a lower speed. Narration uses a slower, audiobook-style pace (`NARRATOR_*` constants in `app/core/voices.py`).
- Fixed a crash after audio export caused by logging from a worker thread into Qt widgets, and an empty-audio error when silence trimming removed a very short clip.

### 📦 Installers
- Installers now pin PyTorch 2.5.1 (CUDA 11.8 / 12.1 / CPU) and 2.7.0 (CUDA 12.8), still with automatic fallback to the latest compatible wheels and then CPU.
- `requirements_min.txt` now installs `f5-tts` and `PySide6`; the launchers check for them and auto-repair.

> **Upgrading from 2.x:** re-run the installer (or `pip install -r requirements_min.txt`) and re-run chapter detection; cached detections from older versions are not reused. Voice reference files are not distributed with the repo — add your own under `voices/references/`.

---

## 🤝 Contributing
PRs welcome! See **CONTRIBUTING.md** for style, tests, and PR checklist.

---

## 📜 License
MIT — see `LICENSE`.
