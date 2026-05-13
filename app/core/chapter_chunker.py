# app/core/chapter_chunker.py

import os
import re
from typing import List, Dict, Optional, Tuple, Set

# Module-level cache for page info from most recent PDF load
_last_pdf_page_info: Optional[List[Dict]] = None


def _extract_pdf_with_pdfplumber(path: str) -> Tuple[str, List[Dict]]:
    """
    Extract PDF text with advanced formatting analysis and font metrics.
    Returns (cleaned_text, page_info_list with font data).
    """
    import pdfplumber

    text_parts = []
    page_info = []

    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            page_data = {
                "page_num": page_num,
                "raw_text": text,
                "lines": text.split('\n') if text else [],
                "char_count": len(text),
                "width": page.width,
                "height": page.height,
            }

            # Extract formatting information
            try:
                # Get words with position data
                words = page.extract_words()
                if words:
                    page_data["words"] = words
                    y_positions = [w["top"] for w in words]
                    page_data["avg_word_y"] = sum(y_positions) / len(y_positions) if y_positions else 0
                    page_data["header_zone"] = (0, page.height * 0.15)
                    page_data["footer_zone"] = (page.height * 0.85, page.height)

                # Get character-level data for font analysis
                chars = page.chars
                if chars:
                    page_data["chars"] = chars
                    # Build font metrics from characters
                    font_metrics = _extract_font_metrics(chars)
                    page_data["font_metrics"] = font_metrics
            except Exception as e:
                pass

            page_info.append(page_data)
            text_parts.append(text)

    return "\n\n".join(text_parts), page_info


def _extract_font_metrics(chars: List[Dict]) -> Dict[str, any]:
    """
    Extract font statistics from character objects.
    Returns dict with font sizes, names, bold info, etc.
    """
    if not chars:
        return {}

    font_sizes = []
    font_names = set()
    bold_fonts = set()

    for char in chars:
        size = char.get("size", 0)
        fontname = char.get("fontname", "").lower()

        if size > 0:
            font_sizes.append(size)

        if fontname:
            font_names.add(fontname)
            if "bold" in fontname:
                bold_fonts.add(fontname)

    if not font_sizes:
        return {}

    # Calculate statistics
    font_sizes.sort()
    median_idx = len(font_sizes) // 2
    median_size = font_sizes[median_idx]

    return {
        "sizes": font_sizes,
        "body_size": median_size,
        "min_size": min(font_sizes),
        "max_size": max(font_sizes),
        "avg_size": sum(font_sizes) / len(font_sizes),
        "font_names": list(font_names),
        "bold_fonts": list(bold_fonts),
        "char_count": len(chars),
    }



def _identify_page_numbers(text: str, page_info: List[Dict]) -> List[str]:
    """
    Identify common page number patterns.
    Returns list of regex patterns that match page numbers.
    """
    patterns = [
        r'^\s*-?\s*\d{1,4}\s*-?\s*$',  # " 1 ", "-1-", "123"
        r'^\s*p\.?\s*\d+\s*$',  # "p. 1", "p1"
        r'^\s*pp\.\s*\d+\s*$',  # "pp. 1"
    ]
    return patterns


