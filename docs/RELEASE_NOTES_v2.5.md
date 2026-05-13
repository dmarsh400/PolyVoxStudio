# PolyVox Studio v2.5

Release date: 2026-05-13

## Highlights

- Linux installer is more resilient for mixed Python/CUDA setups.
- Linux launcher now pins execution to the project virtual environment by default.
- Removed fragile `pkg_resources` runtime dependence in BookNLP core modules.
- Improved startup dependency checks and recovery guidance.

## Detailed changes

### Installer hardening

- `install_linux.sh`
  - Added fallback logic when pinned PyTorch wheels are unavailable for the selected runtime.
  - Retries with latest compatible wheels from the selected PyTorch index.
  - Falls back to CPU wheels automatically if GPU wheel installation fails.
  - Prints the final installed runtime/index in post-install notes.

- `install_windows.ps1`
  - Added fallback logic when pinned PyTorch wheels are unavailable for the selected runtime.
  - Retries with latest compatible wheels from the selected PyTorch index.
  - Falls back to CPU wheels automatically if GPU wheel installation fails.
  - Prints the final installed runtime/index in post-install notes.

### Launcher reliability

- `run_gui.sh`
  - Uses `PolyVox/bin/python` directly when the project environment exists.
  - Prints active Python executable for transparent environment debugging.
  - Checks for key dependencies (`PIL`, `spacy`, `torch`, `customtkinter`) before launch.
  - Attempts automatic repair using `requirements_min.txt --upgrade` when dependencies are missing.

- `run_gui.bat`
  - Uses `PolyVox\Scripts\python.exe` directly (no environment activation script).
  - Prints active Python executable for transparent environment debugging.
  - Checks for key dependencies (`PIL`, `spacy`, `torch`, `customtkinter`) before launch.
  - Attempts automatic repair using `requirements_min.txt --upgrade` when dependencies are missing.

### Core compatibility fixes

- Removed `pkg_resources` usage and replaced with local `pathlib` data-path resolution in:
  - `app/core/entity_tagger.py`
  - `app/core/name_coref.py`
  - `app/core/litbank_coref.py`
  - `app/core/english_booknlp.py`

### Dependency updates

- `requirements_min.txt`
  - Added `setuptools>=68.0.0` to strengthen environment consistency for legacy package expectations.

### Documentation updates

- Updated:
  - `docs/README.md`
  - `docs/INSTALL_LINUX.md`

## Upgrade notes

- Existing users can upgrade in place by pulling changes and re-running:

```bash
./install_linux.sh
./run_gui.sh
```

- If your environment is heavily modified, a clean reset is recommended:

```bash
rm -rf PolyVox
./install_linux.sh
./run_gui.sh
```
