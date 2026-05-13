# PolyVox Studio v2.6

Release date: 2026-05-13

## Highlights

- **NEW: Advanced PDF chapter detection with font-size analysis, bold text detection, and intelligent false-positive filtering.**
- **NEW: Background threading for PDF loading prevents UI freezing on large files.**
- **NEW: Configurable font sensitivity thresholds (1.2x, 1.3x, 1.5x) with real-time detection updates.**
- **NEW: Comprehensive page cleanup removes footers, page numbers, and book title artifacts.**

## Detailed changes

### PDF Chapter Detection (NEW - v2.6)

Advanced PDF text extraction and chapter detection with multiple formatting analysis signals:

**Key Features:**

- **Font-size based detection** — Configurable sensitivity (1.2x, 1.3x, 1.5x body text size)
  - Detects chapters marked only with larger fonts without explicit text markers
  - User-selectable sensitivity dropdown in Book Processing tab
  - Auto-detection updates chapters when threshold changes
  - Default threshold: Balanced (1.3x)

- **Bold text detection** — Identifies chapter headers marked with bold formatting
  - Works independently or combined with other signals
  - Confidence weighted at 25% in final scoring

- **Multi-signal confidence scoring** — Combines all detection methods:
  - Font size prominence (35% weight)
  - Text pattern matching (30% weight)
  - Bold formatting (25% weight)
  - Position context (10% weight)
  - Minimum confidence threshold: 0.6 for acceptance

- **Three-strategy false-positive filtering:**
  - **Bankruptcy context filter** — Prevents "Chapter 11" in legal/bankruptcy contexts from false detection
    - Detects surrounding keywords: "filed", "creditor", "debtor", "court", "bankruptcy", etc.
    - Preserves genuine "Chapter 11" when not in legal context
  - **Paragraph boundary detection** — Filters chapter markers found mid-paragraph
    - Checks for blank lines above/below chapter marker
    - Reduces confidence for isolated markers
  - **Duplicate detection** — Merges or removes duplicate chapter markers
    - Catches OCR artifacts and formatting duplicates

- **Page cleanup improvements:**
  - Automatic page number removal (common formats: "- 1 -", "p.1", "pp.1", "THE BRIGADE 123", etc.)
  - Book title and footer artifact removal
  - Smart regex-based detection without affecting content
  - Optimized for performance (no regex backtracking issues)

- **Background threading for PDF loading:**
  - Large PDFs (1.8MB+) load with responsive UI
  - Loading status message shows progress ("Loading: filename...")
  - No more UI freezing during extraction
  - Thread-safe GUI updates via `master.after()`

**Implementation Details:**

- `app/core/chapter_chunker.py`
  - `_extract_pdf_with_pdfplumber()` — Enhanced PDF extraction with font metrics and word positioning
  - `_extract_font_metrics()` — Font analysis from character objects (sizes, names, bold detection)
  - `_detect_chapters_by_font_size()` — Font-based chapter detection with threshold
  - `_detect_chapters_by_bold()` — Bold text detection and scoring
  - `_filter_false_positives_bankruptcy()` — Bankruptcy context filtering
  - `_filter_false_positives_paragraph_boundary()` — Paragraph boundary detection
  - `_filter_false_positives_duplicates()` — Duplicate chapter merging
  - `_merge_formatting_signals()` — Combines all signals with weighted confidence scoring
  - `detect_chapters_with_formatting()` — Multi-signal detection wrapper
  - `smart_chapter_detection()` — Configurable main pipeline with `font_size_threshold` parameter

- `app/ui/book_processing_tab.py`
  - Font sensitivity dropdown UI control with three presets
  - Background thread for PDF loading (`_load_book_thread()`)
  - Thread-safe GUI updates with `master.after()`
  - Threshold change callback triggers auto-detection

**Configuration:**
- Font sensitivity thresholds: Conservative (1.5x), Balanced (1.3x), Sensitive (1.2x)
- All filters enabled by default
- Minimum chapter length: 1000 characters (configurable)
- Maximum chapter size: 50000 characters (configurable)
- Confidence scoring threshold: 0.6 (configurable)

**Documentation:**
- New: `PDF_CHAPTER_DETECTION.md` — Comprehensive feature guide with examples, API, troubleshooting, and performance metrics
- Updated: `README.md` — Links to detailed PDF detection documentation with feature highlights

**Dependencies:**
- `pdfplumber` — Advanced PDF text extraction with font metrics (added to requirements)

**Performance:**
- PDF extraction: ~59 seconds for 1.8MB file (background threaded)
- Page cleanup: ~0.02 seconds
- Chapter detection: ~8-10 seconds with formatting analysis
- Total pipeline: ~68 seconds with responsive UI

**Testing:**
- All 31 chapters detected correctly from test PDF
- "Chapter 11" bankruptcy false positive properly filtered
- Page numbers and footers completely removed
- Threshold selection updates chapters in real-time
- UI remains responsive during large file loading

## Upgrade notes

- Existing users can upgrade in place by pulling changes and re-running:

```bash
./install_linux.sh
./run_gui.sh
```

or

```powershell
.\install_windows.bat
```

- If your environment is heavily modified, a clean reset is recommended:

```bash
rm -rf PolyVox
./install_linux.sh
./run_gui.sh
```

## What's New Since v2.5

v2.6 focuses on **intelligent PDF processing** with:
- Multiple formatting signals for robust chapter detection
- User-adjustable sensitivity with real-time updates
- Smart false-positive filtering prevents misdetection of legal content
- Responsive UI with background threading
- Complete page artifact cleanup
- Full documentation and examples
