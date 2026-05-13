# PolyVox Studio v2.5

Release date: 2026-05-13

## Highlights

- Linux installer is more resilient for mixed Python/CUDA setups.
- Linux launcher now pins execution to the project virtual environment by default.
- Removed fragile `pkg_resources` runtime dependence in BookNLP core modules.
- Improved startup dependency checks and recovery guidance.
- **NEW: Advanced PDF chapter detection with font-size analysis, bold text detection, and intelligent false-positive filtering.**
- **NEW: Background threading for PDF loading prevents UI freezing on large files.**

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

### PDF Chapter Detection (NEW - v2.5)

Advanced PDF text extraction and chapter detection with multiple formatting analysis signals:

**Features:**
- **Font-size based detection** — Configurable sensitivity (1.2x, 1.3x, 1.5x body text size)
  - Detects chapters marked only with larger fonts without explicit text markers
  - User-selectable sensitivity dropdown in Book Processing tab
  - Auto-detection updates chapters when threshold changes
- **Bold text detection** — Identifies chapter headers marked with bold formatting
- **Multi-signal confidence scoring** — Combines all detection methods:
  - Font size prominence (35% weight)
  - Text pattern matching (30% weight)
  - Bold formatting (25% weight)
  - Position context (10% weight)
- **Three-strategy false-positive filtering:**
  - Bankruptcy context filter — Prevents "Chapter 11" in legal/bankruptcy contexts from false detection
  - Paragraph boundary detection — Filters chapter markers found mid-paragraph
  - Duplicate detection — Merges or removes duplicate chapter markers
- **Page cleanup improvements:**
  - Automatic page number removal (common formats: "- 1 -", "p.1", "THE BRIGADE 123", etc.)
  - Book title and footer artifact removal
  - Smart cleanup without affecting content
- **Background threading for PDF loading:**
  - Large PDFs (1.8MB+) load with responsive UI
  - Loading status message shows progress
  - No more UI freezing during extraction

**Implementation:**
- `app/core/chapter_chunker.py`
  - `_extract_pdf_with_pdfplumber()` — Enhanced PDF extraction with font metrics
  - `_extract_font_metrics()` — Font analysis from character objects
  - `_detect_chapters_by_font_size()` — Font-based chapter detection
  - `_detect_chapters_by_bold()` — Bold text detection
  - `_filter_false_positives_*()` — Three filtering strategies
  - `detect_chapters_with_formatting()` — Multi-signal detection wrapper
  - `smart_chapter_detection()` — Configurable main pipeline
- `app/ui/book_processing_tab.py`
  - Font sensitivity dropdown UI control
  - Background thread for PDF loading (`_load_book_thread()`)
  - Thread-safe GUI updates with `master.after()`

**Configuration:**
- Font sensitivity thresholds: Conservative (1.5x), Balanced (1.3x), Sensitive (1.2x)
- All filters enabled by default
- Minimum chapter length: 1000 characters (configurable)
- Maximum chapter size: 50000 characters (configurable)

**Documentation:**
- New: `PDF_CHAPTER_DETECTION.md` — Comprehensive feature guide with examples, API, and troubleshooting
- Updated: `README.md` — Links to detailed PDF detection documentation

**Dependencies:**
- `pdfplumber` — Advanced PDF text extraction (added to recommended packages)

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
