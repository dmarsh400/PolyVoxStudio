#!/usr/bin/env python3
"""Debug script to test page artifact removal."""

import time
import sys
from app.core.chapter_chunker import _extract_pdf_with_pdfplumber, _remove_page_artifacts, _normalize_whitespace

test_pdf = "/home/moderatec/Desktop/Book 1 TheBrigade.pdf"

print("Starting PDF extraction test...")
start_time = time.time()

try:
    print("1. Extracting PDF with pdfplumber...")
    extract_start = time.time()
    text, page_info = _extract_pdf_with_pdfplumber(test_pdf)
    extract_time = time.time() - extract_start
    print(f"   ✓ Extracted in {extract_time:.2f}s ({len(text):,} chars)")

    print("2. Removing page artifacts...")
    artifact_start = time.time()
    text = _remove_page_artifacts(text, page_info)
    artifact_time = time.time() - artifact_start
    print(f"   ✓ Cleaned in {artifact_time:.2f}s ({len(text):,} chars)")

    print("3. Normalizing whitespace...")
    normalize_start = time.time()
    text = _normalize_whitespace(text)
    normalize_time = time.time() - normalize_start
    print(f"   ✓ Normalized in {normalize_time:.2f}s ({len(text):,} chars)")

    total_time = time.time() - start_time
    print(f"\nTotal time: {total_time:.2f}s")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
