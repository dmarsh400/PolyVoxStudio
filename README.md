# PolyVox Studio - PDF Chapter Detection & Processing

Advanced PDF parsing and chapter detection for audiobook narration with intelligent formatting analysis and false-positive filtering.

## ✨ Features

### 📖 Smart Chapter Detection
- **Multiple Detection Signals**: Combines text patterns, font size, and bold formatting
- **Font-Size Analysis**: Detects chapters marked with larger fonts (configurable 1.2x, 1.3x, 1.5x thresholds)
- **Bold Text Detection**: Identifies chapter headers marked with bold formatting
- **Confidence Scoring**: Weighted multi-signal scoring (Text 30%, Font 35%, Bold 25%, Position 10%)
- **Pattern Matching**: Supports all chapter label formats:
  - Standard: "CHAPTER 1", "Chapter I", "Ch. 5"
  - Roman Numerals: "I", "II.", "III)", with smart single-letter filtering
  - Arabic Numbers: "1", "2.", "3)"
  - Parts & Books: "PART 1", "Book II", "Volume Three"
  - Named Sections: "Prologue", "Epilogue", "Introduction"

### 🛡️ False-Positive Filtering
Three intelligent strategies to avoid false chapter detection:
1. **Bankruptcy Context Filter**: Prevents "Chapter 11" in legal/bankruptcy discussions from being detected as actual chapters
2. **Paragraph Boundary Detection**: Filters chapter markers found mid-paragraph
3. **Duplicate Detection**: Merges or removes duplicate chapter markers

### 🧹 Page Cleanup
- **Automatic Page Number Removal**: Detects and removes common formats (- 1 -, p.1, pp.1, THE BRIGADE 123, etc.)
- **Book Title Removal**: Filters out repeated book titles and author names from footers
- **Smart Artifact Detection**: Removes common PDF artifacts without affecting content

### ⚡ Performance
- **Background Threading**: PDF extraction runs in background thread to prevent UI freezing
- **Fast Processing**: Large PDFs (1.8M+ characters) load with responsive GUI
- **Efficient Detection**: Chapter detection completes in ~8-10 seconds with formatting analysis

### 🎚️ Configurable Sensitivity
Three preset font-size detection thresholds in the GUI:
- **Conservative (1.5x)**: Fewer false positives, may miss subtle headers
- **Balanced (1.3x)**: Default, good balance of detection and accuracy
- **Sensitive (1.2x)**: Catches more headers, may include some non-chapter text

## 🚀 Quick Start

### Installation
```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install pdfplumber for advanced PDF extraction
pip install pdfplumber
```

### Using the GUI
1. Open PolyVox Studio
2. Go to "Book Processing" tab
3. Click "Import Book" and select your PDF
4. (Optional) Select font sensitivity level before detecting chapters
5. Click "Detect Chapters"
6. Review detected chapters in the list
7. Select 1-3 chapters and send to "Characters" tab

### Python API
```python
from app.core.chapter_chunker import load_book, smart_chapter_detection

# Load PDF with automatic cleanup
text = load_book("book.pdf")

# Detect chapters with font-size threshold
chapters = smart_chapter_detection(
    text,
    min_chapter_length=1000,
    max_chunk_size=50000,
    font_size_threshold=1.3  # 1.2, 1.3, or 1.5
)

# Process results
for chapter in chapters:
    print(f"Title: {chapter['title']}")
    print(f"Size: {len(chapter['text'])} chars")
```

## 📚 Processing Flow

```
PDF File
  ↓
Extract with pdfplumber (preserves font metrics & layout)
  ↓
Remove page artifacts (numbers, titles, footers)
  ↓
Analyze formatting:
  ├─ Font size relative to body text
  ├─ Bold/strong font detection
  └─ Text pattern matching
  ↓
Generate confidence scores for candidates
  ├─ Font size prominence (35%)
  ├─ Text pattern match (30%)
  ├─ Bold status (25%)
  └─ Position context (10%)
  ↓
Apply false-positive filters:
  ├─ Bankruptcy context
  ├─ Paragraph boundaries
  └─ Duplicate detection
  ↓
Return ranked, verified chapters
```

