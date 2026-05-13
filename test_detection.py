#!/usr/bin/env python3
"""Test chapter detection speed."""

import time
import sys
from app.core.chapter_chunker import _extract_pdf_with_pdfplumber, _remove_page_artifacts, _normalize_whitespace, smart_chapter_detection

test_pdf = "/home/moderatec/Desktop/Book 1 TheBrigade.pdf"

try:
    print("Loading PDF...")
    extract_start = time.time()
    text, page_info = _extract_pdf_with_pdfplumber(test_pdf)
    text = _remove_page_artifacts(text, page_info)
    text = _normalize_whitespace(text)
    load_time = time.time() - extract_start
    print(f"✓ Loaded in {load_time:.2f}s")

    # Test chapter detection
    for threshold in [1.2, 1.3, 1.5]:
        detect_start = time.time()
        chapters = smart_chapter_detection(
            text,
            page_info=page_info,
            min_chapter_length=1000,
            max_chunk_size=50000,
            font_size_threshold=threshold
        )
        detect_time = time.time() - detect_start
        print(f"\n{threshold}x threshold: {len(chapters)} chapters in {detect_time:.2f}s")
        for i, ch in enumerate(chapters[:5]):
            preview = ch['title'][:40].replace('\n', ' ')
            print(f"  {i+1}. {preview}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
