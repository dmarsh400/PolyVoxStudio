"""Infer a speaker's emotion for a quote from the narration tag around it ("screamed Alice")."""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

EMOTIONS = ("angry", "fearful", "happy", "sad", "surprised", "disgusted")

# (regex, emotion, weight); weight > 1 marks stronger, more specific cues.
_CUES: List[Tuple[str, str, float]] = [
    (r"\b(?:laugh(?:ed|ing)?|chuckl(?:ed|ing)|smil(?:ed|ing)) (?:bitterly|grimly|coldly|humorlessly|darkly)\b", "angry", 2.0),
    (r"\b(?:shout(?:ed|ing)?|yell(?:ed|ing)?|snapp(?:ed|ing)|snarl(?:ed|ing)|bark(?:ed|ing)|roar(?:ed|ing)|growl(?:ed|ing)|bellow(?:ed|ing)|hiss(?:ed|ing)|thunder(?:ed|ing)|fum(?:ed|ing)|rag(?:ed|ing)|curs(?:ed|ing)|seeth(?:ed|ing))\b", "angry", 1.0),
    (r"\b(?:furious(?:ly)?|angry|angrily|irate|livid|enraged|harshly|through (?:his|her|their) (?:clenched |gritted )?teeth|in (?:anger|rage|fury))\b", "angry", 1.2),
    (r"\b(?:scream(?:ed|ing)?|shriek(?:ed|ing)?|whimper(?:ed|ing)?|stammer(?:ed|ing)?|stutter(?:ed|ing)?|quaver(?:ed|ing)?|trembl(?:ed|ing)|panick(?:ed|ing)|cried out)\b", "fearful", 1.0),
    (r"\b(?:fearful(?:ly)?|terrified|frightened|nervous(?:ly)?|anxious(?:ly)?|in (?:fear|terror|horror|panic)|voice shaking|shakily)\b", "fearful", 1.2),
    (r"\b(?:laugh(?:ed|ing)?|chuckl(?:ed|ing)|giggl(?:ed|ing)|grinn(?:ed|ing)|beam(?:ed|ing)|cheer(?:ed|ing)|chirp(?:ed|ing)|quipp(?:ed|ing)|jok(?:ed|ing)|snicker(?:ed|ing))\b", "happy", 1.0),
    (r"\b(?:cheerful(?:ly)?|happ(?:y|ily)|bright(?:ly)?|excited(?:ly)?|gleeful(?:ly)?|joyful(?:ly)?|delighted(?:ly)?|with a (?:smile|grin))\b", "happy", 1.2),
    (r"\b(?:sobb(?:ed|ing)|wept|weep(?:ing)?|sigh(?:ed|ing)|mourn(?:ed|ing)|moan(?:ed|ing)|groan(?:ed|ing)|chok(?:ed|ing)|sniffl(?:ed|ing))\b", "sad", 1.0),
    (r"\b(?:sad(?:ly)?|mournful(?:ly)?|miserabl[ey]|tearful(?:ly)?|heavily|despair(?:ing(?:ly)?)?|in (?:grief|sorrow|despair)|in a leaden voice|forlorn(?:ly)?|dejected(?:ly)?)\b", "sad", 1.2),
    (r"\b(?:exclaim(?:ed|ing)?|gasp(?:ed|ing)?|marvel(?:ed|ing)|burst out)\b", "surprised", 1.0),
    (r"\b(?:in (?:surprise|shock|disbelief|amazement|astonishment)|incredulous(?:ly)?|astonished|stunned|startled|amazed|taken aback)\b", "surprised", 1.3),
    (r"\b(?:sneer(?:ed|ing)|scoff(?:ed|ing)|jeer(?:ed|ing)|mock(?:ed|ing)|spat|spit(?:ting)?|taunt(?:ed|ing))\b", "disgusted", 1.0),
    (r"\b(?:disgust(?:ed|edly)?|in disgust|contemptuous(?:ly)?|with contempt|disdainful(?:ly)?|scornful(?:ly)?|revuls(?:ion|ed))\b", "disgusted", 1.3),
]
_COMPILED = [(re.compile(p, re.IGNORECASE), emo, w) for p, emo, w in _CUES]

_INTENSIFIERS = re.compile(
    r"\b(?:furious(?:ly)?|violent(?:ly)?|hysterical(?:ly)?|wild(?:ly)?|loud(?:ly)?|desperate(?:ly)?|bitter(?:ly)?|"
    r"vicious(?:ly)?|frantic(?:ally)?|at the top of (?:his|her|their) lungs|very|bellow(?:ed)?|scream(?:ed)?|"
    r"shriek(?:ed)?|roar(?:ed)?)\b",
    re.IGNORECASE,
)
_SOFTENERS = re.compile(
    r"\b(?:soft(?:ly)?|quiet(?:ly)?|slight(?:ly)?|wry(?:ly)?|faint(?:ly)?|mild(?:ly)?|gentl[ey]|weak(?:ly)?|"
    r"almost|barely|a little|a bit)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_MAX_TAG_WORDS = 22


def _first_sentence(text: str) -> str:
    parts = _SENTENCE_SPLIT.split((text or "").strip(), maxsplit=1)
    return parts[0] if parts else ""


def _last_sentence(text: str) -> str:
    parts = _SENTENCE_SPLIT.split((text or "").strip())
    return parts[-1] if parts else ""


def _score(text: str) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for pattern, emotion, weight in _COMPILED:
        if pattern.search(text):
            scores[emotion] = scores.get(emotion, 0.0) + weight
    return scores


def detect_emotion(
    prev_narration: Optional[str],
    next_narration: Optional[str],
) -> Tuple[Optional[str], float]:
    """Return (emotion, intensity) from the speech tag adjacent to a quote, or (None, 0.0).

    Intensity is a multiplier around 1.0 (soft cues < 1, emphatic cues > 1).
    """
    tags: List[str] = []
    # A tag after the quote ("...," screamed Alice) is the usual form.
    after = _first_sentence(next_narration or "")
    if after and len(after.split()) <= _MAX_TAG_WORDS:
        tags.append(after)
    # A lead-in ending with a comma or colon ("Alice screamed, ") also belongs to this quote.
    before = _last_sentence(prev_narration or "")
    if before and before.rstrip().endswith((",", ":")) and len(before.split()) <= _MAX_TAG_WORDS:
        tags.append(before)

    total: Dict[str, float] = {}
    for tag in tags:
        for emotion, value in _score(tag).items():
            total[emotion] = total.get(emotion, 0.0) + value
    if not total:
        return None, 0.0

    emotion = max(total, key=total.get)
    intensity = 1.0
    joined = " ".join(tags)
    if _INTENSIFIERS.search(joined):
        intensity = 1.4
    if _SOFTENERS.search(joined):
        intensity = 0.65 if intensity == 1.0 else 1.0
    return emotion, intensity


def annotate_lines(lines: List[Dict[str, object]]) -> List[Tuple[Optional[str], float]]:
    """Per-line (emotion, intensity) for an ordered list of rows; narrator rows get (None, 0.0)."""
    result: List[Tuple[Optional[str], float]] = []
    for i, line in enumerate(lines):
        if not line.get("is_quote"):
            result.append((None, 0.0))
            continue
        prev = lines[i - 1] if i > 0 else None
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        prev_text = str(prev.get("text") or "") if prev and not prev.get("is_quote") else None
        next_text = str(nxt.get("text") or "") if nxt and not nxt.get("is_quote") else None
        result.append(detect_emotion(prev_text, next_text))
    return result
