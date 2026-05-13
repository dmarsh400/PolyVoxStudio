#!/usr/bin/env python3
"""
Advanced PDF processing test - demonstrates chapter detection and cleanup.
"""

from app.core.chapter_chunker import load_book, detect_chapters, _remove_page_artifacts
import os
import tempfile


def create_test_pdf_text_with_artifacts():
    """Create sample text that simulates a PDF with page numbers, headers, etc."""
    return """Chapter 1: The Beginning

This is the first chapter with actual content.
It describes the opening of our story.

- 1 -

Chapter 2: The Middle

More content goes here.
The story continues with important information.

- 2 -

Chapter 3: The End

The final chapter wraps up the narrative.

- 3 -
"""


def test_page_number_removal():
    """Test that page numbers are properly removed."""
    print("=" * 60)
    print("Testing Page Number Removal")
    print("=" * 60)

    sample_text = create_test_pdf_text_with_artifacts()
    print("\nOriginal text (with page numbers):")
    print(sample_text)

    # Clean it
    cleaned = _remove_page_artifacts(sample_text, [])
    print("\nCleaned text (page numbers removed):")
    print(cleaned)

    # Verify page numbers are gone
    if "- 1 -" not in cleaned and "- 2 -" not in cleaned and "- 3 -" not in cleaned:
        print("\n✓ Page numbers successfully removed!")
    else:
        print("\n✗ Some page numbers still present")

    print()


def test_chapter_detection_with_cleanup():
    """Test chapter detection after cleanup."""
    print("=" * 60)
    print("Testing Chapter Detection After Cleanup")
    print("=" * 60)

    sample_text = create_test_pdf_text_with_artifacts()

    # Clean up first
    cleaned = _remove_page_artifacts(sample_text, [])

    # Then detect chapters
    chapters = detect_chapters(cleaned, min_chapter_length=50)

    print(f"\nDetected {len(chapters)} chapters:\n")
    for i, chapter in enumerate(chapters, 1):
        print(f"{i}. {chapter['title']}")
        print(f"   Length: {len(chapter['text'])} chars")
        preview = chapter["text"][:80].replace("\n", " ")
        print(f"   Preview: {preview}...\n")

    if len(chapters) >= 3:
        print("✓ Successfully detected multiple chapters!")
    else:
        print("✗ Expected to find more chapters")


def test_with_real_pdf(pdf_path):
    """Test with a real PDF file."""
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return

    print("=" * 60)
    print(f"Testing Real PDF: {os.path.basename(pdf_path)}")
    print("=" * 60)

    try:
        # Load and clean
        text = load_book(pdf_path)
        print(f"\n✓ Loaded PDF ({len(text)} chars after cleanup)")

        # Detect chapters
        chapters = detect_chapters(text, min_chapter_length=100)
        print(f"✓ Detected {len(chapters)} chapter(s)")

        # Show preview
        if chapters:
            print("\nChapter titles:")
            for i, ch in enumerate(chapters[:10], 1):  # Show first 10
                print(f"  {i}. {ch['title']} ({len(ch['text'])} chars)")

            print(f"\nFirst chapter preview (first 200 chars):")
            print("-" * 60)
            print(chapters[0]["text"][:200].replace("\n", " ") + "...")
            print("-" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    print("\n" + "=" * 60)
    print("PDF Processing Test Suite")
    print("=" * 60 + "\n")

    # Test page number removal
    test_page_number_removal()

    # Test chapter detection with cleanup
    test_chapter_detection_with_cleanup()

    # Test with real PDF
    print("\n" + "=" * 60)
    print("Real PDF Testing")
    print("=" * 60)
    print("\nTo test with your own PDFs:")
    print("1. Edit this script and add your PDF path to pdf_files list")
    print("2. Run: python test_chapter_detection.py\n")

    pdf_files = [
        # Add your PDF files here
        # "/path/to/your/book.pdf",
    ]

    for pdf_file in pdf_files:
        test_with_real_pdf(pdf_file)
        print()


if __name__ == "__main__":
    main()
