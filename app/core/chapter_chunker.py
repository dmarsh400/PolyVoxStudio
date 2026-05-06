# app/core/chapter_chunker.py

import os
import re


def load_book(path: str) -> str:
    """
    Load a book file (txt, epub, or pdf) and return its text content.
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
            import PyPDF2
        except ImportError:
            raise ImportError("Please install PyPDF2 for PDF support.")
        text_parts = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def detect_chapters(text: str, min_chapter_length: int = 100):
    """
    Detect chapters using multiple common formats.
    Returns list of {"title": str, "text": str, "start_pos": int}
    
    Supported formats:
    - "CHAPTER 1", "CHAPTER ONE", "Chapter 1:", "Chapter I"
    - "1.", "1)", "I.", "I)" at start of line (Roman numerals)
    - "Part 1", "Part One", "PART I"
    - "Prologue", "Epilogue", "Preface", "Introduction"
    - Numbered sections like "1", "2", "3" when centered or standalone
    """
    
    chapters = []
    lines = text.split('\n')
    
    # Multiple chapter detection patterns
    patterns = [
        # Standard chapter formats (more flexible - matches trailing content)
        r'^\s*CHAPTER\s+([IVXLCDM]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)',
        r'^\s*Chapter\s+([IVXLCDM]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)',
        r'^\s*chapter\s+([IVXLCDM]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)',
        
        # Part formats
        r'^\s*PART\s+([IVXLCDM]+|\d+|one|two|three|four|five)',
        r'^\s*Part\s+([IVXLCDM]+|\d+|one|two|three|four|five)',
        
        # Special sections (exact match)
        r'^\s*(Prologue|Epilogue|Preface|Introduction|Foreword|Afterword|Interlude)\s*$',
    ]
    
    # Compile all patterns
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    # Special pattern for standalone Roman numerals or numbers (be more careful with these)
    standalone_patterns = [
        re.compile(r'^\s*([IVXLCDM]{1,8})[\.\):]?\s*$'),  # Roman numerals I, II, III, etc.
        re.compile(r'^\s*(\d{1,3})[\.\):]?\s*$'),          # Arabic numbers 1, 2, 3, etc.
    ]
    
    current_chapter = {"title": "Opening", "text": [], "start_line": 0}
    last_was_empty = False
    
    for line_idx, line in enumerate(lines):
        is_chapter_marker = False
        chapter_title = None
        
        stripped = line.strip()
        
        # Skip completely empty lines
        if not stripped:
            current_chapter["text"].append(line)
            last_was_empty = True
            continue
        
        # Check main patterns first
        for pattern in compiled_patterns:
            match = pattern.match(stripped)
            if match:
                # Length validation: chapter headers are usually short
                if len(stripped) < 100:
                    is_chapter_marker = True
                    chapter_title = stripped
                    break
        
        # Check standalone patterns only if preceded by empty line (more strict)
        if not is_chapter_marker and last_was_empty and len(stripped) < 20:
            for pattern in standalone_patterns:
                match = pattern.match(stripped)
                if match:
                    is_chapter_marker = True
                    chapter_title = stripped
                    break
        
        if is_chapter_marker and len(current_chapter["text"]) > 0:
            # Save previous chapter if it has content
            chapter_text = '\n'.join(current_chapter["text"])
            text_length = len(chapter_text.strip())
            
            # Only save if meets minimum length
            if text_length >= min_chapter_length:
                chapters.append({
                    "title": current_chapter["title"],
                    "text": chapter_text,
                    "start_line": current_chapter["start_line"]
                })
            elif text_length > 0:
                # If below minimum, might be just whitespace or title page
                # Include it in next chapter as preamble
                pass
            
            # Start new chapter
            current_chapter = {
                "title": chapter_title if chapter_title else f"Chapter {len(chapters) + 1}",
                "text": [line],
                "start_line": line_idx
            }
        else:
            current_chapter["text"].append(line)
        
        last_was_empty = (not stripped)
    
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


def smart_chapter_detection(text: str, min_chapter_length: int = 1000, 
                           max_chunk_size: int = 50000):
    """
    Smart chapter detection that falls back to size-based chunking.
    
    1. Try to detect actual chapters using multiple formats
    2. If no chapters found, use size-based chunking
    3. If only 1 chapter found and book is large, use size-based chunking
    4. If chapters are too large, sub-chunk them
    
    Args:
        text: Book text
        min_chapter_length: Minimum length to consider a chapter valid
        max_chunk_size: Maximum size before forcing a split
    
    Returns:
        List of {"title": str, "text": str}
    """
    # Try to detect chapters with lower threshold for detection phase
    chapters = detect_chapters(text, min_chapter_length=100)
    
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
