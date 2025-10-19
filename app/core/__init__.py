"""
Core package initializer.
We don’t auto-import submodules here to avoid circular imports.
Always import explicitly in your code:
    from app.core import character_detection
    from app.core import spacy_utils
    from app.core import turn_taking
    from app.core import workers
"""

__all__ = [
    "character_detection",
    "spacy_utils",
    "turn_taking",
    "workers",
]
