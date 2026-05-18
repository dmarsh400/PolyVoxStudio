# PolyVox Studio v2.8

Release date: 2026-05-18

## Highlights

- **IMPROVED: Character detection accuracy — significantly reduced misattribution in first-person and dialogue-heavy chapters.**
- **IMPROVED: Main-character inference now uses address-based scoring to correctly identify the POV protagonist across chapters.**
- **FIXED: Brand/object names (e.g. "Smith & Wesson") no longer leak into speaker attribution as fake characters.**
- **IMPROVED: EPUB chapter detection now correctly splits chapters within parts instead of treating parts as the top-level unit.**

---

## Detailed Changes

### Character Detection (`app/core/character_detection.py`)

**New: Address-based scoring for main-character inference**

The `_infer_main_character()` function now tracks how often each character is *addressed by name* inside dialogue lines, in addition to the existing narration-mention and quote-count signals. Being directly addressed in dialogue ("You're a lucky man, Kovacs.") is a very strong signal that a character is the protagonist. This new `addressed` score is weighted at 6× and an additional 2× for first-person books, which reliably lifts the real POV character above secondary characters in the scoring.

Before this change, the prologue of *Altered Carbon* scored Sarah above Takeshi Kovacs because Sarah had more raw narration mentions. After this change, Chapter One scores Takeshi Kovacs at 118.5 vs Warden Sullivan at 50.0.

**Improved: Book-level main-character aggregation in GUI**

The `_resolve_main_character_override()` method in the GUI now sums the actual candidate scores from each chapter instead of summing the per-chapter confidence values. This means a character who narrowly wins one chapter but is clearly dominant in another now wins at the book level.

**Tuned: Scoring weights**

| Signal | Old weight | New weight |
|---|---|---|
| Narration mentions | 5.0 (+ 2.0 fp) | 4.0 (+ 1.5 fp) |
| Quote count | 2.0 | 1.5 |
| Address mentions | — | 6.0 (+ 2.0 fp) |
| Mention count (unknown ratio) | 0.5× | 0.25× |

---

### Character Attribution UI (`app/ui/characters_tab.py`)

**Fixed: "Smith & Wesson" → "Wesson" false speaker**

The explicit-character-from-context matcher now skips any name match where an ampersand (`&`) appears immediately to the left of the matched name in the surrounding text. This suppresses brand names like `Smith & Wesson` and `Heckler & Koch` from being promoted as real character speakers.

**Improved: Book-level main-character override aggregation**

`_resolve_main_character_override()` now sums raw candidate scores (from all chapter-level inferences) instead of chapter-level confidence floats, giving a more representative book-wide ranking when presenting the override dropdown to the user.

---

### EPUB Chapter Detection (`app/core/chapter_chunker.py`)

**Fixed: Chapters nested inside Parts are now detected correctly**

Previously, EPUB files that organised content as `PART I → Chapter 1, Chapter 2 …` were splitting only on the Part markers, producing very large, undivided segments. The chapter chunker now walks the spine in order and detects chapter-level headings within parts, falling back to size-based chunking only when no chapter markers are found. Word-number labels ("Chapter One", "Chapter Two", …) are also recognised.

---

## Migration / Cache Notes

- The BookNLP cache key is unchanged (`v2`). Existing caches remain valid.
- No changes to the voices or synthesis pipeline.
- No database or settings file migrations required.