def _remove_page_artifacts(text: str, page_info: List[Dict]) -> str:
    """
    Remove page numbers and common header/footer artifacts from text.
    Only removes lines that are clearly page artifacts, not content.
    """
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            cleaned_lines.append(line)
            continue

        is_page_marker = False

        # Check if this is clearly a page marker
        # Patterns for standalone markers
        page_marker_patterns = [
            r'^\s*p\.\s*\d+\s*$',  # "p. 123"
            r'^\s*pp\.\s*\d+\s*$',  # "pp. 123"
            r'^\s*-\s*\d+\s*-\s*$',  # "- 123 -"
            r'^\s*page\s+\d+\s*$',  # "page 123"
            r'^\s*\d{1,3}\s*$',  # Standalone page number
            # Multi-word book title followed by page number: "THE BRIGADE 123"
            r'^(?:\s*[A-Z]+){2,}\s+\d{1,3}\s*$',  # Multi-word titles + number
        ]

        for pattern in page_marker_patterns:
            if re.match(pattern, stripped, re.IGNORECASE):
                is_page_marker = True
                break

        # Remove mid-line page markers like "hunt THE BRIGADE 122 them"
        # Only if line contains multi-word titles followed by numbers
        if not is_page_marker and re.search(r'\s+[A-Z]+\s+[A-Z]+\s+\d{1,3}(?:\s+|$)', line):
            # Replace embedded markers with space
            line = re.sub(r'\s+[A-Z]+\s+[A-Z]+\s+\d{1,3}(?:\s+|$)', ' ', line, flags=re.IGNORECASE)

        if not is_page_marker:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def _normalize_whitespace(text: str) -> str:
    """Normalize excessive whitespace while preserving paragraph breaks."""
    # Replace multiple blank lines with double newline (paragraph break)
    text = re.sub(r'\n\n\n+', '\n\n', text)

    # Remove trailing whitespace from lines
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]
    text = '\n'.join(lines)

    return text


