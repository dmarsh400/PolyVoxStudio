#!/usr/bin/env python3
"""
Test to diagnose the issue with your specific PDF.
"""

from app.core.chapter_chunker import detect_chapters, _remove_page_artifacts

# Simulate text like what you're getting from the PDF
test_text = """Opening material here with some content that sets up the story.

Chapter 11 so they wouldn't have to pay all those death benefits they promised their employees.
The company had strict policies about this. More content continues...

Section mole hunt. They were taken to a warehouse unit in Beaverton for a lecture and hands-on
training. The security protocol was intense. More details about the warehouse training session...

Section who lived and worked in the film community, a mild-mannered and opaque man referred
by his colleagues. He had connections in Hollywood. More about this mysterious figure...

Chapter XXVIII. – The Butcher's Bill
The final reckoning came as a surprise. The accounts were settled. Justice prevailed.
"""

print("=" * 70)
print("DIAGNOSING YOUR PDF ISSUE")
print("=" * 70)

print("\nORIGINAL TEXT:")
print("-" * 70)
print(test_text[:400])

# Remove page artifacts
cleaned = _remove_page_artifacts(test_text, [])

print("\n\nAFTER CLEANUP:")
print("-" * 70)
print(cleaned[:400])

# Detect chapters
chapters = detect_chapters(cleaned, min_chapter_length=50)

print("\n\nDETECTED CHAPTERS:")
print("-" * 70)
for i, ch in enumerate(chapters, 1):
    print(f"{i}. Title: {ch['title']:<50} ({len(ch['text']):>6} chars)")

print("\n" + "=" * 70)

# Detailed analysis
print("\nANALYSIS:")
print("-" * 70)

if len(chapters) > 2:
    problem_chapters = [
        'Chapter 11 so they wouldn\'t have to pay all those death benefits they promised their employees.',
        'Section mole hunt. They were taken to a warehouse unit in Beaverton for a lecture and hands-on',
        'Section who lived and worked in the film community, a mild-mannered and opaque man referred'
    ]

    found_problems = False
    for prob in problem_chapters:
        for ch in chapters:
            if prob in ch['title']:
                print(f"❌ PROBLEM FOUND: Long title detected")
                print(f"   Title: {ch['title'][:80]}...")
                found_problems = True
                break

    if not found_problems:
        print("✓ Good! Long chapter titles are NOT being detected")
        print("✓ Chapter titles are kept short and clean")
else:
    print("✓ Detection working - chapters properly separated")

print("\n" + "=" * 70)
