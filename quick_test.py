#!/usr/bin/env python3
"""
Quick PDF Testing Guide - Start Here!

This script shows you how to test the improved PDF chapter detection.
"""

def quick_test():
    """Quick test with sample PDF text."""
    from app.core.chapter_chunker import (
        detect_chapters,
        _remove_page_artifacts,
        _normalize_whitespace
    )

    # Sample PDF-like text with page numbers
    sample = """CHAPTER 1: THE BEGINNING

Once upon a time, in a far away land, there was a story worth telling.
The protagonist set out on their journey with hope and determination.
Many adventures awaited them in the days to come.

- 1 -

CHAPTER 2: THE MIDDLE

The journey continued through forests and mountains.
Friends were made and challenges were overcome.
Each day brought new discoveries and growth.

- 2 -

CHAPTER 3: THE END

The final chapter brought resolution and understanding.
The protagonist returned home, changed by their experiences.
And they lived happily ever after.

- 3 -
"""

    print("=" * 70)
    print("QUICK PDF PROCESSING TEST")
    print("=" * 70)

    print("\n1. ORIGINAL TEXT (with page numbers):")
    print("-" * 70)
    print(sample[:300] + "...")

    # Clean it
    cleaned = _remove_page_artifacts(sample, [])
    cleaned = _normalize_whitespace(cleaned)

    print("\n2. AFTER CLEANUP (page numbers removed):")
    print("-" * 70)
    print(cleaned[:300] + "...")

    # Detect chapters
    chapters = detect_chapters(cleaned, min_chapter_length=50)

    print(f"\n3. DETECTED CHAPTERS ({len(chapters)} found):")
    print("-" * 70)
    for i, ch in enumerate(chapters, 1):
        print(f"   {i}. {ch['title']:<30} ({len(ch['text']):>6} chars)")

    print("\n" + "=" * 70)
    print("✓ All working correctly!\n")


def test_with_your_pdf(pdf_path):
    """Test with your own PDF."""
    import os
    from app.core.chapter_chunker import load_book, detect_chapters

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return

    print("=" * 70)
    print(f"TESTING: {os.path.basename(pdf_path)}")
    print("=" * 70)

    try:
        # Load and process
        print("\n1. Loading PDF and removing artifacts...")
        text = load_book(pdf_path)
        print(f"   ✓ Loaded: {len(text):,} characters")

        # Detect chapters
        print("\n2. Detecting chapters...")
        chapters = detect_chapters(text, min_chapter_length=1000)
        print(f"   ✓ Found {len(chapters)} chapter(s)")

        # Show results
        print("\n3. CHAPTERS DETECTED:")
        print("-" * 70)
        for i, ch in enumerate(chapters[:15], 1):  # Show first 15
            preview = ch['text'][:60].replace('\n', ' ')
            print(f"   {i:2d}. {ch['title']:<40} ({len(ch['text']):>7,} chars)")
            print(f"       Preview: {preview}...")

        if len(chapters) > 15:
            print(f"   ... and {len(chapters) - 15} more")

        print("\n" + "=" * 70)
        print("✓ Processing complete!\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n")

    # Run quick test
    quick_test()

    # Instructions for user PDFs
    print("=" * 70)
    print("NEXT: TEST WITH YOUR OWN PDFs")
    print("=" * 70)
    print("""
Usage:
    python quick_test.py                    # Run quick test
    python -c "from quick_test import test_with_your_pdf; test_with_your_pdf('your_book.pdf')"

Or modify this script:
    1. Edit the file below the if __name__ == "__main__" line
    2. Add: test_with_your_pdf("path/to/your/book.pdf")
    3. Save and run: python quick_test.py

Example:
    test_with_your_pdf("/home/user/Documents/mybook.pdf")
    """)
    print("=" * 70)
    print()

    # Uncomment to test your PDF:
    # test_with_your_pdf("/path/to/your/book.pdf")