## 🔧 Advanced Configuration

### Minimum Chapter Length
```python
chapters = smart_chapter_detection(
    text,
    min_chapter_length=500  # Default: 1000
)
```

### Custom Font Threshold
```python
chapters = smart_chapter_detection(
    text,
    font_size_threshold=1.2  # Sensitive
)
```

### Maximum Chapter Size
```python
chapters = smart_chapter_detection(
    text,
    max_chunk_size=75000  # Default: 50000 chars
)
```

## 📊 Detection Examples

### Example 1: Text Pattern Detection
```
Input: "CHAPTER 5: The Final Stand"
Detection: Text pattern match (confidence 0.95)
Result: ✓ Detected as chapter
```

### Example 2: Font-Size Detection
```
Input: Large 18pt text "Part IV" (body is 12pt)
Font size factor: 18/12 = 1.5x (> 1.3x threshold)
Detection: Font size prominence (confidence 0.85)
Result: ✓ Detected as chapter
```

### Example 3: Bold Text Detection
```
Input: Bold text "- Introduction -"
Detection: Bold formatting + position (confidence 0.72)
Result: ✓ Detected as chapter
```

### Example 4: Bankruptcy False-Positive Filter
```
Input: "Chapter 11" in bankruptcy discussion context
Surrounding text: "filed", "creditor", "court", "debtor"
Detection: Text match but bankruptcy filter active
Result: ✗ Filtered out (confidence reduced to 0.15)
```

## ⚙️ Implementation Details

### Core Functions

| Function | Purpose |
|----------|---------|
| `load_book()` | Entry point; loads any format (TXT, EPUB, PDF) with cleanup |
| `_extract_pdf_with_pdfplumber()` | Advanced PDF extraction with font metrics |
| `_extract_font_metrics()` | Analyzes character font sizes and names |
| `_detect_chapters_by_font_size()` | Finds chapters by font size deviation |
| `_detect_chapters_by_bold()` | Identifies bold text chapter headers |
| `_filter_false_positives_bankruptcy()` | Removes bankruptcy-context false positives |
| `_filter_false_positives_paragraph_boundary()` | Filters mid-paragraph markers |
| `_filter_false_positives_duplicates()` | Merges duplicate detections |
| `_merge_formatting_signals()` | Combines all signals with confidence scoring |
| `detect_chapters_with_formatting()` | Main detection wrapper with all signals |
| `smart_chapter_detection()` | Orchestrates full pipeline with user-selected threshold |

### UI Components

| Component | Location |
|-----------|----------|
| Book import with threading | `book_processing_tab.py:_import_book()` |
| Font sensitivity dropdown | `book_processing_tab.py` button row |
| Chapter list display | `book_processing_tab.py` left panel |
| Chapter preview | `book_processing_tab.py` right panel |
| Threshold selector | `book_processing_tab.py:_on_threshold_change()` |

## 🧪 Testing

### Run Test Suite
```bash
# Quick test of all features
python test_chapter_detection.py
```

### Manual Testing
1. Place your PDF in the project directory
2. Open GUI and import the PDF
3. Try all three font sensitivity levels
4. Check that chapters are detected correctly
5. Verify page numbers are removed from preview

### Performance Testing
```python
import time
from app.core.chapter_chunker import load_book, smart_chapter_detection

start = time.time()
text = load_book("large_book.pdf")
load_time = time.time() - start

start = time.time()
chapters = smart_chapter_detection(text, font_size_threshold=1.3)
detect_time = time.time() - start

print(f"Load: {load_time:.1f}s, Detect: {detect_time:.1f}s")
```

## 📋 File Structure