def load_book(path: str) -> str:
    """
    Load a book file (txt, epub, or pdf) and return its cleaned text content.
    For PDFs: uses pdfplumber for better formatting, removes page numbers/headers.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == ".epub":
        try:
            from ebooklib import epub
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("Please install ebooklib and beautifulsoup4 for EPUB support.")
        book = epub.read_epub(path)
        text_parts = []
        for item in book.get_items():
            if item.get_type() == 9:  # DOCUMENT
                soup = BeautifulSoup(item.get_body_content(), "html.parser")
                text_parts.append(soup.get_text())
        return "\n".join(text_parts)

    elif ext == ".pdf":
        try:
            import pdfplumber
            text, page_info = _extract_pdf_with_pdfplumber(path)
            # Cache page info for use in chapter detection
            global _last_pdf_page_info
            _last_pdf_page_info = page_info
            # Clean up page numbers and artifacts
            text = _remove_page_artifacts(text, page_info)
            text = _normalize_whitespace(text)
            return text
        except ImportError:
            # Fallback to PyPDF2
            try:
                import PyPDF2
            except ImportError:
                raise ImportError(
                    "Please install pdfplumber for better PDF support:\n"
                    "  pip install pdfplumber"
                )
            text_parts = []
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
            text = "\n".join(text_parts)
            text = _normalize_whitespace(text)
            return text

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _detect_chapters_by_font_size(lines: List[str], page_info: List[Dict], font_size_threshold: float = 1.3) -> List[Dict]:
    """
    Detect chapter candidates based on font size (significantly larger than body text).
    Returns list of {line_num, text, font_size, confidence}.
    """
    candidates = []

    if not page_info:
        return candidates

    # Aggregate font metrics from all pages
    all_sizes = []
    for page in page_info:
        if "font_metrics" in page and "sizes" in page["font_metrics"]:
            all_sizes.extend(page["font_metrics"]["sizes"])

    if not all_sizes:
        return candidates

    # Calculate body font size
    all_sizes.sort()
    body_size = all_sizes[len(all_sizes) // 2]  # Median
    large_font_threshold = body_size * font_size_threshold

    # Check each line for larger font
    # Map words to lines
    line_fonts = {}
    for page in page_info:
        if "words" not in page:
            continue
        for word in page["words"]:
            font_size = word.get("size", 0)
            if font_size > 0 and font_size >= large_font_threshold:
                # Find which line this word belongs to
                word_text = word.get("text", "")
                for line_idx, line_text in enumerate(lines):
                    if word_text in line_text:
                        if line_idx not in line_fonts:
                            line_fonts[line_idx] = []
                        line_fonts[line_idx].append(font_size)

    # Assess each line with large fonts
    for line_idx, sizes in line_fonts.items():
        avg_size = sum(sizes) / len(sizes) if sizes else body_size
        confidence = min(1.0, (avg_size - body_size) / body_size)  # Scale to 0-1
        candidates.append({
            "line_num": line_idx,
            "text": lines[line_idx],
            "font_size": avg_size,
            "confidence_font": confidence,
        })

    return candidates


def _detect_chapters_by_bold(lines: List[str], page_info: List[Dict]) -> List[Dict]:
    """
    Detect chapter candidates based on bold text.
    Returns list of {line_num, text, is_bold, confidence}.
    """
    candidates = []

    if not page_info:
        return candidates

    # Map which lines contain bold text
    for page in page_info:
        if "chars" not in page:
            continue

        bold_chars = [c for c in page["chars"] if "bold" in c.get("fontname", "").lower()]
        if not bold_chars:
            continue

        # Get text of bold characters
        bold_text_snippets = set()
        for char in bold_chars:
            text = char.get("text", "")
            if text.strip():
                bold_text_snippets.add(text)

        # Find lines with significant bold content
        for line_idx, line_text in enumerate(lines):
            bold_char_count = sum(1 for c in bold_text_snippets if c in line_text)
            if bold_char_count > len(line_text) * 0.5:  # > 50% bold
                confidence = min(1.0, bold_char_count / len(line_text))
                candidates.append({
                    "line_num": line_idx,
                    "text": line_text,
                    "is_bold": True,
                    "confidence_bold": confidence,
                })

    return candidates


def _filter_false_positives_bankruptcy(chapters: List[Dict], text: str) -> List[Dict]:
    """Filter out 'Chapter 11' when in bankruptcy context."""
    bankruptcy_keywords = [
        "bankruptcy", "creditor", "debtor", "court", "filing", "filed",
        "section 11", "title 11", "discharge", "petition", "trustee",
        "claim", "lien", "repayment", "liquidation", "reorganization",
        "contractor", "sub-contractor", "sub contractor", "subcontractor",
        "employee", "payroll", "benefits", "wage"
    ]

    filtered = []
    text_lower = text.lower()
    lines = text.split('\n')

    for chapter in chapters:
        # Check if chapter title contains "Chapter 11"
        if "chapter 11" not in chapter.get("title", "").lower():
            filtered.append(chapter)
            continue

        # If it does, check context (±10 lines)
        start_line = max(0, chapter.get("start_line", 0) - 10)
        end_line = min(len(lines), chapter.get("start_line", 0) + 10)
        context = "\n".join(lines[start_line:end_line]).lower()

        # Check for bankruptcy keywords
        has_bankruptcy_context = any(kw in context for kw in bankruptcy_keywords)

        if not has_bankruptcy_context:
            filtered.append(chapter)
        # else: filtered out due to bankruptcy context

    return filtered


def _filter_false_positives_paragraph_boundary(chapters: List[Dict], text: str) -> List[Dict]:
    """Filter chapter markers that appear mid-paragraph (no clear boundaries)."""
    filtered = []
    lines = text.split('\n')

    for chapter in chapters:
        start_line = chapter.get("start_line", 0)

        # Check if there are empty lines before and after
        has_empty_before = start_line == 0 or lines[start_line - 1].strip() == ""
        has_empty_after = (start_line + 1 >= len(lines) or
                          lines[start_line + 1].strip() == "")

        # Accept if has boundaries, otherwise lower confidence
        if has_empty_before and has_empty_after:
            filtered.append(chapter)
        else:
            # Lower confidence but keep it
            chapter_copy = chapter.copy()
            chapter_copy["confidence"] = chapter_copy.get("confidence", 1.0) * 0.7
            filtered.append(chapter_copy)

    return filtered


def _filter_false_positives_duplicates(chapters: List[Dict]) -> List[Dict]:
    """Merge or remove duplicate chapters detected twice."""
    if len(chapters) < 2:
        return chapters

    filtered = []
    doc_length = sum(len(c.get("text", "")) for c in chapters)
    seen_titles = set()

    for chapter in chapters:
        title = chapter.get("title", "").strip()

        # Check if we've seen this title recently (within 5% of document)
        proximity_threshold = doc_length * 0.05

        # Simple duplicate check - exact title match
        if title in seen_titles:
            continue  # Skip duplicate

        seen_titles.add(title)
        filtered.append(chapter)

    return filtered


def _merge_formatting_signals(text_candidates: List[Dict], font_candidates: List[Dict],
                             bold_candidates: List[Dict]) -> List[Dict]:
    """
    Merge detections from all three signals into unified list with confidence scores.
    Confidence formula: Font(0.35) + Bold(0.25) + Text(0.30) + Position(0.10)
    """
    merged = {}  # line_num -> merged candidate

    # Start with text-based candidates
    for candidate in text_candidates:
        line_num = candidate.get("line_num", candidate.get("start_line", 0))
        merged[line_num] = {
            "line_num": line_num,
            "text": candidate.get("title", candidate.get("text", "")),
            "start_line": candidate.get("start_line", line_num),
            "title": candidate.get("title", candidate.get("text", "")),
            "confidence_text": 0.8,  # Text pattern match is strong signal
            "confidence_font": 0,
            "confidence_bold": 0,
            "confidence_position": 0.1,  # Default position score
            "detection_methods": ["text_pattern"],
        }

    # Add font-based candidates
    for candidate in font_candidates:
        line_num = candidate.get("line_num", 0)
        if line_num in merged:
            merged[line_num]["confidence_font"] = candidate.get("confidence_font", 0)
            merged[line_num]["detection_methods"].append("font_size")
        else:
            merged[line_num] = {
                "line_num": line_num,
                "text": candidate.get("text", ""),
                "title": candidate.get("text", ""),
                "confidence_text": 0,
                "confidence_font": candidate.get("confidence_font", 0),
                "confidence_bold": 0,
                "confidence_position": 0.1,
                "detection_methods": ["font_size"],
            }

    # Add bold-based candidates
    for candidate in bold_candidates:
        line_num = candidate.get("line_num", 0)
        if line_num in merged:
            merged[line_num]["confidence_bold"] = candidate.get("confidence_bold", 0)
            merged[line_num]["detection_methods"].append("bold")
        else:
            merged[line_num] = {
                "line_num": line_num,
                "text": candidate.get("text", ""),
                "title": candidate.get("text", ""),
                "confidence_text": 0,
                "confidence_font": 0,
                "confidence_bold": candidate.get("confidence_bold", 0),
                "confidence_position": 0.1,
                "detection_methods": ["bold"],
            }

    # Calculate combined confidence
    result = []
    for line_num, candidate in sorted(merged.items()):
        # If strong text pattern match (>= 0.7), prioritize it
        if candidate["confidence_text"] >= 0.7:
            total_confidence = candidate["confidence_text"]
        else:
            # Otherwise use weighted formula
            total_confidence = (
                candidate["confidence_font"] * 0.35 +
                candidate["confidence_bold"] * 0.25 +
                candidate["confidence_text"] * 0.30 +
                candidate["confidence_position"] * 0.10
            )
        candidate["confidence"] = total_confidence
        result.append(candidate)

    return result


def detect_chapters(text: str, min_chapter_length: int = 100) -> List[Dict]:
    """
    Detect chapters - conservative matching focusing on chapter markers.
    """
    chapters = []
    lines = text.split('\n')

    # Extract chapter marker at start of line, optionally with short title
    # Matches: "CHAPTER 1", "Chapter 2: Title", "PART I - Something", etc.
    # But stops at realistic chapter title lengths
    def extract_chapter_title(line_text: str) -> Optional[str]:
        """Extract chapter title from a line, being conservative."""
        s = line_text.strip()

        # Exact named sections (case-insensitive match)
        if re.match(r'^(Prologue|Epilogue|Preface|Foreword|Introduction|Afterword|Interlude|Conclusion|Coda|Appendix)\s*$', s, re.IGNORECASE):
            return s

        # Chapter/Part/etc with NUMBER - must be digits or uppercase Roman numerals ONLY
        # We'll check for both cases by using two separate patterns
        patterns = [
            # All caps
            r"^((?:CHAPTER|PART|BOOK|VOLUME|SECTION|ACT|SCENE)\s+(?:[0-9]+|[IVXLCDM]+)\s*[\.\:\-]?)\s*",
            # Mixed case
            r"^((?:[Cc]hapter|[Pp]art|[Bb]ook|[Vv]olume|[Ss]ection|[Aa]ct|[Ss]cene)\s+(?:[0-9]+|[IVXLCDM]+)\s*[\.\:\-]?)\s*",
            # Standalone Roman numerals with title: "I. Title", "II. – Title", etc.
            # Require at least 2 chars of Roman numerals OR allow single I/V/X followed by period/dash
            r"^((?:[IVX]{2,}|[IVX])[\.\-\:])\s*",
        ]

        for pattern_idx, pattern in enumerate(patterns):
            match = re.match(pattern, s)  # Note: no flags, case-sensitive
            if match:
                base = match.group(1)
                rest = s[match.end():].strip()

                # For single-letter Roman numerals (pattern 2, the third one), be strict
                if pattern_idx == 2 and len(base) == 2:  # Single letter + punct like "X-"
                    # Reject if followed by lowercase letter (not a title)
                    if rest and rest[0].islower():
                        continue  # Try next pattern
                    # Reject if nothing meaningful follows
                    if not rest or len(rest) < 3:
                        # Only accept if it's just the marker (like "X." alone)
                        if s in ("I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX.", "X.",
                                "XI.", "XII.", "XIII.", "XIV.", "XV.", "XVI.", "XVII.", "XVIII.", "XIX.",
                                "XX.", "XXI.", "XXII.", "XXIII.", "XXIV.", "XXV.", "XXVI.", "XXVII.",
                                "XXVIII.", "XXIX.", "XXX.") or \
                           s.startswith(("I. ", "II. ", "III. ", "IV. ", "V. ", "VI. ", "VII. ", "VIII. ",
                                        "IX. ", "X. ", "XI. ", "XII. ")):
                            return base
                        continue  # Skip this match

                # If nothing after marker, use the marker
                if not rest:
                    return base

                # If there's text after, include it but cap at reasonable length
                if len(rest) > 0 and len(rest) <= 60 and rest[0].isupper():
                    full = (base + ' ' + rest).strip()
                    return full[:80]

                # Otherwise, just return the chapter marker
                return base

        return None

    current_chapter = {"title": "Opening", "text": [], "start_line": 0}
    empty_count = 0

    for line_idx, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            empty_count += 1
            current_chapter["text"].append(line)
            continue

        is_chapter = False
        chapter_title = None

        # Try to extract chapter title
        chapter_title = extract_chapter_title(stripped)
        if chapter_title and len(chapter_title) < 100:
            is_chapter = True

        # Standalone numbers/roman (strict - only after empty line)
        if not is_chapter and empty_count >= 1 and len(stripped) <= 10:
            if re.match(r'^[IVXLCDM]{1,8}[\.\)]?\s*$', stripped, re.IGNORECASE) or \
               re.match(r'^\d{1,3}[\.\)]?\s*$', stripped):
                is_chapter = True
                chapter_title = stripped

        empty_count = 0

        if is_chapter and len(current_chapter["text"]) > 0:
            chapter_text = '\n'.join(current_chapter["text"])
            if len(chapter_text.strip()) >= min_chapter_length:
                chapters.append({
                    "title": current_chapter["title"],
                    "text": chapter_text,
                    "start_line": current_chapter["start_line"]
                })
            current_chapter = {
                "title": chapter_title or f"Chapter {len(chapters) + 1}",
                "text": [line],
                "start_line": line_idx
            }
        else:
            current_chapter["text"].append(line)

    # Add final chapter
    if current_chapter["text"]:
        chapter_text = '\n'.join(current_chapter["text"])
        if len(chapter_text.strip()) >= min_chapter_length:
            chapters.append({
                "title": current_chapter["title"],
                "text": chapter_text,
                "start_line": current_chapter["start_line"]
            })

    return chapters


def chunk_by_size(text: str, target_chunk_size: int = 50000, overlap: int = 500):
    """
    Split text into manageable chunks by size when no chapters are detected.
    Uses sentence boundaries to avoid breaking mid-sentence.
    
    Args:
        text: The text to chunk
        target_chunk_size: Target size in characters (default ~50K chars)
        overlap: Number of characters to overlap between chunks for context
    
    Returns:
        List of {"title": str, "text": str, "chunk_num": int}
    """
    chunks = []
    
    # Split into sentences (rough approximation)
    sentence_endings = re.compile(r'([.!?]+[\s\n]+)')
    sentences = sentence_endings.split(text)
    
    # Recombine sentences with their punctuation
    combined_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            combined_sentences.append(sentences[i] + sentences[i + 1])
        else:
            combined_sentences.append(sentences[i])
    
    current_chunk = []
    current_length = 0
    chunk_num = 1
    
    for sentence in combined_sentences:
        sentence_len = len(sentence)
        
        if current_length + sentence_len > target_chunk_size and current_chunk:
            # Save current chunk
            chunk_text = ''.join(current_chunk)
            chunks.append({
                "title": f"Section {chunk_num}",
                "text": chunk_text,
                "chunk_num": chunk_num
            })
            
            # Start new chunk with overlap
            overlap_text = chunk_text[-overlap:] if len(chunk_text) > overlap else chunk_text
            current_chunk = [overlap_text, sentence]
            current_length = len(overlap_text) + sentence_len
            chunk_num += 1
        else:
            current_chunk.append(sentence)
            current_length += sentence_len
    
    # Add final chunk
    if current_chunk:
        chunks.append({
            "title": f"Section {chunk_num}",
            "text": ''.join(current_chunk),
            "chunk_num": chunk_num
        })
    
    return chunks


def detect_chapters_with_formatting(text: str, page_info: List[Dict] = None,
                                   min_chapter_length: int = 100,
                                   font_size_threshold: float = 1.3) -> List[Dict]:
    """
    Enhanced chapter detection using both text patterns and formatting signals.
    Falls back to text-only detection if font data unavailable.

    Args:
        text: Book text
        page_info: Optional list of page info dicts with font metrics
        min_chapter_length: Minimum chapter length in characters
        font_size_threshold: Font size multiplier for large text (1.2, 1.3, or 1.5)

    Returns:
        List of detected chapters with confidence scores
    """
    # Fall back to text-only if no formatting data available
    if not page_info or not any(p.get("font_metrics") for p in page_info):
        chapters = detect_chapters(text, min_chapter_length)
        return chapters

    lines = text.split('\n')

    # Get text-based detections first
    text_based_chapters = detect_chapters(text, min_chapter_length=100)  # Lower threshold for detection
    text_candidates = [
        {
            "line_num": ch.get("start_line", 0),
            "text": ch["title"],
            "title": ch["title"],
            "start_line": ch.get("start_line", 0),
        }
        for ch in text_based_chapters
    ]

    # Get formatting-based detections
    font_candidates = _detect_chapters_by_font_size(lines, page_info, font_size_threshold)
    bold_candidates = _detect_chapters_by_bold(lines, page_info)

    # Merge all signals
    merged = _merge_formatting_signals(text_candidates, font_candidates, bold_candidates)

    # Filter for confidence threshold (0.4 = 40%)
    # Lower threshold to allow text-pattern matches with minimal other signals
    min_confidence = 0.4
    filtered = [c for c in merged if c.get("confidence", 0) >= min_confidence]

    # Apply false-positive filters
    # Convert to chapter format for filtering
    formatted_chapters = []
    for item in filtered:
        formatted_chapters.append({
            "title": item.get("title", ""),
            "text": "",  # Will be populated later
            "start_line": item.get("start_line", 0),
            "confidence": item.get("confidence", 0),
        })

    # Apply all three false-positive filters
    formatted_chapters = _filter_false_positives_bankruptcy(formatted_chapters, text)
    formatted_chapters = _filter_false_positives_paragraph_boundary(formatted_chapters, text)
    formatted_chapters = _filter_false_positives_duplicates(formatted_chapters)

    # Now build full chapters with text content
    final_chapters = []
    for i, chapter in enumerate(formatted_chapters):
        start_line = chapter.get("start_line", 0)
        # Find end of chapter (start of next chapter or end of text)
        if i + 1 < len(formatted_chapters):
            end_line = formatted_chapters[i + 1].get("start_line", len(lines))
        else:
            end_line = len(lines)

        chapter_text = '\n'.join(lines[start_line:end_line])
        if len(chapter_text.strip()) >= min_chapter_length:
            chapter["text"] = chapter_text
            final_chapters.append(chapter)

    return final_chapters if final_chapters else text_based_chapters


def smart_chapter_detection(text: str, min_chapter_length: int = 1000,
                           max_chunk_size: int = 50000, page_info: List[Dict] = None,
                           font_size_threshold: float = 1.3):
    """
    Smart chapter detection that falls back to size-based chunking.

    1. Try to detect actual chapters using text patterns and formatting signals
    2. If no chapters found, use size-based chunking
    3. If only 1 chapter found and book is large, use size-based chunking

    Args:
        text: Book text
        min_chapter_length: Minimum length to consider a chapter valid
        max_chunk_size: Maximum size before forcing a split
        page_info: Optional page info with font metrics for formatting-based detection
        font_size_threshold: Threshold for font size detection (1.2, 1.3, or 1.5)

    Returns:
        List of {"title": str, "text": str}
    """
    # Try to detect chapters using formatting signals if available, else text patterns
    if page_info is None:
        # Try to use cached page info from last PDF load
        global _last_pdf_page_info
        page_info = _last_pdf_page_info

    chapters = detect_chapters_with_formatting(
        text,
        page_info=page_info,
        min_chapter_length=100,
        font_size_threshold=font_size_threshold
    )
    
    # If no chapters detected, use size-based chunking
    if len(chapters) == 0:
        print(f"[ChapterChunker] No chapter markers found. Using size-based chunking.")
        return chunk_by_size(text, target_chunk_size=max_chunk_size)
    
    # If only 1 chapter found and the book is large, probably failed to detect properly
    if len(chapters) == 1 and len(text) > max_chunk_size:
        print(f"[ChapterChunker] Only 1 chapter in large book ({len(text)} chars). Using size-based chunking.")
        return chunk_by_size(text, target_chunk_size=max_chunk_size)
    
    # Keep chapters intact - do NOT sub-chunk them
    # Users want full chapters preserved regardless of size
    final_chunks = []
    for chapter in chapters:
        final_chunks.append({
            "title": chapter["title"],
            "text": chapter["text"]
        })
        # Just log if chapter is large, but don't split it
        if len(chapter["text"]) > max_chunk_size:
            print(f"[ChapterChunker] Note: Chapter '{chapter['title']}' is large ({len(chapter['text'])} chars), keeping intact")
    
    print(f"[ChapterChunker] Detected {len(final_chunks)} chapter(s)")
    return final_chunks


# Legacy function for backward compatibility
def chunk_text(text: str, max_chars: int = 50000):
    """
    Legacy function - now uses smart_chapter_detection.
    Break text into chunks (by chapter or fixed size).
    """
    return smart_chapter_detection(text, max_chunk_size=max_chars)
