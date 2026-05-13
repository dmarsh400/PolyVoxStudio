#!/usr/bin/env python3
"""Test script to verify PDF loading and chapter detection without freezing."""

import time
import sys
from app.core.chapter_chunker import load_book, smart_chapter_detection

# Test PDF path
test_pdf = "/home/moderatec/Desktop/Book 1 TheBrigade.pdf"

print("Starting PDF load test...")
start_time = time.time()

try:
    print("Loading book...")
    raw_text = load_book(test_pdf)
    load_time = time.time() - start_time
    print(f"✓ Book loaded in {load_time:.2f}s ({len(raw_text):,} chars)")

    # Show first 500 chars
    print(f"\nFirst 500 chars:\n{raw_text[:500]}")
    print("\n...")

    # Test chapter detection with different thresholds
    for threshold in [1.2, 1.3, 1.5]:
        detect_start = time.time()
        print(f"\nDetecting chapters with threshold {threshold}x...")
        chapters = smart_chapter_detection(
            raw_text,
            min_chapter_length=1000,
            max_chunk_size=50000,
            font_size_threshold=threshold
        )
        detect_time = time.time() - detect_start
        print(f"✓ Detected {len(chapters)} chapters in {detect_time:.2f}s")

        # Show first 3 chapter titles
        for i, ch in enumerate(chapters[:3]):
            print(f"  {i+1}. {ch['title'][:50]}")

    print("\n✓ All tests passed!")
    sys.exit(0)

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