```
app/core/chapter_chunker.py         # Main detection module
├─ _extract_pdf_with_pdfplumber()  # PDF extraction with metrics
├─ _extract_font_metrics()          # Font analysis
├─ _detect_chapters_by_font_size()  # Font-based detection
├─ _detect_chapters_by_bold()       # Bold text detection
├─ _filter_false_positives_*()      # Filter implementations
├─ _merge_formatting_signals()      # Confidence scoring
├─ detect_chapters_with_formatting()# Detection wrapper
└─ smart_chapter_detection()        # Full pipeline

app/ui/book_processing_tab.py       # GUI integration
├─ _import_book()                   # Book import with threading
├─ _load_book_thread()              # Background load thread
├─ _detect_chapters()               # Detection trigger
├─ _on_threshold_change()           # Threshold selector
└─ Font sensitivity dropdown        # UI control

CHAPTER_DETECTION_IMPROVEMENTS.md   # Technical documentation
README.md                           # This file
```

## 🐛 Troubleshooting

### Issue: "Program freezes when loading PDF"
**Solution**: Applies only to very large PDFs (1MB+). Uses background threading to keep UI responsive. Progress message shows "Loading: filename...".

### Issue: "Page numbers still showing in chapters"
**Solution**: The cleanup catches common patterns. For unusual formats:
1. Check the debug output for what was detected
2. Create an issue with a sample of the page number format
3. Manual removal is available by editing chapters in the GUI

### Issue: "Not detecting all chapters"
**Solution**: Try different sensitivity levels:
- Sensitive (1.2x) - catches more headers
- Balanced (1.3x) - recommended default
- Conservative (1.5x) - fewer false positives

### Issue: "False positives (e.g., 'Chapter 11' in legal docs)"
**Solution**: The bankruptcy filter is active by default. If "Chapter 11" is a real chapter:
- Check surrounding text doesn't contain bankruptcy keywords
- Try Sensitive (1.2x) threshold which weights text patterns higher
- Or manually adjust detected chapters in the GUI

### Issue: "pdfplumber not found"
**Solution**:
```bash
source .venv/bin/activate
pip install pdfplumber
python -c "import pdfplumber; print('✓ Ready')"
```

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| PDF extraction (1.8MB PDF) | ~59 seconds |
| Page cleanup | ~0.02 seconds |
| Chapter detection (1.3x) | ~8-10 seconds |
| Total pipeline | ~68 seconds |
| **UI remains responsive** | ✓ (background threading) |

## 🔒 Confidence Scoring Details

### Score Components
```
Total Score = (Font 0.35) + (Text 0.30) + (Bold 0.25) + (Position 0.10)

Range: 0.0 - 1.0
Decision: Score >= 0.6 = Accept as chapter
```

### Adjustment Factors
- Bankruptcy filter: -0.5 confidence
- Mid-paragraph: -0.3 confidence
- Duplicate: merge/consolidate

## 🎯 Known Limitations

1. **Image-based PDFs**: Cannot process scanned PDFs (requires OCR)
2. **Complex Layouts**: Multi-column documents may extract imperfectly
3. **Custom Formats**: Very unusual page numbering formats may not be detected
4. **Language**: Patterns optimized for English

## 🔮 Future Enhancements

- [ ] OCR support for scanned PDFs
- [ ] Multi-column document handling
- [ ] Custom pattern configuration UI
- [ ] Language-specific detection rules
- [ ] Chapter confidence visualization in GUI
- [ ] Custom false-positive rules editor

## 📝 Recent Changes

### v2.0 - Enhanced PDF Detection
- ✅ Font-size based chapter detection
- ✅ Bold text detection
- ✅ Bankruptcy context filtering
- ✅ Paragraph boundary filtering
- ✅ Duplicate detection filtering
- ✅ Confidence scoring system
- ✅ Configurable sensitivity thresholds (1.2x, 1.3x, 1.5x)
- ✅ Auto-detection on threshold change
- ✅ Background threading for UI responsiveness
- ✅ Page number and artifact removal improvements

## 📄 License

See LICENSE file for details.

## 🤝 Contributing

To report issues with PDF detection:

1. Export the problematic PDF
2. Note what went wrong (missing chapters, false positives, page numbers, etc.)
3. Create an issue with the PDF format details
4. Include sample of the content that wasn't detected correctly

## 📞 Support

For questions or issues:
1. Check this README and CHAPTER_DETECTION_IMPROVEMENTS.md
2. Review debug output in the GUI or console
3. Try different sensitivity thresholds
4. Create a GitHub issue with details
