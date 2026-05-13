#!/usr/bin/env python3
"""Debug script to find where the freezing occurs."""

import time
import sys
from app.core.chapter_chunker import _extract_pdf_with_pdfplumber

test_pdf = "/home/moderatec/Desktop/Book 1 TheBrigade.pdf"

print("Starting PDF extraction test...")
start_time = time.time()

try:
    print("Extracting PDF with pdfplumber...")
    text, page_info = _extract_pdf_with_pdfplumber(test_pdf)
    extract_time = time.time() - start_time
    print(f"✓ PDF extracted in {extract_time:.2f}s ({len(text):,} chars)")
    print(f"Page info length: {len(page_info)}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
