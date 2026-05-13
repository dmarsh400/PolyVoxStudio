# PDF Chapter Detection & Cleanup - Complete Guide

## What's Improved

### 1. **PDF Text Extraction with pdfplumber**
- Uses advanced PDF parsing instead of simple text extraction
- Preserves document structure and layout information
- Detects word positions for header/footer analysis

### 2. **Automatic Page Number Removal**
Detects and removes common page number formats:
- `- 1 -`, `-1-`, `1`, `p.1`, `pp.1`
- Very short standalone numbers
- Lines that match "Chapter 1", "Page 2" patterns

### 3. **Header/Footer Detection (Future)**
The infrastructure is in place to detect and remove:
- Top 15% of page (typical header zone)
- Bottom 15% of page (typical footer zone)
- Repeated book titles and author names

### 4. **Text Normalization**
- Removes excessive blank lines (preserves paragraph breaks)
- Cleans up trailing whitespace
- Maintains readability

### 5. **Enhanced Chapter Detection**
Supports all common chapter label formats:
- **Standard**: "CHAPTER 1", "Chapter I", "Ch. 5"
- **Parts**: "PART 1", "Book II", "Volume Three", "SECTION 4"
- **Roman Numerals**: "I", "II.", "III)", "IV:"
- **Arabic Numbers**: "1", "2.", "3)"
- **Named Sections**: "Prologue", "Epilogue", "Introduction", "Foreword", "Appendix"
- **Drama**: "ACT I", "SCENE 1"

## Installation

### Step 1: Install pdfplumber in your virtual environment
```bash
# Activate your venv first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install pdfplumber
pip install pdfplumber
```

### Step 2: Verify Installation
```bash
python -c "import pdfplumber; print('✓ pdfplumber ready')"
```

## Testing

### Run the Test Suite
```bash
python test_chapter_detection.py
```

This will:
1. ✓ Test page number removal
2. ✓ Test chapter detection with cleanup
3. ✓ Show how to test with your own PDFs

### Test with Your PDF

**Option 1: Quick Test**
```python
from app.core.chapter_chunker import load_book, detect_chapters

# Load and clean PDF
text = load_book("your_book.pdf")

# Detect chapters
chapters = detect_chapters(text, min_chapter_length=1000)

# See results
for i, ch in enumerate(chapters, 1):
    print(f"{i}. {ch['title']} - {len(ch['text'])} chars")
```

**Option 2: Using the GUI**
1. Open the application
2. Go to "Book Processing" tab
3. Import your PDF (pdfplumber will automatically clean it)
4. Click "Detect Chapters"
5. Review detected chapters

### Troubleshooting

**Issue: pdfplumber not found in app**
- Solution: Activate your venv and reinstall
  ```bash
  source .venv/bin/activate
  pip install pdfplumber
  ```

**Issue: Page numbers still visible**
- The detection catches common patterns
- If your PDF uses unusual page numbering, you can:
  1. Manually review detected chapters in the GUI
  2. Edit/remove unwanted content
  3. Create an issue with your PDF format

**Issue: Chapters not detected**
- Make sure chapter titles are on their own line
- Keep chapter titles under 200 characters
- Ensure content after chapter title is at least 100 characters (configurable)

## How It Works

### Processing Flow:
```
1. PDF File
   ↓
2. Extract Text with pdfplumber
   ├─ Preserve layout information
   ├─ Get word positions
   ├─ Identify page zones (header/footer)
   ↓
3. Remove Artifacts
   ├─ Detect page numbers
   ├─ Remove lines matching page number patterns
   ├─ Normalize whitespace
   ↓
4. Detect Chapters
   ├─ Match chapter patterns (regex)
   ├─ Validate by length and context
   ├─ Group content into chapters
   ↓
5. Return Clean Chapters
```

### Code Examples

**Basic Usage:**
```python
from app.core.chapter_chunker import load_book, smart_chapter_detection

# Load PDF (auto-cleanup with pdfplumber)
text = load_book("book.pdf")

# Detect chapters smartly
chapters = smart_chapter_detection(text)

for chapter in chapters:
    print(f"Title: {chapter['title']}")
    print(f"Length: {len(chapter['text'])} chars")
```

**Advanced - Manual Cleanup:**
```python
from app.core.chapter_chunker import (
    _extract_pdf_with_pdfplumber,
    _remove_page_artifacts,
    _normalize_whitespace,
    detect_chapters
)

# Extract with formatting info
text, page_info = _extract_pdf_with_pdfplumber("book.pdf")

# Remove page numbers
cleaned = _remove_page_artifacts(text, page_info)

# Normalize spaces
cleaned = _normalize_whitespace(cleaned)

# Detect chapters
chapters = detect_chapters(cleaned)
```

## Implementation Details

### Page Number Detection Patterns
```python
# Matches:
r'^\s*-?\s*\d{1,4}\s*-?\s*$'    # " 1 ", "-1-", "123"
r'^\s*p\.?\s*\d+\s*$'           # "p. 1", "p1"
r'^\s*pp\.\s*\d+\s*$'           # "pp. 1"
```

### Chapter Pattern Detection
```python
# All patterns are regex-based for flexibility
# Examples:
CHAPTER 1          # matches
Chapter I          # matches
chapter TWO        # matches
PART 3             # matches
Book IV            # matches
I.                 # matches (roman numeral with period)
1)                 # matches (number with paren)
Prologue           # matches (special section)
```

## Configuration

### Customize Detection

**Adjust minimum chapter length:**
```python
chapters = detect_chapters(text, min_chapter_length=500)  # Default: 100
```

**Adjust in smart detection:**
```python
chapters = smart_chapter_detection(
    text,
    min_chapter_length=500,
    max_chunk_size=75000  # Max size per chapter
)
```

## Performance

- **Extraction**: Depends on PDF size (typically 1-5 seconds for 100+ page books)
- **Cleanup**: ~1 second for 100K characters
- **Detection**: ~100ms for typical books
- **Total**: Usually under 10 seconds for most books

## Limitations

1. **Unusual Layouts**: Very complex PDFs with multiple columns may not extract perfectly
2. **Scanned PDFs**: Can't process image-based PDFs (need OCR)
3. **Custom Page Numbers**: Unique formats might not be detected
4. **Language**: Patterns designed for English; may need adjustment for other languages

## Future Enhancements

- Font-size based header detection
- Bold/italic text analysis
- Multi-column support
- OCR for scanned PDFs
- Custom pattern configuration UI

## File Structure

```
app/core/chapter_chunker.py     # Main processing module
├─ load_book()                   # Entry point for all formats
├─ _extract_pdf_with_pdfplumber()  # PDF extraction
├─ _remove_page_artifacts()      # Page number removal
├─ _normalize_whitespace()       # Text cleanup
├─ detect_chapters()             # Chapter detection
├─ chunk_by_size()              # Fallback chunking
└─ smart_chapter_detection()    # Main orchestration

test_chapter_detection.py        # Test suite
CHAPTER_DETECTION_IMPROVEMENTS.md # This file
```

## Support

To test with your specific PDF:

1. **Save the PDF** to your project directory
2. **Run the test**:
   ```bash
   # Edit test_chapter_detection.py
   # Add your PDF path to: pdf_files = ["/path/to/your.pdf"]
   python test_chapter_detection.py
   ```

3. **Check the output**:
   - Are chapters detected correctly?
   - Are page numbers removed?
   - Does the text look clean?

4. **If there are issues**:
   - Share the PDF with details about what went wrong
   - Include sample of page numbers/headers you want removed
