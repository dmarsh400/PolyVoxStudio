from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.core.english_booknlp import EnglishBookNLP

# -----------------------------------------------------------------------------
# Constants & configuration
# -----------------------------------------------------------------------------

BOOKNLP_PIPELINE = "entity,quote,coref"
BOOKNLP_MODEL_DEFAULT = "english"
CACHE_ROOT = Path(__file__).resolve().parents[2] / ".polyvox_tmp" / "booknlp_cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
CACHE_FORMAT_VERSION = "v2"
SPEAKER_CONFIDENCE_MIN = 0.47


_BOOK_ADAPTIVE_PRIORS: Dict[str, Counter] = defaultdict(Counter)


def clear_booknlp_cache() -> int:
    """Remove cached BookNLP artifacts and recreate the cache root directory."""
    removed = 0
    if CACHE_ROOT.exists():
        for child in CACHE_ROOT.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed += 1
            except Exception:
                continue
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return removed

QUOTE_TOGGLE_CHARS = {"\"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""}
QUOTE_TOGGLE_CHARS.update({"\"", "", "", "", "", "", ""})  # defensive duplicates
QUOTE_TOGGLE_CHARS.update({"\"", "", ""})
QUOTE_TOGGLE_CHARS.update({"\"", "", "", "", ""})
QUOTE_TOGGLE_CHARS = {"\"", "", "", "", "", "", "", "", "", "", ""}
QUOTE_TOGGLE_CHARS.update({"\"", "", ""})
QUOTE_TOGGLE_CHARS = {"\"", "", "", "", ""}
QUOTE_TOGGLE_CHARS.update({"\"", "", ""})
QUOTE_TOGGLE_CHARS = {"\"", "", "", "", ""}
QUOTE_TOGGLE_CHARS.update({"\"", "", "", "", ""})
QUOTE_TOGGLE_CHARS = {"\"", "", "", "", ""}
QUOTE_TOGGLE_CHARS.update({"\"", "", ""})
QUOTE_TOGGLE_CHARS = {"\"", "", "", "", ""}
QUOTE_TOGGLE_CHARS.update({"\"", "", "", "", ""})
QUOTE_TOGGLE_CHARS = {"\"", "", "", "", ""}

# Normal opening/closing curly quotes
QUOTE_TOGGLE_CHARS.update({"", ""})
QUOTE_TOGGLE_CHARS.update({"\"", "", "", "", ""})
QUOTE_TOGGLE_CHARS = {"\"", "", "", "", ""}

# Human titles to strip from the front of names when normalizing
TITLE_PREFIXES = {
    "mr",
    "mrs",
    "ms",
    "miss",
    "dr",
    "sir",
    "madam",
    "madame",
    "lady",
    "lord",
    "capt",
    "captain",
    "col",
    "colonel",
    "gen",
    "general",
    "lt",
    "lieutenant",
    "sgt",
    "sergeant",
    "major",
    "commandant",
    "judge",
    "chief",
    "agent",
    "officer",
    "prof",
    "professor",
    "president",
    "senator",
    "governor",
    "mayor",
    "queen",
    "king",
    "prince",
    "princess",
    "duke",
    "duchess",
    "brother",
    "sister",
    "father",
    "mother",
    "pastor",
    "reverend",
}

STOP_TOKENS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "for",
    "of",
    "to",
    "from",
    "with",
    "without",
    "about",
    "above",
    "below",
    "over",
    "under",
    "into",
    "onto",
    "as",
    "is",
    "am",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "done",
    "i",
    "me",
    "my",
    "mine",
    "myself",
    "we",
    "us",
    "our",
    "ours",
    "ourselves",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "this",
    "that",
    "these",
    "those",
    "here",
    "there",
    "who",
    "whom",
    "whose",
    "which",
    "what",
    "whatever",
    "whichever",
    "anyone",
    "someone",
    "everyone",
    "noone",
    "none",
    "each",
    "either",
    "neither",
    "both",
    "few",
    "many",
    "several",
    "most",
    "much",
    "more",
    "some",
    "thou",
    "thee",
    "thy",
    "thine",
    "ye",
    "god",
}

OPEN_QUOTE_CHARS = {"\"", "\u201c"}
CLOSE_QUOTE_CHARS = {"\"", "\u201d"}

SPEECH_VERBS = (
    "said",
    "asked",
    "replied",
    "repeated",
    "conceded",
    "told",
    "called",
    "shouted",
    "screamed",
    "cried",
    "muttered",
    "whispered",
    "responded",
    "added",
    "continued",
    "insisted",
    "retorted",
    "remarked",
    "snorted",
    "agreed",
    "yelled",
    "answered",
    "announced",
    "protested",
    "suggested",
    "explained",
    "murmured",
    "offered",
    "interjected",
    "prompted",
    "demanded",
    "called out",
    "spoke",
    "spoke up",
    "gestured",
    "pressed",
    "warned",
    "urged",
    "laughed",
    "chuckled",
    "giggled",
    "sighed",
    "groaned",
    "moaned",
    "gasped",
    "hissed",
    "snarled",
    "barked",
    "bellowed",
    "roared",
    "mumbled",
    "stammered",
    "stuttered",
    "drawled",
    "purred",
    "cooed",
    "simpered",
    "sneered",
    "scoffed",
    "jeered",
    "taunted",
    "mocked",
    "teased",
    "joked",
    "quipped",
    "bantered",
    "chattered",
    "prattled",
    "rambled",
    "lectured",
    "preached",
    "complained",
    "sermonized",
    "declaimed",
    "recited",
    "intoned",
    "chanted",
    "sang",
    "hummed",
    "whistled",
    "grumbled",
    "rumbled",
    "growled",
    "snapped",
    "huffed",
    "puffed",
    "panted",
    "wheezed",
    "rasped",
    "croaked",
    "squawked",
    "chirped",
    "trilled",
    "warbled",
    "breathed",
    "spat",
    "sputtered",
    "spluttered",
    "faltered",
    "hesitated",
    "paused",
    "stumbled",
    "tripped",
    "fumbled",
    "slurred",
    "lisped",
    "lilted",
    "crooned",
    "smirked",
    "grinned",
    "smiled",
    "beamed",
    "glowed",
    "radiated",
    "exuded",
    "oozed",
    "dripped",
    "sarcasmed",
    "broke in",
    "butted in",
    "called back",
    "chimed in",
    "chipped in",
    "cried out",
    "cut in",
    "jumped in",
    "piped up",
    "pitched in",
    "pointed out",
    "spoke out",
    "weighed in",
    "went on",
    "yelled back",
    "burst out",
    "blurted out",
    "snapped back",
    "retorted back",
    "replied back",
    "answered back",
    "responded back",
    "continued on",
)

NAME_PATTERN = r"[A-Z][A-Za-z\.'\-]*(?:\s+[A-Z][A-Za-z\.'\-]*){0,2}"
NARRATION_CUE_NAME_PATTERN = rf"(?:(?i:the|a|an)\s+[A-Za-z][A-Za-z'\-]*|{NAME_PATTERN})"
NARRATION_CUE_RELATIONSHIP_PREFIX = r"(?:(?i:his|her|their|my|our|your)\s+(?i:friend|buddy|partner|brother|sister|husband|wife|son|daughter|father|mother|cousin)\s+)?"

# -----------------------------------------------------------------------------
# Helper data structures
# -----------------------------------------------------------------------------


def _safe_slug(value: Optional[str]) -> str:
    if not value:
        return "chapter"
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "chapter"


def _hash_text(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def _clean_surface(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"[\"\u201c\u201d\u2018\u2019]", "", text)
    text = text.strip()
    return text


def _normalize_whitespace(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _has_meaningful_text(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[A-Za-z0-9]", text))


def _fix_contractions(text: str) -> str:
    # Merge split contractions like "don 't" or "don ’t" -> "don't"
    text = re.sub(r"(\w)\s+['\u2019]\s+(\w)", r"\1'\2", text)
    return text


def _split_quote_segments(text: str) -> List[Dict[str, str]]:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return []

    pieces: List[Dict[str, str]] = []
    buffer: List[str] = []
    in_quote = False

    def _flush_buffer(kind: str):
        if not buffer:
            return
        chunk = "".join(buffer).strip()
        buffer.clear()
        if not _has_meaningful_text(chunk):
            return
        if kind == "narration":
            chunk = chunk.strip('"“”')
            if not _has_meaningful_text(chunk):
                return
        chunk = _fix_contractions(chunk)
        pieces.append({"type": kind, "text": chunk})

    for ch in normalized:
        if ch in OPEN_QUOTE_CHARS and not in_quote:
            _flush_buffer("narration")
            in_quote = True
            buffer.append(ch)
            continue
        if ch in CLOSE_QUOTE_CHARS and in_quote:
            buffer.append(ch)
            _flush_buffer("quote")
            in_quote = False
            continue
        buffer.append(ch)

    if buffer:
        _flush_buffer("quote" if in_quote else "narration")

    return pieces


def is_first_person_narration(text: str) -> bool:
    """Detect first-person POV from narration only, not first-person dialogue."""
    pieces = _split_quote_segments(text or "")
    narration = " ".join(piece["text"] for piece in pieces if piece.get("type") == "narration").lower()
    first_person_hits = len(re.findall(r"\b(i|me|my|mine|myself|i'm|i've|i'd|i'll)\b", narration))
    third_person_hits = len(re.findall(r"\b(he|she|they|him|her|them|his|hers|their)\b", narration))
    return first_person_hits >= 3 and first_person_hits >= (third_person_hits * 0.12)


def _resolve_display_from_alias(
    name: str,
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> Optional[str]:
    alias = _normalize_alias(name)
    if not alias:
        return None
    cid = alias_to_id.get(alias)
    if cid is None:
        return None
    cid_str = str(cid)
    display = id_to_display.get(cid_str)
    if display:
        return display
    meta = characters.get(cid_str)
    if not meta:
        return None
    canonical = meta.get("canonical_name") or meta.get("normalized_name")
    if canonical:
        return _smart_capitalize(str(canonical))
    return None


def _resolve_narration_name_candidate(
    candidate: str,
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> Optional[str]:
    speaker = _resolve_display_from_alias(candidate, alias_to_id, id_to_display, characters)
    if speaker:
        return speaker

    without_article = re.sub(r"^(?:the|a|an)\s+", "", candidate.strip(), flags=re.IGNORECASE)
    if without_article != candidate.strip():
        speaker = _resolve_display_from_alias(without_article, alias_to_id, id_to_display, characters)
    if speaker:
        return speaker

    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*", without_article)
    for end in range(len(tokens) - 1, 0, -1):
        speaker = _resolve_display_from_alias(" ".join(tokens[:end]), alias_to_id, id_to_display, characters)
        if speaker:
            return speaker
    return _fallback_speaker_label(candidate)


def _extract_speaker_hints(
    text: str,
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> Dict[str, List[str]]:
    if not text:
        return {"prev": [], "next": []}

    cleaned = _normalize_whitespace(re.sub(r"[“”\"]", "", text))
    if not cleaned:
        return {"prev": [], "next": []}

    cleaned = cleaned.replace("Mr.", "Mr").replace("Mrs.", "Mrs").replace("Dr.", "Dr")

    prev_hints: List[str] = []
    next_hints: List[str] = []

    for verb in SPEECH_VERBS:
        verb_pattern = r"\s+".join(re.escape(token) for token in verb.split())
        verb_regex = rf"(?i:\b{verb_pattern}\b)"

        pattern_verb_first = re.compile(
            rf"{verb_regex}(?:\s+|\s*,\s*){NARRATION_CUE_RELATIONSHIP_PREFIX}(?P<name>{NARRATION_CUE_NAME_PATTERN})(?=\b|[^A-Za-z])"
        )
        for match in pattern_verb_first.finditer(cleaned):
            candidate = match.group("name").strip()
            speaker = _resolve_narration_name_candidate(candidate, alias_to_id, id_to_display, characters)
            if speaker and speaker not in prev_hints:
                prev_hints.append(speaker)

        pattern_name_first = re.compile(
            rf"(?P<name>{NARRATION_CUE_NAME_PATTERN})(?:\s*,)?\s+{verb_regex}"
        )
        for match in pattern_name_first.finditer(cleaned):
            candidate = match.group("name").strip()
            speaker = _resolve_narration_name_candidate(candidate, alias_to_id, id_to_display, characters)
            if not speaker:
                continue
            trailing = cleaned[match.end():].lstrip()
            orientation = "prev"
            if trailing:
                first_token = trailing.split(maxsplit=1)[0]
                if trailing[0] in {",", "-", "—"} or first_token.endswith(","):
                    orientation = "next"
                elif first_token.lower() in {"that", "to", "with", "as", "while", "because"}:
                    orientation = "next"
            target = prev_hints if orientation == "prev" else next_hints
            if speaker not in target:
                target.append(speaker)

    return {"prev": prev_hints, "next": next_hints}


def _extract_speaker_from_text(
    text: str,
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> Optional[str]:
    hints = _extract_speaker_hints(text, alias_to_id, id_to_display, characters)
    if hints["prev"]:
        return hints["prev"][0]
    if hints["next"]:
        return hints["next"][0]
    return None


def _contextual_speaker(
    surrounding_texts: Iterable[str],
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> Optional[str]:
    for text in surrounding_texts:
        speaker = _extract_speaker_from_text(text, alias_to_id, id_to_display, characters)
        if speaker:
            return speaker

    # Fallback: if surrounding narration mentions exactly one known character name,
    # use that as the likely speaker for nearby unresolved quotes.
    mention_scores: Dict[str, int] = {}
    for text in surrounding_texts:
        if not text:
            continue
        haystack = _normalize_whitespace(text).lower()
        if not haystack:
            continue

        for cid, display in id_to_display.items():
            if not display or display in {"Narrator", "Unknown"}:
                continue
            variants = {display}
            meta = characters.get(str(cid)) or characters.get(cid)
            if isinstance(meta, dict):
                canonical = meta.get("canonical_name") or meta.get("normalized_name")
                if canonical:
                    variants.add(str(canonical))

            for variant in variants:
                candidate = _normalize_whitespace(str(variant)).strip()
                if not candidate:
                    continue
                if re.search(rf"\b{re.escape(candidate.lower())}\b", haystack):
                    mention_scores[display] = mention_scores.get(display, 0) + len(candidate.split())

    if len(mention_scores) == 1:
        return next(iter(mention_scores.keys()))
    if mention_scores:
        ranked = sorted(mention_scores.items(), key=lambda kv: kv[1], reverse=True)
        if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
            return ranked[0][0]
    return None


ROLE_LABELS = {
    "doctor": "Doctor",
    "dr": "Doctor",
    "physician": "Doctor",
    "nurse": "Nurse",
    "warden": "Warden",
    "chief": "Chief",
    "commander": "Commander",
    "captain": "Captain",
    "lieutenant": "Lieutenant",
    "sergeant": "Sergeant",
    "officer": "Officer",
    "deputy": "Deputy",
    "detective": "Detective",
    "inspector": "Inspector",
    "constable": "Constable",
    "agent": "Agent",
    "guard": "Guard",
    "jailer": "Guard",
    "clerk": "Clerk",
    "receptionist": "Receptionist",
    "attendant": "Attendant",
    "driver": "Driver",
    "butler": "Butler",
    "maid": "Maid",
    "professor": "Professor",
    "teacher": "Teacher",
    "student": "Student",
    "mother": "Mother",
    "father": "Father",
    "sister": "Sister",
    "brother": "Brother",
    "king": "King",
    "queen": "Queen",
    "prince": "Prince",
    "princess": "Princess",
    "duke": "Duke",
    "duchess": "Duchess",
    "lord": "Lord",
    "lady": "Lady",
    "mr": "Mister",
    "mrs": "Missus",
    "ms": "Ms",
    "judge": "Judge",
    "lawyer": "Lawyer",
    "prosecutor": "Prosecutor",
    "barrister": "Lawyer",
    "witness": "Witness",
}

ROLE_SPEECH_HINTS = (
    "said",
    "asked",
    "replied",
    "answered",
    "told",
    "whispered",
    "murmured",
    "shouted",
    "yelled",
    "called",
    "announced",
    "continued",
    "added",
    "snapped",
    "growled",
    "hissed",
    "insisted",
    "warned",
    "ordered",
)


NON_PERSON_LABEL_TOKENS = {
    "world",
    "city",
    "administration",
    "division",
    "department",
    "facility",
    "system",
    "race",
    "amanglic",
    "psychasec",
    "psychasec",
    "alcatraz",
    "hotel",
    "house",
    "resolution",
    "division",
    "carte",
    "blanche",
    "innenin",
    "hendrix",
    "envoy",
    "corps",
    "hq",
    "beachhead",
}

QUOTE_ONLY_GROUP_LABEL_TOKENS = {
    "agency", "agencies", "center", "county", "girls", "guys", "boys",
    "people", "children", "kids", "men", "women", "group", "organization",
    "organizations", "dispatcher",
}


def _is_valid_quote_speaker_label(label: Optional[str]) -> bool:
    if not label or not isinstance(label, str):
        return False
    cleaned = label.strip()
    if not cleaned or cleaned in {"Unknown", "Narrator"}:
        return False
    if cleaned.lower().startswith("the "):
        return False
    lowered = cleaned.lower()
    tokens = set(re.findall(r"[a-z]+", lowered))
    if tokens & NON_PERSON_LABEL_TOKENS:
        return False
    if cleaned.isupper() and len(cleaned) <= 6:
        return False
    return True


def _sanitize_quote_speakers(rows: List[Dict[str, object]], allowed_speakers: Optional[Set[str]] = None) -> List[Dict[str, object]]:
    """Downgrade invalid quote speaker labels to Unknown."""
    if not rows:
        return rows
    for row in rows:
        if not row.get("is_quote"):
            continue
        speaker = row.get("speaker")
        if not isinstance(speaker, str):
            continue
        if speaker in {"Unknown", "Narrator"}:
            continue
        if not _is_valid_quote_speaker_label(speaker):
            row["speaker"] = "Unknown"
            continue
        if (
            allowed_speakers
            and speaker not in allowed_speakers
            and row.get("speaker_source") not in {"explicit_narration_cue", "booknlp_quote_mention", "arbitrated"}
        ):
            row["speaker"] = "Unknown"
    return rows


def _canonicalize_speaker_aliases(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Merge speaker label variants (title/surname forms) into canonical full names."""
    if not rows:
        return rows

    quote_counts: Counter = Counter()
    for row in rows:
        if not row.get("is_quote"):
            continue
        sp = row.get("speaker")
        if isinstance(sp, str) and _is_valid_quote_speaker_label(sp):
            quote_counts[sp] += 1

    if not quote_counts:
        return rows

    # Candidate canonical names: non-title multi-token person labels.
    canonical_candidates: List[str] = []
    for sp, _ in quote_counts.most_common():
        tokens = [t for t in re.findall(r"[A-Za-z][A-Za-z'\-]*", sp) if t]
        if len(tokens) < 2:
            continue
        if tokens[0].lower().rstrip(".") in TITLE_PREFIXES:
            continue
        canonical_candidates.append(sp)

    if not canonical_candidates:
        return rows

    mapping: Dict[str, str] = {}

    def _surname(name: str) -> Optional[str]:
        toks = [t for t in re.findall(r"[A-Za-z][A-Za-z'\-]*", name) if t]
        if not toks:
            return None
        return toks[-1].lower()

    by_surname: Dict[str, List[str]] = defaultdict(list)
    for cand in canonical_candidates:
        s = _surname(cand)
        if s:
            by_surname[s].append(cand)

    for sp in list(quote_counts.keys()):
        if sp in {"Unknown", "Narrator"}:
            continue
        tokens = [t for t in re.findall(r"[A-Za-z][A-Za-z'\-]*", sp) if t]
        if not tokens:
            continue

        first_is_title = tokens[0].lower().rstrip(".") in TITLE_PREFIXES
        s = tokens[-1].lower()
        if s not in by_surname:
            continue

        options = by_surname[s]
        if not options:
            continue

        # Only collapse strong variants:
        # - title+surname forms (e.g., Lieutenant Ortega)
        # - single-token surname aliases where there is an unambiguous full name.
        is_surname_only = len(tokens) == 1
        if not (first_is_title or is_surname_only):
            continue

        if len(options) == 1:
            mapping[sp] = options[0]
            continue

        # If multiple full names share surname, pick the most frequent quote speaker.
        best = sorted(options, key=lambda n: quote_counts.get(n, 0), reverse=True)[0]
        if quote_counts.get(best, 0) >= 2:
            mapping[sp] = best

    if not mapping:
        return rows

    for row in rows:
        sp = row.get("speaker")
        if isinstance(sp, str) and sp in mapping:
            row["speaker"] = mapping[sp]

    return rows


def _has_role_speech_cue(text: str, role_key: str) -> bool:
    lowered = text.lower()
    role_pat = rf"\b(?:the\s+)?{re.escape(role_key)}\b"
    if not re.search(role_pat, lowered):
        return False
    verbs_pat = "|".join(re.escape(v) for v in ROLE_SPEECH_HINTS)
    if re.search(rf"{role_pat}[^.!?;]{{0,42}}\b(?:{verbs_pat})\b", lowered):
        return True
    if re.search(rf"\b(?:{verbs_pat})\b[^.!?;]{{0,42}}{role_pat}", lowered):
        return True
    return False


def _chapter_number_from_title(title: Optional[str]) -> Optional[int]:
    if not title:
        return None
    lowered = title.lower()
    m = re.search(r"\bchapter\s+([0-9]+)\b", lowered)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    word_map = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
    }
    for word, num in word_map.items():
        if re.search(rf"\bchapter\s+{word}\b", lowered):
            return num
    return None


def _adaptive_book_key(title: Optional[str], explicit_key: Optional[str] = None) -> Optional[str]:
    if explicit_key:
        cleaned = re.sub(r"\W+", "_", str(explicit_key).lower()).strip("_")
        if cleaned:
            return cleaned
    if not title:
        return None
    base = title.lower()
    base = re.sub(r"\bchapter\b", "", base)
    base = re.sub(r"\b[0-9]+\b", "", base)
    base = re.sub(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", "", base)
    base = re.sub(r"\W+", "_", base).strip("_")
    if not base:
        return None
    return base


def _get_adaptive_priors(book_key: Optional[str], chapter_num: Optional[int]) -> Dict[str, float]:
    if not book_key:
        return {}
    if chapter_num is not None and chapter_num <= 2:
        return {}
    counter = _BOOK_ADAPTIVE_PRIORS.get(book_key)
    if not counter:
        return {}
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {k: float(v) / float(total) for k, v in counter.items() if k not in {"Unknown", "Narrator"}}


def _update_adaptive_priors(book_key: Optional[str], rows: List[Dict[str, object]]) -> None:
    if not book_key:
        return
    if not rows:
        return
    counter = _BOOK_ADAPTIVE_PRIORS[book_key]
    for row in rows:
        if not row.get("is_quote"):
            continue
        speaker = row.get("speaker")
        if not isinstance(speaker, str) or speaker in {"Unknown", "Narrator"}:
            continue
        conf = float(row.get("speaker_confidence", 0.0) or 0.0)
        if conf >= SPEAKER_CONFIDENCE_MIN:
            counter[speaker] += 1


def _weighted_context_speaker(
    weighted_texts: Iterable[Tuple[str, float]],
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> Optional[str]:
    """Use nearby narration cues with weights to infer a likely speaker."""
    scores, role_scores = _score_weighted_context(
        weighted_texts,
        alias_to_id,
        id_to_display,
        characters,
    )

    if scores:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        if len(ranked) == 1:
            return ranked[0][0]
        if ranked[0][1] >= 2.5 and ranked[0][1] >= (ranked[1][1] * 1.25):
            return ranked[0][0]

    if role_scores:
        role_ranked = sorted(role_scores.items(), key=lambda kv: kv[1], reverse=True)
        if len(role_ranked) == 1 or role_ranked[0][1] >= (role_ranked[1][1] * 1.2):
            if role_ranked[0][1] >= 1.4:
                return role_ranked[0][0]

    return None


def _score_weighted_context(
    weighted_texts: Iterable[Tuple[str, float]],
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return speaker/role score maps for nearby narration cues."""
    scores: Dict[str, float] = defaultdict(float)
    role_scores: Dict[str, float] = defaultdict(float)

    for text, weight in weighted_texts:
        if not text or weight <= 0:
            continue
        cleaned = _normalize_whitespace(str(text))
        if not cleaned:
            continue

        hints = _extract_speaker_hints(cleaned, alias_to_id, id_to_display, characters)
        for speaker in hints.get("prev", []):
            if _is_valid_quote_speaker_label(speaker):
                scores[speaker] += 5.0 * weight
        for speaker in hints.get("next", []):
            if _is_valid_quote_speaker_label(speaker):
                scores[speaker] += 3.5 * weight

        lowered = cleaned.lower()
        for cid, display in id_to_display.items():
            if not _is_valid_quote_speaker_label(display):
                continue
            variants = {display}
            meta = characters.get(str(cid)) or characters.get(cid)
            if isinstance(meta, dict):
                canonical = meta.get("canonical_name") or meta.get("normalized_name")
                if canonical:
                    variants.add(str(canonical))

            for variant in variants:
                cand = _normalize_whitespace(str(variant)).strip()
                if not cand:
                    continue
                if re.search(rf"\b{re.escape(cand.lower())}\b", lowered):
                    scores[display] += max(1.0, len(cand.split()) * 1.2) * weight

        for role_key, role_label in ROLE_LABELS.items():
            if _has_role_speech_cue(cleaned, role_key):
                role_scores[role_label] += 1.7 * weight

    return dict(scores), dict(role_scores)


def _diagnose_unknown_quotes(
    rows: List[Dict[str, object]],
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    """Explain why unresolved Unknown quote rows remained unresolved."""
    diagnostics: List[Dict[str, object]] = []

    if not rows:
        return diagnostics

    for idx, row in enumerate(rows):
        if row.get("speaker") != "Unknown" or not row.get("is_quote"):
            continue

        context_texts: List[Tuple[str, float]] = []

        # Immediate narration context is most informative.
        for offset, base_weight in ((-1, 1.0), (1, 1.0), (-2, 0.7), (2, 0.7)):
            j = idx + offset
            if j < 0 or j >= len(rows):
                continue
            near_row = rows[j]
            if near_row.get("is_quote"):
                continue
            near_text = str(near_row.get("text") or "")
            if near_text:
                context_texts.append((near_text, base_weight))

        # Back-history context often carries mention/hint cues.
        for back, prev_row in enumerate(reversed(rows[max(0, idx - 8):idx]), start=1):
            prev_text = str(prev_row.get("text") or "")
            if not prev_text:
                continue
            context_texts.append((prev_text, 0.75 / back))

        speaker_scores, role_scores = _score_weighted_context(
            context_texts,
            alias_to_id,
            id_to_display,
            characters,
        )

        reason = "no_cue"
        confidence = "low"

        ranked_speakers = sorted(speaker_scores.items(), key=lambda kv: kv[1], reverse=True)
        ranked_roles = sorted(role_scores.items(), key=lambda kv: kv[1], reverse=True)

        if ranked_speakers:
            if len(ranked_speakers) > 1 and ranked_speakers[0][1] < (ranked_speakers[1][1] * 1.25):
                reason = "conflicting_cues"
                confidence = "low"
            elif ranked_speakers[0][1] < 2.5:
                reason = "low_confidence"
                confidence = "low"
            else:
                reason = "filtered_by_assignment_logic"
                confidence = "medium"
        elif ranked_roles:
            if len(ranked_roles) > 1 and ranked_roles[0][1] < (ranked_roles[1][1] * 1.2):
                reason = "conflicting_cues"
            elif ranked_roles[0][1] < 1.4:
                reason = "low_confidence"
            else:
                reason = "filtered_by_assignment_logic"
                confidence = "medium"

        diagnostics.append({
            "line_index": idx,
            "text": row.get("text", ""),
            "speaker_confidence": row.get("speaker_confidence", 0.0),
            "reason": reason,
            "confidence": confidence,
            "top_speaker_candidates": [
                {"speaker": name, "score": round(float(score), 3)}
                for name, score in ranked_speakers[:3]
            ],
            "top_role_candidates": [
                {"speaker": name, "score": round(float(score), 3)}
                for name, score in ranked_roles[:2]
            ],
        })

    return diagnostics


def _looks_first_person_quote(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    # First-person signals for books where the POV character is also a speaker.
    return bool(re.search(r"\b(i|me|my|mine|myself|i'm|i've|i'd|i'll)\b", t))


def _map_narrator_quotes_to_pov(
    rows: List[Dict[str, object]],
    first_person_narration: bool,
    pov_speaker: Optional[str],
) -> List[Dict[str, object]]:
    """In first-person books, map quoted Narrator turns to the POV character."""
    if not rows or not first_person_narration or not _is_valid_quote_speaker_label(pov_speaker):
        return rows

    for row in rows:
        if not row.get("is_quote"):
            continue
        if row.get("speaker") == "Narrator":
            row["speaker"] = pov_speaker
    return rows


def _apply_first_person_narration_cues(
    rows: List[Dict[str, object]],
    first_person_narration: bool,
    pov_speaker: Optional[str],
) -> List[Dict[str, object]]:
    """Use nearby narration cues like 'I said/asked' to anchor quote speaker to POV."""
    if not rows or not first_person_narration or not _is_valid_quote_speaker_label(pov_speaker):
        return rows

    first_person_speech_re = re.compile(
        r"\b(i)\s+(said|asked|replied|answered|murmured|whispered|growled|snapped|told|suggested|added|continued|croaked|shouted|yelled|insisted|warned)\b",
        re.IGNORECASE,
    )

    for idx, row in enumerate(rows):
        if row.get("is_quote"):
            continue
        text = str(row.get("text") or "")
        if not text or not first_person_speech_re.search(text):
            continue

        # Re-anchor the nearest preceding quote line when a direct first-person
        # narration cue appears immediately after dialogue.
        prev_quote_idx = None
        for j in range(idx - 1, -1, -1):
            if rows[j].get("is_quote"):
                prev_quote_idx = j
                break
            if idx - j > 2:
                break

        if prev_quote_idx is None:
            continue

        qrow = rows[prev_quote_idx]
        current = qrow.get("speaker")
        conf = float(qrow.get("speaker_confidence", 0.0) or 0.0)
        if current == pov_speaker:
            continue

        # Keep very high-confidence attributions; otherwise trust explicit
        # first-person narration anchor.
        if conf >= 0.9 and current not in {"Unknown", "Narrator"}:
            continue

        qrow["speaker"] = pov_speaker

    return rows


def _assign_speaker_to_previous_quote(rows: List[Dict[str, object]], speaker: Optional[str]) -> None:
    if not speaker or speaker in {"Narrator", "Unknown"}:
        return
    for row in reversed(rows):
        if not row.get("is_quote"):
            continue
        row["speaker"] = speaker
        return


_SCENE_BREAK_RE = re.compile(r"\*\s*\*\s*\*")
_CONTINUATION_TAG_RE = re.compile(r"\b(?:went on|continued|carried on|pressed on|added)\b", re.IGNORECASE)
_SPEECH_VERB_RE = re.compile(r"\b(?:" + "|".join(re.escape(v) for v in SPEECH_VERBS) + r")\b", re.IGNORECASE)
_TRAILING_QUOTE_CHARS = "\u201d\"'\u2019"

# BookNLP wins unless a structural cue (tag comma, continuation, action beat) favors someone else.
_BOOKNLP_DECISIVE_BONUS = 50.0
_BOOKNLP_CONTESTED_BONUS = 4.5
_NON_PARTICIPANT_PENALTY = 4.0
_PARTICIPANT_WINDOW = 10


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text or ""))


def _name_tokens(name: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", name or "")


def _quote_names_speaker(text: str, speaker: str) -> bool:
    """True when the quote refers to the speaker by name (people rarely name themselves)."""
    if not text or not speaker or _is_self_identification_quote(text, speaker):
        return False
    for token in _name_tokens(speaker):
        if not token[0].isupper() or token.lower() in ROLE_LABELS:
            continue
        if re.search(rf"\b{re.escape(token)}\b", text):
            return True
    return False


def _scene_ids(rows: List[Dict[str, object]]) -> List[int]:
    ids: List[int] = []
    scene = 0
    for row in rows:
        ids.append(scene)
        if not row.get("is_quote") and _SCENE_BREAK_RE.search(str(row.get("text") or "")):
            scene += 1
    return ids


def _scene_participants(rows: List[Dict[str, object]], scene_ids: List[int]) -> Dict[int, Set[str]]:
    """Per quote row: speakers confirmed by explicit narration tags nearby in the same scene."""
    quotes = [i for i, r in enumerate(rows) if r.get("is_quote")]
    result: Dict[int, Set[str]] = {}
    for pos, i in enumerate(quotes):
        names: Set[str] = set()
        for j in quotes[max(0, pos - _PARTICIPANT_WINDOW):pos + _PARTICIPANT_WINDOW + 1]:
            if j == i or scene_ids[j] != scene_ids[i]:
                continue
            other = rows[j]
            if other.get("speaker_source") == "explicit_narration_cue" and _is_valid_quote_speaker_label(other.get("speaker")):
                names.add(str(other["speaker"]))
        result[i] = names
    return result


def _previous_quote_context(
    rows: List[Dict[str, object]], idx: int, scene_ids: List[int]
) -> Tuple[Optional[int], str]:
    """Index of the closest earlier quote in the same scene plus the narration between."""
    narration: List[str] = []
    j = idx - 1
    while j >= 0 and not rows[j].get("is_quote"):
        narration.append(str(rows[j].get("text") or ""))
        j -= 1
    if j < 0 or scene_ids[j] != scene_ids[idx]:
        return None, ""
    return j, " ".join(reversed(narration)).strip()


def _beat_subject(narration: str, participants: Set[str], allow_speech: bool = False) -> Optional[str]:
    """Participant that opens the last narration sentence (an action beat, not a speech tag)."""
    if not narration or not participants:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", narration.strip())
    last = sentences[-1] if sentences else ""
    match = re.match(r"([A-Z][A-Za-z'\-]+)", last)
    if not match or (not allow_speech and _SPEECH_VERB_RE.search(last)):
        return None
    matches = [p for p in participants if match.group(1) in _name_tokens(p)]
    return matches[0] if len(matches) == 1 else None


def _following_tag_subject(rows: List[Dict[str, object]], idx: int, participants: Set[str]) -> Optional[str]:
    """Participant named in a short narration beat right after the quote (e.g. 'confirmed Hatfield.')."""
    if idx + 1 >= len(rows) or rows[idx + 1].get("is_quote") or not participants:
        return None
    first = re.split(r"(?<=[.!?])\s+", str(rows[idx + 1].get("text") or "").strip())[0]
    if not first or _word_count(first) > 10:
        return None
    matches = [
        p for p in participants
        if any(re.search(rf"\b{re.escape(tok)}\b", first) for tok in _name_tokens(p))
    ]
    return matches[0] if len(matches) == 1 else None


def _arbitrate_quote_speakers(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Reconcile BookNLP's quote speaker with local dialogue structure instead of overriding blindly."""
    if not rows:
        return rows

    scene_ids = _scene_ids(rows)
    participants = _scene_participants(rows, scene_ids)
    anchored: Set[int] = {
        i for i, r in enumerate(rows)
        if r.get("is_quote") and r.get("speaker_source") == "explicit_narration_cue"
    }

    for i, row in enumerate(rows):
        if not row.get("is_quote") or i in anchored:
            continue

        text = str(row.get("text") or "")
        parts = participants.get(i, set())
        gate = len(parts) >= 2
        current = row.get("speaker") if _is_valid_quote_speaker_label(row.get("speaker")) else None
        booknlp = row.get("booknlp_quote_speaker")
        booknlp = booknlp if _is_valid_quote_speaker_label(booknlp) else None
        if not booknlp and not current:
            continue

        scores: Dict[str, float] = {}
        for cand in row.get("speaker_candidates") or []:
            name = cand.get("speaker") if isinstance(cand, dict) else None
            if _is_valid_quote_speaker_label(name):
                scores[name] = max(0.0, float(cand.get("score", 0.0) or 0.0))
        for name in (booknlp, current):
            if name:
                scores.setdefault(name, 0.0)
        for name in parts:
            scores.setdefault(name, 0.5)

        excluded = {
            name for name in scores
            if (_looks_vocative_addressed_to_speaker(text, name) and not _is_self_identification_quote(text, name))
            or _quote_names_speaker(text, name)
        }

        bonus: Dict[str, float] = defaultdict(float)
        prev_idx, between = _previous_quote_context(rows, i, scene_ids)
        between_words = _word_count(between)
        continuation = bool(between) and between_words <= 20 and bool(_CONTINUATION_TAG_RE.search(between))
        beat = _beat_subject(between, parts, allow_speech=continuation)
        prev_anchored = prev_idx is not None and prev_idx in anchored
        prev_speaker = rows[prev_idx].get("speaker") if prev_idx is not None else None
        prev_text = str(rows[prev_idx].get("text") or "") if prev_idx is not None else ""
        prev_tail = prev_text.rstrip().rstrip(_TRAILING_QUOTE_CHARS)

        if continuation:
            target = beat or (prev_speaker if prev_anchored else None)
            if target:
                bonus[str(target)] += 8.0
        elif beat:
            bonus[beat] += 3.0

        # A narration beat right after the quote can name its speaker even without a speech verb.
        tag_after = _following_tag_subject(rows, i, parts)
        if tag_after:
            bonus[tag_after] += 4.0

        addressed = [
            p for p in parts
            if prev_anchored and p != prev_speaker and _looks_vocative_addressed_to_speaker(prev_text, p)
        ]
        for p in addressed:
            bonus[p] += 3.0
        if (
            prev_anchored and between and between_words <= 14 and not continuation and not addressed
            and prev_tail.endswith(",") and _word_count(prev_text) >= 2
        ):
            bonus[str(prev_speaker)] += 2.5

        # A short question tagged to X is answered by someone else, usually whoever X was addressing.
        if (
            prev_anchored and not continuation and prev_tail.endswith("?") and between_words <= 8
            and "?" not in text
            and (_word_count(text) <= 12 or _word_count(prev_text) >= 8)
        ):
            excluded.add(str(prev_speaker))
            for k in range(prev_idx - 1, -1, -1):
                other = rows[k]
                if scene_ids[k] != scene_ids[i]:
                    break
                if k in anchored and other.get("speaker") != prev_speaker:
                    bonus[str(other.get("speaker"))] += 2.5
                    break

        # Short interjection between two tags of the same speaker belongs to the other party.
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        if (
            prev_anchored and nxt is not None and nxt.get("is_quote") and (i + 1) in anchored
            and nxt.get("speaker") == prev_speaker and _word_count(text) <= 3
        ):
            excluded.add(str(prev_speaker))

        booknlp_ok = bool(booknlp) and booknlp not in excluded and not (gate and booknlp not in parts)
        competing = any(v >= 2.5 for n, v in bonus.items() if n != booknlp and n not in excluded)
        if booknlp and not booknlp_ok:
            excluded.add(booknlp)

        final: Dict[str, float] = {}
        for name, base in scores.items():
            if name in excluded:
                continue
            value = base + bonus.get(name, 0.0)
            if gate and name not in parts:
                value -= _NON_PARTICIPANT_PENALTY
            if booknlp_ok and name == booknlp:
                value += _BOOKNLP_CONTESTED_BONUS if competing else _BOOKNLP_DECISIVE_BONUS
            final[name] = value

        needs_review = booknlp is not None or (current in excluded) or (gate and current not in parts)
        if not needs_review or not final:
            continue

        best = max(final, key=lambda n: (final[n], n == current))
        if final[best] <= 0.0:
            best = "Unknown"

        row["speaker"] = best
        row["speaker_source"] = "booknlp_quote_mention" if best == booknlp else "arbitrated"
        if bonus.get(best, 0.0) >= 2.5:
            anchored.add(i)
    return rows


def _demote_inline_scare_quotes(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Turn quoted words embedded mid-sentence in narration (e.g. 'quaint') back into narration."""
    out: List[Dict[str, object]] = []
    merge_next = False
    for i, row in enumerate(rows):
        if merge_next and not row.get("is_quote"):
            out[-1]["text"] = f"{out[-1]['text']} {row.get('text', '')}".strip()
            merge_next = False
            continue
        merge_next = False
        if row.get("is_quote") and 0 < i < len(rows) - 1:
            prev, nxt = rows[i - 1], rows[i + 1]
            inner = re.sub(r"[\u201c\u201d\"]", "", str(row.get("text") or "")).strip()
            prev_text = str(prev.get("text") or "").rstrip()
            next_text = str(nxt.get("text") or "").lstrip()
            if (
                not prev.get("is_quote") and not nxt.get("is_quote")
                and 0 < _word_count(inner) <= 3
                and not re.search(r"[.!?,;:\u2014\u2026]", inner)
                and prev_text and not re.search(r"[.!?:\u2026\u201d\"]$", prev_text)
                and next_text[:1].islower()
            ):
                out[-1]["text"] = f"{out[-1]['text']} {row.get('text', '')}".strip()
                merge_next = True
                continue
        out.append(row)
    return out


def _demote_heading_quotes(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """A Title-Cased quote right after the chapter heading is a subtitle, not dialogue."""
    small = {"a", "an", "the", "of", "and", "in", "on", "to", "at", "for", "but", "or", "nor", "by", "with", "from", "as"}
    for i, row in enumerate(rows[:3]):
        if not row.get("is_quote"):
            continue
        if any(r.get("is_quote") for r in rows[:i]):
            break
        if sum(_word_count(str(r.get("text") or "")) for r in rows[:i]) > 6:
            break
        words = re.findall(r"[A-Za-z][A-Za-z'\u2019\-]*", str(row.get("text") or ""))
        significant = [w for w in words if w.lower() not in small]
        if 2 <= len(words) <= 14 and significant and sum(w[0].isupper() for w in significant) / len(significant) >= 0.8:
            rows[i] = {"speaker": "Narrator", "text": row.get("text", ""), "is_quote": False}
        break
    return rows


def _apply_explicit_previous_quote_cues(
    rows: List[Dict[str, object]],
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    """Reapply explicit narration tags after statistical attribution/smoothing."""
    if not rows:
        return rows

    known_names = set((id_to_display or {}).values())
    for narration_idx, narration in enumerate(rows):
        if narration.get("is_quote") or narration.get("speaker") != "Narrator":
            continue

        hints = _extract_speaker_hints(
            str(narration.get("text") or ""),
            alias_to_id,
            id_to_display,
            characters,
        )
        speakers = {
            speaker
            for speaker in hints["prev"]
            if speaker in known_names and _is_valid_quote_speaker_label(speaker)
        }
        if len(speakers) != 1:
            continue
        speaker = next(iter(speakers))

        skipped_narration = 0
        for previous_idx in range(narration_idx - 1, -1, -1):
            previous = rows[previous_idx]
            if previous.get("is_quote"):
                previous["speaker"] = speaker
                previous["speaker_confidence"] = 1.0
                previous["speaker_source"] = "explicit_narration_cue"
                break
            if previous.get("speaker") != "Narrator":
                break
            skipped_narration += 1
            if skipped_narration > 2:
                break

    return rows


def _fuse_speaker_evidence(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Calibrate final speaker confidence from BookNLP, local candidates, and cue agreement."""
    for row in rows or []:
        if not row.get("is_quote"):
            continue

        final_speaker = str(row.get("speaker") or "Unknown")
        booknlp_speaker = row.get("booknlp_quote_speaker")
        candidates = row.get("speaker_candidates") or []
        candidate_scores = {
            str(candidate.get("speaker")): max(0.0, float(candidate.get("score", 0.0) or 0.0))
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("speaker")
        }
        heuristic_speaker = next(iter(candidate_scores), None)
        heuristic_top_score = max(candidate_scores.values(), default=0.0)
        direct_score = candidate_scores.get(str(booknlp_speaker), 0.0) if booknlp_speaker else 0.0
        support = (direct_score / heuristic_top_score) if heuristic_top_score > 0 else 0.0
        source = row.get("speaker_source", "model")

        if source == "explicit_narration_cue":
            agrees = final_speaker == heuristic_speaker or final_speaker == booknlp_speaker
            confidence = 0.98 if agrees else 0.88
        elif source == "booknlp_quote_mention":
            agrees = final_speaker == heuristic_speaker
            confidence = 0.97 if agrees else round(0.60 + 0.30 * min(1.0, support), 3)
        elif source == "arbitrated":
            agrees = final_speaker == heuristic_speaker
            confidence = 0.3 if final_speaker == "Unknown" else (0.8 if agrees else 0.65)
        else:
            agrees = final_speaker == heuristic_speaker
            confidence = float(row.get("speaker_confidence", 0.0) or 0.0)
            if final_speaker not in {"Unknown", "Narrator"} and confidence < max(SPEAKER_CONFIDENCE_MIN + 0.05, 0.52):
                final_speaker = "Unknown"
                row["speaker"] = final_speaker
                row["speaker_source"] = "low_confidence_fusion"
                source = "low_confidence_fusion"

        row["speaker_confidence"] = round(confidence, 3)
        row["speaker_evidence"] = {
            "source": source,
            "booknlp_speaker": booknlp_speaker,
            "heuristic_top": heuristic_speaker,
            "booknlp_heuristic_agree": bool(booknlp_speaker and booknlp_speaker == heuristic_speaker),
            "final_agrees_with_heuristic": agrees,
            "booknlp_score_support_ratio": round(support, 3) if booknlp_speaker else None,
        }
        row.pop("booknlp_quote_speaker", None)
    return rows


def _apply_turn_taking_heuristic(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """
    Fill some short Unknown quote lines using conservative A/B alternation.

    Heuristic triggers only when:
    - the current row is an Unknown quote,
    - the quote is short (dialogue turn-like), and
    - surrounding quote speakers provide strong turn-taking evidence.
    """
    if not rows:
        return rows

    quote_indices = [i for i, r in enumerate(rows) if r.get("is_quote")]
    if not quote_indices:
        return rows

    def _quote_len_ok(text: str) -> bool:
        if not text:
            return False
        words = len(re.findall(r"[A-Za-z0-9']+", text))
        return words <= 18

    def _speaker_at_quote_pos(qpos: int) -> Optional[str]:
        if qpos < 0 or qpos >= len(quote_indices):
            return None
        speaker = rows[quote_indices[qpos]].get("speaker")
        if not isinstance(speaker, str):
            return None
        if speaker in {"Unknown", "Narrator"}:
            return None
        return speaker

    for qpos, row_idx in enumerate(quote_indices):
        row = rows[row_idx]
        speaker = row.get("speaker")
        if speaker != "Unknown" or not row.get("is_quote"):
            continue

        text = str(row.get("text") or "")
        if not _quote_len_ok(text):
            continue

        prev1 = _speaker_at_quote_pos(qpos - 1)
        prev2 = _speaker_at_quote_pos(qpos - 2)
        next1 = _speaker_at_quote_pos(qpos + 1)

        # Pattern: A, B, Unknown -> choose A (alternating turns)
        if prev1 and prev2 and prev1 != prev2:
            row["speaker"] = prev2
            continue

        # Pattern: A, Unknown, A with earlier B -> Unknown is likely B
        if prev1 and next1 and prev1 == next1 and prev2 and prev2 != prev1:
            row["speaker"] = prev2
            continue

    return rows


def _apply_dialogue_block_alternation(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """
    Resolve some short Unknown turns in long two-speaker dialogue blocks.

    This mirrors the conversational-pattern sieve style: in quote-heavy local
    windows with two dominant speakers, short Unknown lines are assigned by
    alternation only when neighboring evidence supports it.
    """
    if not rows:
        return rows

    quote_positions = [i for i, r in enumerate(rows) if r.get("is_quote")]
    if len(quote_positions) < 5:
        return rows

    def _is_short_turn(text: str) -> bool:
        if not text:
            return False
        words = len(re.findall(r"[A-Za-z0-9']+", text))
        return words <= 20

    blocks: List[Tuple[int, int]] = []
    block_start = 0
    for qpos in range(1, len(quote_positions)):
        prev_idx = quote_positions[qpos - 1]
        cur_idx = quote_positions[qpos]
        narration_rows = rows[prev_idx + 1:cur_idx]
        long_break = False
        if len(narration_rows) > 2:
            long_break = True
        for nrow in narration_rows:
            if nrow.get("is_quote"):
                continue
            ntext = str(nrow.get("text") or "")
            if len(ntext) > 220:
                long_break = True
                break
        if long_break:
            blocks.append((block_start, qpos - 1))
            block_start = qpos
    blocks.append((block_start, len(quote_positions) - 1))

    for bstart, bend in blocks:
        if (bend - bstart + 1) < 6:
            continue

        speakers_in_block: List[str] = []
        for qpos in range(bstart, bend + 1):
            sp = rows[quote_positions[qpos]].get("speaker")
            if isinstance(sp, str) and sp not in {"Unknown", "Narrator"} and _is_valid_quote_speaker_label(sp):
                speakers_in_block.append(sp)
        if len(speakers_in_block) < 4:
            continue

        counts = Counter(speakers_in_block)
        top_two = counts.most_common(2)
        if len(top_two) < 2:
            continue
        (sp_a, c_a), (sp_b, c_b) = top_two
        if c_a < 2 or c_b < 2:
            continue
        if (c_a + c_b) < int(0.72 * len(speakers_in_block)):
            continue

        pair = {sp_a, sp_b}
        for qpos in range(bstart, bend + 1):
            ridx = quote_positions[qpos]
            row = rows[ridx]
            if row.get("speaker") != "Unknown":
                continue

            text = str(row.get("text") or "")
            if not _is_short_turn(text):
                continue

            prev_sp: Optional[str] = None
            for back in range(qpos - 1, bstart - 1, -1):
                cand = rows[quote_positions[back]].get("speaker")
                if isinstance(cand, str) and cand in pair:
                    prev_sp = cand
                    break

            next_sp: Optional[str] = None
            for fwd in range(qpos + 1, bend + 1):
                cand = rows[quote_positions[fwd]].get("speaker")
                if isinstance(cand, str) and cand in pair:
                    next_sp = cand
                    break

            if prev_sp and next_sp and prev_sp == next_sp:
                row["speaker"] = sp_b if prev_sp == sp_a else sp_a
                continue

            if prev_sp and next_sp and prev_sp != next_sp:
                # Prefer keeping strict alternation with the nearest previous turn.
                row["speaker"] = sp_b if prev_sp == sp_a else sp_a
                continue

            if prev_sp and not next_sp:
                row["speaker"] = sp_b if prev_sp == sp_a else sp_a

    return rows


def _resolve_unknown_from_neighbor_narration(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Conservative pass: resolve Unknown quotes from immediate narration cues."""
    if not rows:
        return rows

    speech_pronoun_re = re.compile(r"\b(?P<pn>he|she)\s+(said|asked|replied|murmured|whispered|recited|managed)\b", re.IGNORECASE)

    def _nearest_prior_named_quote(start_idx: int) -> Optional[str]:
        for j in range(start_idx - 1, -1, -1):
            rowj = rows[j]
            if not rowj.get("is_quote"):
                continue
            sp = rowj.get("speaker")
            if isinstance(sp, str) and sp not in {"Unknown", "Narrator"}:
                return sp
        return None

    def _nearest_prior_surname(role: str, start_idx: int) -> Optional[str]:
        role_l = role.lower()
        for j in range(start_idx - 1, -1, -1):
            txt = str(rows[j].get("text") or "")
            if not txt:
                continue
            if role_l == "warden" and "sullivan" in txt.lower():
                return "Warden Sullivan"
            if role_l == "doctor" and "doctor" in txt.lower():
                return "Doctor"
        return None

    for i, row in enumerate(rows):
        if not row.get("is_quote") or row.get("speaker") != "Unknown":
            continue

        prev_txt = str(rows[i - 1].get("text") or "") if i - 1 >= 0 else ""
        next_txt = str(rows[i + 1].get("text") or "") if i + 1 < len(rows) else ""
        cue_text = f"{prev_txt} {next_txt}".strip().lower()
        if not cue_text:
            continue

        for role_key, role_label in ROLE_LABELS.items():
            if re.search(rf"\b(?:the\s+)?{re.escape(role_key)}\b", cue_text):
                specific = _nearest_prior_surname(role_key, i)
                row["speaker"] = specific or role_label
                break

        if row.get("speaker") != "Unknown":
            continue

        if speech_pronoun_re.search(cue_text):
            prior = _nearest_prior_named_quote(i)
            if prior:
                row["speaker"] = prior

    return rows


def _nearest_named_quote_speaker(rows: List[Dict[str, object]], start_idx: int, direction: int) -> Optional[str]:
    j = start_idx + direction
    while 0 <= j < len(rows):
        row = rows[j]
        if row.get("is_quote"):
            speaker = row.get("speaker")
            if isinstance(speaker, str) and speaker not in {"Unknown", "Narrator"}:
                return speaker
        j += direction
    return None


def _looks_vocative_addressed_to_speaker(text: str, speaker: str) -> bool:
    """Detect quotes that likely address a speaker by name (not spoken by them)."""
    if not text or not speaker:
        return False

    speaker_parts = [p for p in re.split(r"\s+", speaker.strip()) if p]
    if not speaker_parts:
        return False

    last_name = re.escape(speaker_parts[-1])
    first_name = re.escape(speaker_parts[0])
    full_name = re.escape(" ".join(speaker_parts))

    t = text.strip()
    has_second_person = bool(re.search(r"\b(you|your|you're|you'll|you've)\b", t, flags=re.IGNORECASE))
    if not has_second_person:
        # Punctuation-delimited address such as "Why, Zack?" or "They were upstairs, Zack!".
        either = rf"(?:{first_name}|{last_name})"
        return any(
            re.search(pat, t, flags=re.IGNORECASE)
            for pat in (rf",\s*{either}\s*[!?,]", rf"^\W*{either}\s*[!?]")
        )

    # Common direct-address patterns: "..., Name" or "Name, ..."
    vocative_patterns = [
        rf",\s*{last_name}\b",
        rf"^\W*{last_name}\s*,",
        rf",\s*{first_name}\b",
        rf"^\W*{first_name}\s*,",
        rf",\s*{full_name}\b",
        rf"^\W*{full_name}\s*,",
    ]
    return any(re.search(pat, t, flags=re.IGNORECASE) for pat in vocative_patterns)


def _has_continuity_cue(text: str) -> bool:
    if not text:
        return False
    return bool(
        re.search(
            r"\b(continued|went on|kept talking|kept speaking|added|again|without pause|still speaking|he said again|she said again)\b",
            text.lower(),
        )
    )


def _is_self_identification_quote(text: str, speaker: str) -> bool:
    if not text or not speaker:
        return False
    tokens = [p for p in re.split(r"\s+", speaker.strip()) if p]
    if not tokens:
        return False
    first = re.escape(tokens[0])
    last = re.escape(tokens[-1])
    lowered = text.lower()
    return bool(
        re.search(rf"\b(my name is|i am|i'm|this is)\s+{first}(?:\s+{last})?\b", lowered)
    )


def _compute_quote_candidate_scores(
    rows: List[Dict[str, object]],
    idx: int,
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
    adaptive_priors: Dict[str, float],
    global_character_priors: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    row = rows[idx]
    text = str(row.get("text") or "")
    scores: Dict[str, float] = defaultdict(float)

    current = row.get("speaker")
    if isinstance(current, str) and current not in {"Unknown", "Narrator"}:
        scores[current] += 0.5

    # Local quote state window (last 2-3 quote speakers).
    quote_speakers_back: List[str] = []
    for j in range(idx - 1, -1, -1):
        prev = rows[j]
        if not prev.get("is_quote"):
            continue
        sp = prev.get("speaker")
        if isinstance(sp, str) and sp not in {"Unknown", "Narrator"}:
            quote_speakers_back.append(sp)
        if len(quote_speakers_back) >= 3:
            break

    continuity = _has_continuity_cue(
        f"{rows[idx-1].get('text','') if idx-1>=0 else ''} {rows[idx+1].get('text','') if idx+1 < len(rows) else ''}"
    )

    if quote_speakers_back:
        scores[quote_speakers_back[0]] += 0.7 if continuity else 0.25
    if len(quote_speakers_back) >= 2 and quote_speakers_back[0] != quote_speakers_back[1]:
        scores[quote_speakers_back[1]] += 0.65
    if len(quote_speakers_back) >= 3:
        scores[quote_speakers_back[2]] += 0.25

    # Narration context around the quote.
    weighted_contexts: List[Tuple[str, float]] = []
    for offset, weight in ((-1, 1.0), (1, 1.0), (-2, 0.7), (2, 0.7)):
        j = idx + offset
        if j < 0 or j >= len(rows):
            continue
        near = rows[j]
        if near.get("is_quote"):
            continue
        near_text = str(near.get("text") or "")
        if near_text:
            weighted_contexts.append((near_text, weight))
    for back, prev_row in enumerate(reversed(rows[max(0, idx - 8):idx]), start=1):
        prev_text = str(prev_row.get("text") or "")
        if prev_text:
            weighted_contexts.append((prev_text, 0.75 / back))

    sp_scores, role_scores = _score_weighted_context(weighted_contexts, alias_to_id, id_to_display, characters)
    for speaker, score in sp_scores.items():
        scores[speaker] += float(score) * 0.7
    for role_speaker, score in role_scores.items():
        scores[role_speaker] += float(score) * 0.45

    # Adaptive per-book priors (from earlier chapters/runs).
    for speaker, prior in (adaptive_priors or {}).items():
        if _is_valid_quote_speaker_label(speaker):
            scores[speaker] += 0.12 * float(prior)

    # Global priors from full-book cast weighting.
    for speaker, prior in (global_character_priors or {}).items():
        if _is_valid_quote_speaker_label(speaker):
            scores[speaker] += 0.22 * float(prior)

    # Addressee-aware penalty: if a line addresses "Name," then that name is less likely the speaker.
    for candidate in list(scores.keys()):
        if _looks_vocative_addressed_to_speaker(text, candidate):
            scores[candidate] -= 1.25

    # Penalize improbable immediate repetition unless narration indicates continuity.
    if len(quote_speakers_back) >= 2 and quote_speakers_back[0] != quote_speakers_back[1] and not continuity:
        repeat = quote_speakers_back[0]
        scores[repeat] -= 0.6

    # Anti-collapse: long same-speaker runs should require explicit continuity cues.
    same_run = 0
    run_speaker = quote_speakers_back[0] if quote_speakers_back else None
    for j in range(idx - 1, -1, -1):
        prev = rows[j]
        if not prev.get("is_quote"):
            continue
        if run_speaker and prev.get("speaker") == run_speaker:
            same_run += 1
        else:
            break
    if same_run >= 3 and quote_speakers_back and not continuity:
        scores[quote_speakers_back[0]] -= 0.6

    return dict(scores)


def _score_to_confidence(top_score: float, second_score: float) -> float:
    margin = top_score - second_score
    conf = 0.5 + (margin / (abs(top_score) + 2.0))
    if top_score < 1.2:
        conf *= 0.72
    return max(0.0, min(0.99, conf))


def _apply_quote_confidence_threshold(
    rows: List[Dict[str, object]],
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
    adaptive_priors: Dict[str, float],
    first_person_narration: bool,
    pov_speaker: Optional[str] = None,
    global_character_priors: Optional[Dict[str, float]] = None,
    allowed_speakers: Optional[Set[str]] = None,
) -> List[Dict[str, object]]:
    """Attach per-quote confidence and keep Unknown when confidence is below threshold."""
    if not rows:
        return rows

    quote_meta: List[Tuple[int, List[Tuple[str, float]], float, float, float]] = []

    for idx, row in enumerate(rows):
        if not row.get("is_quote"):
            continue

        scores = _compute_quote_candidate_scores(
            rows,
            idx,
            alias_to_id,
            id_to_display,
            characters,
            adaptive_priors,
            global_character_priors,
        )

        ranked = sorted(
            (
                (n, s)
                for n, s in scores.items()
                if _is_valid_quote_speaker_label(n)
                and (not allowed_speakers or n in allowed_speakers)
            ),
            key=lambda kv: kv[1],
            reverse=True,
        )
        top_score = float(ranked[0][1]) if ranked else 0.0
        second_score = float(ranked[1][1]) if len(ranked) > 1 else 0.0
        confidence = _score_to_confidence(top_score, second_score)
        quote_meta.append((idx, ranked, top_score, second_score, confidence))

    effective_threshold = float(SPEAKER_CONFIDENCE_MIN)
    if quote_meta:
        provisional: List[str] = []
        for _idx, ranked, top_score, _second_score, conf in quote_meta:
            if not ranked or top_score <= 0.0 or conf < SPEAKER_CONFIDENCE_MIN:
                provisional.append("Unknown")
            else:
                provisional.append(ranked[0][0])

        unknown_ratio = provisional.count("Unknown") / float(len(provisional))
        named = [sp for sp in provisional if sp not in {"Unknown", "Narrator"}]
        dominant_share = 0.0
        if named:
            dominant_share = Counter(named).most_common(1)[0][1] / float(len(named))

        if unknown_ratio >= 0.55:
            effective_threshold -= 0.05
        elif unknown_ratio >= 0.40:
            effective_threshold -= 0.03

        if dominant_share >= 0.62:
            effective_threshold += 0.03

        effective_threshold = max(0.42, min(0.53, effective_threshold))

    for idx, ranked, top_score, second_score, confidence in quote_meta:
        row = rows[idx]
        top_name = ranked[0][0] if ranked else "Unknown"

        chosen = top_name
        if confidence < effective_threshold or top_score <= 0.0:
            chosen = "Unknown"

        text = str(row.get("text") or "")

        if chosen not in {"Unknown", "Narrator"} and _looks_vocative_addressed_to_speaker(text, chosen):
            if not _is_self_identification_quote(text, chosen):
                alt = None
                for cand_name, cand_score in ranked[1:]:
                    if cand_score <= 0 or not _is_valid_quote_speaker_label(cand_name):
                        continue
                    if not _looks_vocative_addressed_to_speaker(text, cand_name):
                        if cand_score >= (top_score * 0.85):
                            alt = cand_name
                        break
                chosen = alt or "Unknown"

        if chosen == "Unknown" and first_person_narration and _looks_first_person_quote(text):
            if _is_valid_quote_speaker_label(pov_speaker):
                chosen = str(pov_speaker)
            else:
                chosen = "Narrator"

        if chosen not in {"Unknown", "Narrator"} and allowed_speakers and chosen not in allowed_speakers:
            chosen = "Unknown"

        row["speaker"] = chosen
        row["speaker_confidence"] = round(float(confidence), 3)
        row["speaker_threshold"] = round(float(effective_threshold), 3)
        row["speaker_candidates"] = [
            {"speaker": name, "score": round(float(score), 3)}
            for name, score in ranked[:3]
        ]

    return rows


def _apply_vocative_self_mention_guard(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Prevent obvious 'addressed-to-name' quotes from being assigned to that same speaker."""
    if not rows:
        return rows

    for idx, row in enumerate(rows):
        if not row.get("is_quote"):
            continue
        speaker = row.get("speaker")
        if (
            not isinstance(speaker, str)
            or speaker in {"Unknown"}
            or row.get("speaker_source") == "explicit_narration_cue"
        ):
            continue

        text = str(row.get("text") or "")
        if not _looks_vocative_addressed_to_speaker(text, speaker):
            continue

        prev_named = _nearest_named_quote_speaker(rows, idx, -1)
        next_named = _nearest_named_quote_speaker(rows, idx, 1)

        replacement: Optional[str] = None
        if prev_named and prev_named != speaker:
            replacement = prev_named
        elif next_named and next_named != speaker:
            replacement = next_named
        else:
            replacement = "Unknown"

        if replacement != speaker:
            row["speaker"] = replacement
            row["speaker_source"] = "vocative_address_guard"

    return rows


def _rebalance_long_quote_streaks(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Break implausibly long single-speaker stretches when confidence is weak."""
    if not rows:
        return rows

    quote_positions = [i for i, r in enumerate(rows) if r.get("is_quote")]
    if not quote_positions:
        return rows

    runs: List[Tuple[str, int, int]] = []
    cur_sp = None
    run_start = -1
    for q_idx, row_idx in enumerate(quote_positions):
        sp = str(rows[row_idx].get("speaker") or "Unknown")
        if cur_sp is None:
            cur_sp = sp
            run_start = q_idx
            continue
        if sp != cur_sp:
            runs.append((cur_sp, run_start, q_idx - 1))
            cur_sp = sp
            run_start = q_idx
    if cur_sp is not None:
        runs.append((cur_sp, run_start, len(quote_positions) - 1))

    for sp, start_q, end_q in runs:
        run_len = end_q - start_q + 1
        if run_len < 6:
            continue
        if sp in {"Unknown", "Narrator"}:
            continue

        for qpos in range(start_q, end_q + 1):
            ridx = quote_positions[qpos]
            row = rows[ridx]
            conf = float(row.get("speaker_confidence", 0.0) or 0.0)
            if conf >= 0.82:
                continue
            near_text = f"{rows[ridx-1].get('text','') if ridx-1>=0 else ''} {rows[ridx+1].get('text','') if ridx+1 < len(rows) else ''}"
            if _has_continuity_cue(near_text):
                continue
            # Keep every third entry to preserve plausible local turn continuity.
            if ((qpos - start_q) % 3) != 0:
                row["speaker"] = "Unknown"

    return rows


def _reevaluate_long_quote_blocks(
    rows: List[Dict[str, object]],
    alias_to_id: Dict[str, str],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
    adaptive_priors: Dict[str, float],
    global_character_priors: Optional[Dict[str, float]] = None,
    allowed_speakers: Optional[Set[str]] = None,
    pov_speaker: Optional[str] = None,
) -> List[Dict[str, object]]:
    """
    Re-evaluate quote runs longer than 3 using wider backward/forward context.

    This is intentionally conservative: it only changes low-confidence lines when
    a competing speaker has clear support from distant context or anchor speakers.
    """
    if not rows:
        return rows

    quote_positions = [i for i, r in enumerate(rows) if r.get("is_quote")]
    if not quote_positions:
        return rows

    runs: List[Tuple[str, int, int]] = []
    cur_sp = None
    run_start = -1
    for q_idx, row_idx in enumerate(quote_positions):
        sp = str(rows[row_idx].get("speaker") or "Unknown")
        if cur_sp is None:
            cur_sp = sp
            run_start = q_idx
            continue
        if sp != cur_sp:
            runs.append((cur_sp, run_start, q_idx - 1))
            cur_sp = sp
            run_start = q_idx
    if cur_sp is not None:
        runs.append((cur_sp, run_start, len(quote_positions) - 1))

    def _anchor_nearest_named(start_q: int, direction: int, max_hops: int = 12) -> Tuple[Optional[str], Optional[int]]:
        q = start_q + direction
        hops = 0
        while 0 <= q < len(quote_positions) and hops < max_hops:
            ridx = quote_positions[q]
            sp = rows[ridx].get("speaker")
            if isinstance(sp, str) and sp not in {"Unknown", "Narrator"}:
                if _is_valid_quote_speaker_label(sp):
                    return sp, (hops + 1)
            q += direction
            hops += 1
        return None, None

    for run_sp, start_q, end_q in runs:
        run_len = end_q - start_q + 1
        if run_len <= 3:
            continue
        if run_sp in {"Unknown", "Narrator"}:
            continue

        prev_anchor, prev_dist = _anchor_nearest_named(start_q, -1)
        next_anchor, next_dist = _anchor_nearest_named(end_q, +1)

        anchor_scores: Dict[str, float] = defaultdict(float)
        if prev_anchor and prev_anchor != run_sp and _is_valid_quote_speaker_label(prev_anchor):
            anchor_scores[prev_anchor] += max(0.8, 2.0 / float((prev_dist or 1) + 0.4))
        if next_anchor and next_anchor != run_sp and _is_valid_quote_speaker_label(next_anchor):
            anchor_scores[next_anchor] += max(0.8, 2.0 / float((next_dist or 1) + 0.4))
        if _is_valid_quote_speaker_label(pov_speaker) and pov_speaker != run_sp:
            anchor_scores[str(pov_speaker)] += 0.35

        for qpos in range(start_q, end_q + 1):
            ridx = quote_positions[qpos]
            row = rows[ridx]
            conf = float(row.get("speaker_confidence", 0.0) or 0.0)
            if conf >= 0.86:
                continue

            # Build wider narration context than the default confidence pass.
            weighted_contexts: List[Tuple[str, float]] = []
            for offset in range(-6, 7):
                if offset == 0:
                    continue
                j = ridx + offset
                if j < 0 or j >= len(rows):
                    continue
                near = rows[j]
                if near.get("is_quote"):
                    continue
                near_text = str(near.get("text") or "")
                if near_text:
                    weighted_contexts.append((near_text, max(0.15, 1.15 / (abs(offset) + 0.5))))
            for back, prev_row in enumerate(reversed(rows[max(0, ridx - 16):ridx]), start=1):
                if prev_row.get("is_quote"):
                    continue
                prev_text = str(prev_row.get("text") or "")
                if prev_text:
                    weighted_contexts.append((prev_text, 0.5 / back))

            sp_scores, _ = _score_weighted_context(weighted_contexts, alias_to_id, id_to_display, characters)

            combined: Dict[str, float] = defaultdict(float)
            for cand, score in sp_scores.items():
                combined[cand] += 0.65 * float(score)
            for cand, score in anchor_scores.items():
                combined[cand] += float(score)

            # Blend with normal candidate scores to avoid abrupt flips.
            base_scores = _compute_quote_candidate_scores(
                rows,
                ridx,
                alias_to_id,
                id_to_display,
                characters,
                adaptive_priors,
                global_character_priors,
            )
            for cand, score in base_scores.items():
                combined[cand] += 0.35 * float(score)

            # Encourage alternatives when a run is long and weak.
            combined[run_sp] -= 0.9 + (0.18 * min(6, run_len - 3))

            ranked = sorted(
                (
                    (n, s)
                    for n, s in combined.items()
                    if _is_valid_quote_speaker_label(n)
                    and (not allowed_speakers or n in allowed_speakers)
                ),
                key=lambda kv: kv[1],
                reverse=True,
            )
            if not ranked:
                continue

            best_name, best_score = ranked[0]
            run_score = float(combined.get(run_sp, -999.0))
            if best_name == run_sp:
                continue
            if best_score < 0.7:
                continue
            if run_score > -999.0 and best_score < (run_score + 0.35):
                continue

            row["speaker"] = best_name

    return rows


def _rebalance_first_person_pov_runs(rows: List[Dict[str, object]], pov_speaker: Optional[str]) -> List[Dict[str, object]]:
    """
    In first-person narration, avoid long monologues incorrectly collapsed to a
    non-POV speaker when confidence is weak.
    """
    if not rows or not _is_valid_quote_speaker_label(pov_speaker):
        return rows

    quote_positions = [i for i, r in enumerate(rows) if r.get("is_quote")]
    if not quote_positions:
        return rows

    runs: List[Tuple[str, int, int]] = []
    cur_sp = None
    run_start = -1
    for q_idx, row_idx in enumerate(quote_positions):
        sp = str(rows[row_idx].get("speaker") or "Unknown")
        if cur_sp is None:
            cur_sp = sp
            run_start = q_idx
            continue
        if sp != cur_sp:
            runs.append((cur_sp, run_start, q_idx - 1))
            cur_sp = sp
            run_start = q_idx
    if cur_sp is not None:
        runs.append((cur_sp, run_start, len(quote_positions) - 1))

    for sp, start_q, end_q in runs:
        run_len = end_q - start_q + 1
        if run_len < 5:
            continue
        if sp in {"Unknown", "Narrator", str(pov_speaker)}:
            continue

        for qpos in range(start_q, end_q + 1):
            ridx = quote_positions[qpos]
            row = rows[ridx]
            conf = float(row.get("speaker_confidence", 0.0) or 0.0)
            if conf >= 0.74:
                continue

            # Flip every second weak line to POV to restore conversation shape.
            if ((qpos - start_q) % 2) == 1:
                row["speaker"] = str(pov_speaker)

    return rows


def _infer_first_person_protagonist_name(text: str, id_to_display: Dict[str, str]) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    scores: Dict[str, int] = {}
    for _, name in (id_to_display or {}).items():
        if not _is_valid_quote_speaker_label(name):
            continue
        parts = [p for p in re.split(r"\s+", name.strip()) if p]
        if not parts:
            continue
        full_hits = len(re.findall(rf"\b{re.escape(name.lower())}\b", lowered))
        last_hits = len(re.findall(rf"\b{re.escape(parts[-1].lower())}\b", lowered)) if len(parts) >= 2 else 0
        # Penalize place-like constructions so location mentions don't dominate.
        place_like_hits = len(
            re.findall(
                rf"\b{re.escape(parts[-1].lower())}\b\s+(world|city|station|house|tower|bay|district|province|sector)\b",
                lowered,
            )
        )
        score = (full_hits * 4) + last_hits - (place_like_hits * 5)
        if score > 0:
            scores[name] = score
    if not scores:
        return None
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if ranked[0][1] < 2:
        return None
    return ranked[0][0]


def _character_variants_for_matching(
    cid: str,
    display: str,
    characters: Dict[str, Dict[str, object]],
) -> List[str]:
    variants: List[str] = []
    if display:
        variants.append(str(display))
    meta = characters.get(str(cid), {}) if isinstance(characters, dict) else {}
    for key in ("canonical_name", "normalized_name"):
        value = meta.get(key)
        if value:
            variants.append(str(value))
    deduped: List[str] = []
    for value in variants:
        if not value:
            continue
        cleaned = _clean_surface(str(value))
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)

        # BookNLP can prepend descriptive fragments (e.g. "Hard-eyed Virginia Vidaura").
        # Add a stable 2-token tail variant so narration matching still finds the person.
        tokens = [tok for tok in re.findall(r"[A-Za-z][A-Za-z'\-]*", cleaned) if tok]
        if len(tokens) >= 2:
            tail = " ".join(tokens[-2:])
            if tail not in deduped:
                deduped.append(tail)
    return deduped


def _variant_matches_text(variant: str, lowered_text: str) -> bool:
    if not variant or not lowered_text:
        return False
    tokens = [tok for tok in re.findall(r"[a-z][a-z'\-]*", variant.lower()) if tok]
    if not tokens:
        return False
    # Be resilient to punctuation/hyphen spacing differences in extracted names.
    joiner = r"(?:\s+|[-'’.]|\s*[-'’.]\s*)+"
    pattern = rf"\b{joiner.join(re.escape(tok) for tok in tokens)}\b"
    return bool(re.search(pattern, lowered_text))


def _looks_place_like_character_alias(name: str, text: str) -> bool:
    """Reject aliases that mostly appear as locations (e.g. Harlan in Harlan's World)."""
    if not name or not text:
        return False

    tokens = [tok for tok in re.findall(r"[A-Za-z][A-Za-z'\-]*", name) if tok]
    lowered = text.lower()
    speech_verbs = r"said|asked|replied|answered|told|murmured|whispered|shouted|yelled|growled|snarled|gasped|stammered"

    if len(tokens) == 1:
        base = re.escape(tokens[0].lower())
        place_hits = len(
            re.findall(
                rf"\b{base}(?:'s)?\s+(world|city|station|house|tower|bay|district|province|sector|system|facility|administration|justice)\b",
                lowered,
            )
        )
        speech_hits = len(re.findall(rf"\b{base}\b\s+(?:{speech_verbs})\b", lowered))
        return place_hits >= 2 and speech_hits == 0

    place_suffixes = {
        "world", "city", "station", "house", "tower", "bay", "district",
        "province", "sector", "system", "facility", "administration", "justice",
        "county", "center", "agency", "agencies", "airport", "river", "mountain",
    }
    if tokens[-1].lower() not in place_suffixes:
        return False

    phrase = re.escape(" ".join(tokens).lower())
    phrase_hits = len(re.findall(rf"\b{phrase}\b", lowered))
    speech_hits = len(
        re.findall(
            rf"(?:\b{phrase}\b\s+(?:{speech_verbs})\b|\b(?:{speech_verbs})\b\s+(?:the\s+)?{phrase}\b)",
            lowered,
        )
    )
    return phrase_hits >= 2 and speech_hits == 0


def _build_booknlp_character_coverage(
    rows: List[Dict[str, object]],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    """Summarize BookNLP character visibility across narration and attributed quotes."""
    quote_counts: Counter = Counter()
    narration_mentions: Counter = Counter()

    for row in rows or []:
        speaker = row.get("speaker")
        text = str(row.get("text") or "")
        if row.get("is_quote"):
            if isinstance(speaker, str) and speaker not in {"Unknown", "Narrator"}:
                quote_counts[speaker] += 1
            continue

        if speaker != "Narrator" or not text:
            continue

        lowered = text.lower()
        for cid, display in (id_to_display or {}).items():
            if not display or display in {"Unknown", "Narrator"}:
                continue
            for variant in _character_variants_for_matching(cid, display, characters):
                if not variant:
                    continue
                if _variant_matches_text(str(variant), lowered):
                    narration_mentions[display] += 1
                    break

    coverage: List[Dict[str, object]] = []
    for cid, display in (id_to_display or {}).items():
        if not display or display in {"Unknown", "Narrator"}:
            continue
        meta = characters.get(str(cid), {}) if isinstance(characters, dict) else {}
        mention_count = 0
        try:
            mention_count = int(meta.get("mention_count", 0))
        except Exception:
            mention_count = 0
        coverage.append(
            {
                "name": display,
                "mention_count": mention_count,
                "quote_count": int(quote_counts.get(display, 0)),
                "narration_mentions": int(narration_mentions.get(display, 0)),
            }
        )

    coverage.sort(
        key=lambda item: (
            int(item.get("quote_count", 0)),
            int(item.get("narration_mentions", 0)),
            int(item.get("mention_count", 0)),
            len(str(item.get("name", ""))),
        ),
        reverse=True,
    )
    return coverage


def _infer_main_character(
    rows: List[Dict[str, object]],
    id_to_display: Dict[str, str],
    characters: Dict[str, Dict[str, object]],
    first_person_narration: bool,
) -> Dict[str, object]:
    """
    Infer likely protagonist/main POV character.

    Returns:
      {
        "name": Optional[str],
        "confidence": float,
        "reason": str,
        "candidates": [{"name": str, "score": float}]
      }
    """
    quote_counts: Dict[str, int] = Counter()
    narration_counts: Dict[str, int] = Counter()
    addressed_counts: Dict[str, int] = Counter()
    unknown_quotes = 0
    total_quotes = 0

    for row in rows or []:
        speaker = row.get("speaker")
        text = str(row.get("text") or "")

        if row.get("is_quote"):
            total_quotes += 1
            if not isinstance(speaker, str) or speaker in {"Unknown", "Narrator"}:
                unknown_quotes += 1
            else:
                quote_counts[speaker] += 1

            lowered_quote = text.lower()
            for cid, display in (id_to_display or {}).items():
                if not display or display in {"Unknown", "Narrator"}:
                    continue
                for variant in _character_variants_for_matching(cid, display, characters):
                    if not variant:
                        continue
                    if _variant_matches_text(str(variant), lowered_quote):
                        addressed_counts[display] += 1
                        break
        elif speaker == "Narrator" and text:
            lowered = text.lower()
            for cid, display in (id_to_display or {}).items():
                if not display or display in {"Unknown", "Narrator"}:
                    continue
                for variant in _character_variants_for_matching(cid, display, characters):
                    if not variant:
                        continue
                    if _variant_matches_text(str(variant), lowered):
                        narration_counts[display] += 1
                        break

    # Build candidate metadata from BookNLP character payload
    candidates: Dict[str, Dict[str, float]] = {}
    for cid, display in (id_to_display or {}).items():
        if not display or display in {"Unknown", "Narrator"}:
            continue
        meta = characters.get(str(cid), {}) if isinstance(characters, dict) else {}
        mention_count = 0
        try:
            mention_count = int(meta.get("mention_count", 0))
        except Exception:
            mention_count = 0

        narration_mentions = float(narration_counts.get(display, 0))
        quote_mentions = float(quote_counts.get(display, 0))
        addressed_mentions = float(addressed_counts.get(display, 0))
        score = (
            narration_mentions * 4.0
            + addressed_mentions * 6.0
            + quote_mentions * 1.5
            + float(mention_count)
        )

        # In first-person books, the protagonist is often the most-addressed name in dialogue.
        unknown_ratio = (unknown_quotes / total_quotes) if total_quotes else 0.0
        if first_person_narration:
            score += addressed_mentions * 2.0
            score += narration_mentions * 1.5
            if unknown_ratio >= 0.4:
                score += float(mention_count) * 0.25

        # Soft penalty for obvious non-person labels.
        if display.lower().startswith("the "):
            score *= 0.8

        candidates[display] = {
            "score": score,
            "mention_count": float(mention_count),
            "quote_count": quote_mentions,
            "narration_count": narration_mentions,
            "addressed_count": addressed_mentions,
        }

    if not candidates:
        return {
            "name": None,
            "confidence": 0.0,
            "reason": "No suitable character candidates available.",
            "candidates": [],
        }

    ranked = sorted(candidates.items(), key=lambda kv: kv[1]["score"], reverse=True)
    best_name, best_stats = ranked[0]
    second_score = ranked[1][1]["score"] if len(ranked) > 1 else 0.0
    margin = max(0.0, best_stats["score"] - second_score)
    confidence = 0.5
    if best_stats["score"] > 0:
        confidence = min(0.95, 0.55 + (margin / (best_stats["score"] + 1.0)))

    reason = (
        f"Selected by combined mention+dialogue score "
        f"(narration={int(best_stats['narration_count'])}, addressed={int(best_stats['addressed_count'])}, quotes={int(best_stats['quote_count'])}, mentions={int(best_stats['mention_count'])})."
    )

    return {
        "name": best_name,
        "confidence": round(float(confidence), 3),
        "reason": reason,
        "candidates": [
            {"name": name, "score": round(float(stats["score"]), 3)}
            for name, stats in ranked[:5]
        ],
    }

def _fallback_speaker_label(raw: str) -> Optional[str]:
    cleaned = _clean_surface(raw)
    if not cleaned:
        return None
    if len(cleaned) > 40:
        return None

    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*", cleaned)
    normalized: List[str] = []
    for token in tokens:
        core = token.rstrip("-")
        if len(core) <= 1:
            continue
        if core.lower() in STOP_TOKENS:
            return None
        if not core[0].isalpha() or not core[0].isupper():
            return None
        if len(core) > 20:
            return None
        normalized.append(core)

    if not normalized or len(normalized) > 3:
        return None

    lowered_tokens = {tok.lower() for tok in normalized}
    if lowered_tokens & NON_PERSON_LABEL_TOKENS:
        return None

    return " ".join(normalized)


def _strip_title_tokens(tokens: List[str]) -> List[str]:
    while tokens and tokens[0].lower().rstrip(".") in TITLE_PREFIXES:
        tokens.pop(0)
    return tokens


def _smart_capitalize(name: str) -> str:
    def _cap(token: str) -> str:
        if not token:
            return token
        if token.isupper():
            return token
        if len(token) == 1:
            return token.upper()
        if token[0].isalpha():
            return token[0].upper() + token[1:]
        return token

    parts = re.split(r"(\W+)", name)
    return "".join(_cap(part) if part.isalpha() else part for part in parts)


@dataclass
class DetectionOutput:
    lines: List[Dict[str, object]]
    character_order: List[str]
    characters: Dict[str, Dict[str, object]]

    def as_dict(self) -> Dict[str, object]:
        return {
            "lines": self.lines,
            "character_order": self.character_order,
            "characters": self.characters,
        }


# -----------------------------------------------------------------------------
# Core processing
# -----------------------------------------------------------------------------


class _BookNLPDetector:
    """Thin wrapper around EnglishBookNLP with on-disk caching."""

    def __init__(self, model: str = BOOKNLP_MODEL_DEFAULT):
        self.model = model or BOOKNLP_MODEL_DEFAULT
        self._booknlp: Optional[EnglishBookNLP] = None

    def _ensure_pipeline(self) -> EnglishBookNLP:
        if self._booknlp is None:
            params = {"model": self.model, "pipeline": BOOKNLP_PIPELINE}
            self._booknlp = EnglishBookNLP(params)
        return self._booknlp

    def process(self, text: str, chapter_title: Optional[str], force_reprocess: bool = False) -> Tuple[Path, str]:
        slug = _safe_slug(chapter_title)
        digest = _hash_text(text)[:12]
        prefix = f"{slug}_{digest}_{CACHE_FORMAT_VERSION}"
        out_dir = CACHE_ROOT / prefix
        book_path = out_dir / f"{prefix}.book.txt"

        if force_reprocess and out_dir.exists():
            print(f"[CharacterDetection] Forcing fresh BookNLP run: {prefix}")
            shutil.rmtree(out_dir, ignore_errors=True)

        if not book_path.exists():
            print(f"[CharacterDetection] BookNLP cache MISS: {prefix}")
            out_dir.mkdir(parents=True, exist_ok=True)
            input_path = out_dir / f"{prefix}.txt"
            input_path.write_text(text, encoding="utf-8")
            pipeline = self._ensure_pipeline()
            pipeline.process(str(input_path), str(out_dir), prefix)
        else:
            print(f"[CharacterDetection] BookNLP cache HIT: {prefix}")

        return out_dir, prefix


def _load_characters(characters_json: Path) -> Dict[str, Dict[str, object]]:
    if not characters_json.exists():
        return {}
    data = json.loads(characters_json.read_text(encoding="utf-8"))
    characters: Dict[str, Dict[str, object]] = {}
    for entry in data.get("characters", []):
        canonical = entry.get("canonical_name")
        cid = entry.get("character_id")
        if canonical is None or cid is None:
            continue
        characters[str(cid)] = entry
    return characters


def _load_quote_only_characters(
    simple_characters_json: Path,
    quotes_path: Path,
    existing_ids: Iterable[str],
) -> Dict[str, Dict[str, object]]:
    """Recover filtered BookNLP IDs only when they are used by a quote span."""
    if not simple_characters_json.exists() or not quotes_path.exists():
        return {}

    existing = {str(cid) for cid in existing_ids}
    quote_ids = {
        str(span.char_id)
        for span in _load_quote_spans(quotes_path)
        if span.char_id is not None and span.char_id >= 0
    }
    if not quote_ids - existing:
        return {}

    data = json.loads(simple_characters_json.read_text(encoding="utf-8"))
    recovered: Dict[str, Dict[str, object]] = {}
    for entry in data.get("characters", []):
        cid = entry.get("char_id", entry.get("character_id"))
        if cid is None or str(cid) not in quote_ids or str(cid) in existing:
            continue

        raw_name = entry.get("normalized_name") or entry.get("canonical_name") or ""
        tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*", str(raw_name))
        if tokens and tokens[0].lower() in {"the", "a", "an"}:
            tokens = tokens[1:]
        if len(tokens) > 3 or any(token.lower() in QUOTE_ONLY_GROUP_LABEL_TOKENS for token in tokens):
            continue
        display = _smart_capitalize(" ".join(tokens))
        if not _is_valid_quote_speaker_label(display):
            continue

        recovered[str(cid)] = {
            "character_id": cid,
            "canonical_name": display,
            "normalized_name": display,
            "mention_count": 0,
            "booknlp_quote_fallback": True,
        }
    return recovered


def _collect_entity_mentions(entities_path: Path, allowed_ids: Iterable[str]) -> Tuple[Dict[str, Counter], Dict[str, Counter]]:
    proper_mentions: Dict[str, Counter] = defaultdict(Counter)
    part_mentions: Dict[str, Counter] = defaultdict(Counter)

    if not entities_path.exists():
        return proper_mentions, part_mentions

    allowed = set(allowed_ids)
    with entities_path.open("r", encoding="utf-8", errors="ignore") as handle:
        header = handle.readline()
        for raw in handle:
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            cid, *_rest, prop, cat, surface = parts
            if allowed and cid not in allowed:
                continue
            if "PER" not in cat.upper():
                continue
            clean_surface = _clean_surface(surface)
            if not clean_surface:
                continue
            tokens = [tok for tok in re.split(r"\s+", clean_surface) if tok]
            if not tokens:
                continue
            if prop.upper() == "PROP":
                proper_mentions[cid][clean_surface] += 1
                for tok in tokens:
                    part_mentions[cid][tok] += 1
            else:
                for tok in tokens:
                    if tok.lower() not in STOP_TOKENS:
                        part_mentions[cid][tok] += 1
    return proper_mentions, part_mentions


def _select_display_name(canonical: str, cid: str, proper: Counter, parts: Counter) -> Optional[str]:
    candidates = proper.most_common()
    for surface, _count in candidates:
        tokens = [tok for tok in surface.split() if tok]
        tokens = _strip_title_tokens(tokens)
        if len(tokens) >= 2:
            candidate = " ".join(tokens)
            return _smart_capitalize(candidate)

    # Fallback: combine best first name with canonical last name
    canonical_tokens = [tok for tok in canonical.split() if tok]
    canonical_tokens = _strip_title_tokens(canonical_tokens)
    last_name = canonical_tokens[-1] if canonical_tokens else canonical

    first_candidates = [(tok, cnt) for tok, cnt in parts.items() if tok.lower() not in STOP_TOKENS]
    first_candidates.sort(key=lambda item: (-item[1], -len(item[0])))

    for token, _count in first_candidates:
        cleaned = re.sub(r"[^A-Za-z-]", "", token)
        if not cleaned:
            continue
        if cleaned.lower() == last_name.lower():
            continue
        return _smart_capitalize(f"{cleaned} {last_name}")

    return None


def _build_alias_index(characters: Dict[str, Dict[str, object]], proper: Dict[str, Counter], display_names: Dict[str, str]) -> Dict[str, str]:
    alias_ids: Dict[str, set] = defaultdict(set)

    for cid, data in characters.items():
        canonical = data.get("canonical_name", "")
        for candidate in [canonical, data.get("normalized_name", "")]:
            key = _normalize_alias(candidate)
            if key:
                alias_ids[key].add(cid)

    for cid, counter in proper.items():
        for surface in counter:
            key = _normalize_alias(surface)
            if key:
                alias_ids[key].add(cid)
            for token in surface.split():
                key = _normalize_alias(token)
                if key:
                    alias_ids[key].add(cid)

    alias_to_id = {}
    for key, ids in alias_ids.items():
        if len(ids) == 1:
            alias_to_id[key] = next(iter(ids))
    # ensure display name tokens also map back
    for cid, display in display_names.items():
        key = _normalize_alias(display)
        if key:
            alias_to_id.setdefault(key, cid)
        for token in display.split():
            key = _normalize_alias(token)
            if key and key not in STOP_TOKENS:
                alias_to_id.setdefault(key, cid)
    return alias_to_id


def _normalize_alias(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    if not cleaned:
        return None
    if cleaned in STOP_TOKENS:
        return None
    return cleaned


def _load_token_offsets(tokens_path: Path) -> Dict[int, Tuple[int, int, str]]:
    offsets: Dict[int, Tuple[int, int, str]] = {}
    if not tokens_path.exists():
        return offsets

    with tokens_path.open("r", encoding="utf-8", errors="ignore") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        try:
            doc_idx = header.index("token_ID_within_document")
            start_idx = header.index("byte_onset")
            end_idx = header.index("byte_offset")
            word_idx = header.index("word")
        except ValueError:
            return offsets

        for raw in handle:
            if not raw.strip():
                continue
            parts = raw.rstrip("\n").split("\t")
            try:
                token_id = int(parts[doc_idx])
                start = int(parts[start_idx])
                end = int(parts[end_idx])
            except (ValueError, IndexError):
                continue
            word = parts[word_idx] if word_idx < len(parts) else ""
            offsets[token_id] = (start, end, word)
    return offsets


@dataclass
class QuoteSpan:
    start_token: int
    end_token: int
    mention: Optional[str]
    char_id: Optional[int]


def _load_quote_spans(quotes_path: Path) -> List[QuoteSpan]:
    spans: List[QuoteSpan] = []
    if not quotes_path.exists():
        return spans

    with quotes_path.open("r", encoding="utf-8", errors="ignore") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        try:
            start_idx = header.index("quote_start")
            end_idx = header.index("quote_end")
            mention_idx = header.index("mention_phrase")
            char_idx = header.index("char_id") if "char_id" in header else header.index("character_id")
        except ValueError:
            return spans

        for raw in handle:
            if not raw.strip():
                continue
            parts = raw.rstrip("\n").split("\t")
            try:
                start = int(parts[start_idx])
                end = int(parts[end_idx])
            except (ValueError, IndexError):
                continue
            mention = parts[mention_idx] if mention_idx < len(parts) else None
            try:
                char_raw = parts[char_idx]
                char_id = int(char_raw)
            except (ValueError, IndexError):
                char_id = None
            spans.append(QuoteSpan(start_token=start, end_token=end, mention=mention, char_id=char_id))
    spans.sort(key=lambda span: span.start_token)
    return spans


def _segment_text_using_quotes(
    text: str,
    tokens_path: Path,
    quotes_path: Path,
) -> List[Dict[str, object]]:
    offsets = _load_token_offsets(tokens_path)
    spans = _load_quote_spans(quotes_path)

    if not text or not offsets or not spans:
        return []

    segments: List[Dict[str, object]] = []
    cursor = 0
    text_length = len(text)

    for span in spans:
        token_start = offsets.get(span.start_token)
        token_end = offsets.get(span.end_token)
        if not token_start or not token_end:
            continue
        start_char = token_start[0]
        end_char = token_end[1]
        token_cursor = span.end_token

        while True:
            next_token = offsets.get(token_cursor + 1)
            if not next_token:
                break
            token_cursor += 1
            _, next_end, next_word = next_token
            # include trailing punctuation until we hit the closing quote
            end_char = next_end
            if next_word in CLOSE_QUOTE_CHARS:
                break
            if next_word in OPEN_QUOTE_CHARS:
                # encountered the start of the next quote without finding a close
                break

        if end_char <= start_char:
            continue

        # narration before quote
        if start_char > cursor:
            narration = _normalize_whitespace(text[cursor:start_char])
            if _has_meaningful_text(narration):
                narration = _fix_contractions(narration)
                segments.append({
                    "type": "narration",
                    "text": narration,
                })

        quote_text = _normalize_whitespace(text[start_char:end_char])
        if _has_meaningful_text(quote_text):
            quote_text = _fix_contractions(quote_text)
            segments.append({
                "type": "quote",
                "text": quote_text,
                "char_id": span.char_id,
                "mention": span.mention,
            })

        cursor = max(cursor, end_char)

    if cursor < text_length:
        tail = _normalize_whitespace(text[cursor:])
        if _has_meaningful_text(tail):
            tail = _fix_contractions(tail)
            segments.append({
                "type": "narration",
                "text": tail,
            })

    return segments


def _split_segments(text: str) -> List[Tuple[str, bool]]:
    segments: List[Tuple[str, bool]] = []
    buffer: List[str] = []
    inside_quote = False

    def flush(is_quote: bool):
        if not buffer:
            return
        chunk = "".join(buffer).strip()
        buffer.clear()
        if chunk:
            segments.append((chunk, is_quote))

    for ch in text:
        if ch in {'"', '\u201c', '\u201d'}:
            if inside_quote:
                flush(True)
                inside_quote = False
            else:
                flush(False)
                inside_quote = True
        else:
            buffer.append(ch)
    flush(inside_quote)
    return segments or [(text.strip(), False)]


def _merge_adjacent_narration(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    merged: List[Dict[str, object]] = []
    for row in rows:
        if not merged:
            merged.append(row)
            continue
        if row.get("speaker") == "Narrator" and merged[-1].get("speaker") == "Narrator":
            merged[-1]["text"] = f"{merged[-1]['text']} {row['text']}".strip()
        else:
            merged.append(row)
    return merged


def _split_mixed_narrator_rows(rows: List[Dict[str, object]], first_person_narration: bool) -> List[Dict[str, object]]:
    """Split any Narrator row that still contains quoted spans into separate rows."""
    normalized: List[Dict[str, object]] = []
    for row in rows:
        speaker = row.get("speaker")
        text = str(row.get("text", "") or "")
        is_quote = bool(row.get("is_quote", False))

        if speaker != "Narrator" or is_quote:
            normalized.append(row)
            continue

        pieces = _split_quote_segments(text)
        if not pieces or len(pieces) <= 1 or not any(p.get("type") == "quote" for p in pieces):
            normalized.append(row)
            continue

        for piece in pieces:
            piece_type = piece.get("type")
            piece_text = _fix_contractions(piece.get("text", ""))
            if not _has_meaningful_text(piece_text):
                continue

            if piece_type == "quote":
                quote_speaker = "Unknown"
                if first_person_narration and _looks_first_person_quote(piece_text):
                    quote_speaker = "Narrator"
                normalized.append({
                    "speaker": quote_speaker,
                    "text": piece_text,
                    "is_quote": True,
                })
            else:
                normalized.append({
                    "speaker": "Narrator",
                    "text": piece_text,
                    "is_quote": False,
                })

    return normalized


def _split_mixed_quote_rows(rows: List[Dict[str, object]], first_person_narration: bool) -> List[Dict[str, object]]:
    """Split any quote row that still contains narration between quoted spans."""
    normalized: List[Dict[str, object]] = []

    for row in rows:
        text = str(row.get("text", "") or "")
        if not text:
            normalized.append(row)
            continue

        pieces = _split_quote_segments(text)
        has_quote_piece = any(p.get("type") == "quote" for p in pieces)
        has_narr_piece = any(p.get("type") == "narration" for p in pieces)

        if not pieces or len(pieces) <= 1 or not (has_quote_piece and has_narr_piece):
            normalized.append(row)
            continue

        base_speaker = row.get("speaker") or "Unknown"
        for piece in pieces:
            piece_type = piece.get("type")
            piece_text = _fix_contractions(piece.get("text", ""))
            if not _has_meaningful_text(piece_text):
                continue

            if piece_type == "quote":
                quote_speaker = base_speaker
                if quote_speaker == "Unknown" and first_person_narration and _looks_first_person_quote(piece_text):
                    quote_speaker = "Narrator"
                normalized.append({
                    "speaker": quote_speaker,
                    "text": piece_text,
                    "is_quote": True,
                })
            else:
                normalized.append({
                    "speaker": "Narrator",
                    "text": piece_text,
                    "is_quote": False,
                })

    return normalized


def _parse_book_rows(book_txt: Path, normalize_speaker) -> Tuple[List[Dict[str, object]], List[str]]:
    if not book_txt.exists():
        return [], []

    row_pattern = re.compile(r"^\[(?P<speaker>[^\]]+)\]\s*(?P<text>.*)\[/\]$")
    rows: List[Dict[str, object]] = []
    order: List[str] = []

    with book_txt.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            match = row_pattern.match(line)
            if not match:
                continue
            raw_speaker = match.group("speaker").strip()
            text = match.group("text").strip()
            text = _fix_contractions(text)
            for segment, is_quote in _split_segments(text):
                if not segment:
                    continue
                segment = _fix_contractions(segment)
                if is_quote:
                    speaker = normalize_speaker(raw_speaker)
                    if not speaker:
                        speaker = "Unknown"
                    if speaker not in order and speaker not in {"Narrator", "Unknown"}:
                        order.append(speaker)
                    rows.append({
                        "speaker": speaker,
                        "text": segment,
                        "is_quote": True,
                    })
                else:
                    rows.append({
                        "speaker": "Narrator",
                        "text": segment,
                        "is_quote": False,
                    })
    rows = _merge_adjacent_narration(rows)
    return rows, order


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


_detector_pool: Dict[str, _BookNLPDetector] = {}


def _get_detector(model: str) -> _BookNLPDetector:
    key = model or BOOKNLP_MODEL_DEFAULT
    if key not in _detector_pool:
        _detector_pool[key] = _BookNLPDetector(model=key)
    return _detector_pool[key]


def _normalize_speaker_factory(characters: Dict[str, Dict[str, object]], display_names: Dict[str, str], alias_to_id: Dict[str, str]):
    def _normalize(name: str) -> Optional[str]:
        if not name:
            return None
        cleaned = _clean_surface(name)
        if not cleaned:
            return None
        key = _normalize_alias(cleaned)
        if key in {None, "unknown", "unk"}:
            return None
        cid = alias_to_id.get(key)
        if cid is not None:
            meta = characters.get(str(cid))
            display = display_names.get(str(cid)) or display_names.get(cid)
            if display:
                return display
            if meta:
                canonical = meta.get("canonical_name") or meta.get("normalized_name")
                if canonical:
                    return _smart_capitalize(str(canonical))
        fallback = _fallback_speaker_label(cleaned)
        if fallback and _is_valid_quote_speaker_label(fallback):
            return fallback
        return None

    return _normalize


def run_attribution(
    text: str,
    *,
    title: Optional[str] = None,
    book_key: Optional[str] = None,
    global_character_priors: Optional[Dict[str, float]] = None,
    allowed_book_characters: Optional[Iterable[str]] = None,
    pov_speaker_override: Optional[str] = None,
    model: str = BOOKNLP_MODEL_DEFAULT,
    max_lines: Optional[int] = None,
    force_reprocess: bool = False,
) -> Dict[str, object]:
    detector = _get_detector(model)
    chapter_num = _chapter_number_from_title(title)
    adaptive_key = _adaptive_book_key(title, explicit_key=book_key)
    adaptive_priors = _get_adaptive_priors(adaptive_key, chapter_num)
    first_person_narration = is_first_person_narration(text)
    allowed_speakers: Optional[Set[str]] = None
    if allowed_book_characters:
        allowed_speakers = {
            str(name).strip()
            for name in allowed_book_characters
            if isinstance(name, str) and str(name).strip()
        }
        if not allowed_speakers:
            allowed_speakers = None

    try:
        out_dir, prefix = detector.process(text, title, force_reprocess=force_reprocess)
    except Exception as exc:
        error_message = f"BookNLP processing failed: {type(exc).__name__}: {exc}"
        print(f"[CharacterDetection] {error_message}")
        fallback = DetectionOutput(
            lines=[{"speaker": "Narrator", "text": text.strip(), "is_quote": False}],
            character_order=["Narrator"],
            characters={},
        )
        payload = fallback.as_dict()
        payload["detection_error"] = error_message
        return payload

    characters_path = out_dir / f"{prefix}.characters.json"
    simple_characters_path = out_dir / f"{prefix}.characters_simple.json"
    entities_path = out_dir / f"{prefix}.entities"
    book_path = out_dir / f"{prefix}.book.txt"
    quotes_path = out_dir / f"{prefix}.quotes"

    characters = _load_characters(characters_path)
    characters.update(
        _load_quote_only_characters(
            simple_characters_path,
            quotes_path,
            characters.keys(),
        )
    )
    proper_mentions, part_mentions = _collect_entity_mentions(entities_path, characters.keys())

    display_names: Dict[str, str] = {}
    for cid, meta in characters.items():
        canonical = meta.get("canonical_name", "")
        display = _select_display_name(
            canonical,
            cid,
            proper_mentions.get(cid, Counter()),
            part_mentions.get(cid, Counter()),
        )
        if display and len(display.split()) >= 2:
            display_names[cid] = display

    alias_to_id = _build_alias_index(characters, proper_mentions, display_names)
    normalize = _normalize_speaker_factory(characters, display_names, alias_to_id)

    id_to_display: Dict[str, str] = {}
    for cid, meta in characters.items():
        display = display_names.get(cid)
        if not display:
            canonical = meta.get("canonical_name") or meta.get("normalized_name")
            if canonical:
                display = _smart_capitalize(str(canonical))
        if display and _is_valid_quote_speaker_label(display):
            id_to_display[cid] = display

    # Remove aliases that are likely location references rather than people.
    if id_to_display:
        id_to_display = {
            cid: name
            for cid, name in id_to_display.items()
            if not _looks_place_like_character_alias(name, text)
        }

    pov_speaker: Optional[str] = None
    if _is_valid_quote_speaker_label(pov_speaker_override):
        pov_speaker = str(pov_speaker_override)
    if first_person_narration:
        if not pov_speaker:
            pov_speaker = _infer_first_person_protagonist_name(text, id_to_display)
            if not _is_valid_quote_speaker_label(pov_speaker):
                pov_speaker = None

    tokens_path = out_dir / f"{prefix}.tokens"
    segments = _segment_text_using_quotes(text, tokens_path, quotes_path)

    rows: List[Dict[str, object]]
    parsed_order: List[str] = []

    if segments:
        rows = []
        pending_speaker_hints: deque[str] = deque()
        for idx, segment in enumerate(segments):
            segment_type = segment.get("type")
            text_piece = segment.get("text", "")

            if segment_type == "narration":
                if not _has_meaningful_text(text_piece):
                    continue

                # BookNLP can occasionally return narration spans that still include
                # quoted speech. Split those spans here to avoid merged narrator+dialogue rows.
                narration_pieces = _split_quote_segments(text_piece)
                if not narration_pieces:
                    narration_pieces = [{"type": "narration", "text": text_piece}]

                for piece_idx, piece in enumerate(narration_pieces):
                    piece_type = piece.get("type")
                    piece_text = piece.get("text", "")
                    if not _has_meaningful_text(piece_text):
                        continue
                    piece_text = _fix_contractions(piece_text)

                    if piece_type == "narration":
                        hints = _extract_speaker_hints(piece_text, alias_to_id, id_to_display, characters)
                        for prev_hint in hints["prev"]:
                            _assign_speaker_to_previous_quote(rows, prev_hint)
                        for next_hint in hints["next"]:
                            if next_hint not in {"Narrator", "Unknown"}:
                                pending_speaker_hints.append(next_hint)
                        rows.append({
                            "speaker": "Narrator",
                            "text": piece_text,
                            "is_quote": False,
                        })
                        continue

                    # Quote chunk embedded in a narration segment.
                    context_texts: List[str] = []
                    if piece_idx + 1 < len(narration_pieces) and narration_pieces[piece_idx + 1].get("type") == "narration":
                        context_texts.append(narration_pieces[piece_idx + 1].get("text", ""))
                    if piece_idx > 0 and narration_pieces[piece_idx - 1].get("type") == "narration":
                        context_texts.append(narration_pieces[piece_idx - 1].get("text", ""))
                    if idx + 1 < len(segments) and segments[idx + 1].get("type") == "narration":
                        context_texts.append(segments[idx + 1].get("text", ""))
                    if idx > 0 and segments[idx - 1].get("type") == "narration":
                        context_texts.append(segments[idx - 1].get("text", ""))

                    speaker_for_piece = _contextual_speaker(context_texts, alias_to_id, id_to_display, characters)
                    if not speaker_for_piece:
                        weighted_contexts: List[Tuple[str, float]] = []
                        for pos, ctx in enumerate(context_texts):
                            if not ctx:
                                continue
                            weighted_contexts.append((ctx, 1.0 / (pos + 1)))
                        for back, prev_row in enumerate(reversed(rows[-8:]), start=1):
                            prev_text = str(prev_row.get("text") or "")
                            if not prev_text:
                                continue
                            weighted_contexts.append((prev_text, 0.75 / back))
                        speaker_for_piece = _weighted_context_speaker(
                            weighted_contexts,
                            alias_to_id,
                            id_to_display,
                            characters,
                        )
                    if not speaker_for_piece and pending_speaker_hints:
                        speaker_for_piece = pending_speaker_hints.popleft()
                    if not speaker_for_piece:
                        speaker_for_piece = "Unknown"

                    if speaker_for_piece == "Unknown" and first_person_narration and _looks_first_person_quote(piece_text):
                        speaker_for_piece = pov_speaker if _is_valid_quote_speaker_label(pov_speaker) else "Narrator"

                    rows.append({
                        "speaker": speaker_for_piece,
                        "text": piece_text,
                        "is_quote": True,
                    })
                continue

            pieces = _split_quote_segments(text_piece)
            if not pieces:
                continue

            char_id = segment.get("char_id")
            base_speaker: Optional[str] = None
            mention = segment.get("mention")
            booknlp_quote_speaker: Optional[str] = None
            rejected_quote_only_id = False
            mention_speaker = None
            mention_is_inside_span = False
            char_id_text = str(char_id) if char_id is not None else None
            char_meta = characters.get(char_id_text, {}) if char_id_text else {}
            id_speaker = id_to_display.get(char_id_text) if char_id_text else None

            if isinstance(char_id, int) and char_id >= 0:
                base_speaker = id_speaker
                # BookNLP frequently uses char_id=0 for dominant POV speakers; that id
                # can be filtered from character JSON. In first-person chapters, map it
                # to Narrator only when quote content itself looks first-person.
                if not base_speaker and char_id == 0 and first_person_narration and _looks_first_person_quote(text_piece):
                    base_speaker = pov_speaker if _is_valid_quote_speaker_label(pov_speaker) else "Narrator"

            if char_meta.get("booknlp_quote_fallback"):
                if isinstance(mention, str):
                    mention_speaker = _resolve_narration_name_candidate(
                        mention,
                        alias_to_id,
                        id_to_display,
                        characters,
                    )
                mention_is_inside_span = bool(
                    isinstance(mention, str)
                    and _variant_matches_text(mention, text_piece.lower())
                )
                if not base_speaker or mention_speaker != base_speaker or mention_is_inside_span:
                    base_speaker = None
                    rejected_quote_only_id = True

            if not base_speaker:
                if isinstance(mention, str) and not rejected_quote_only_id:
                    base_speaker = normalize(mention)

            if not base_speaker:
                base_speaker = "Unknown"

            fallback_mention_is_reliable = (
                not char_meta.get("booknlp_quote_fallback")
                or (mention_speaker == base_speaker and not mention_is_inside_span)
            )
            if (
                isinstance(mention, str)
                and mention.strip()
                and base_speaker == id_speaker
                and fallback_mention_is_reliable
            ):
                booknlp_quote_speaker = base_speaker

            for piece_idx, piece in enumerate(pieces):
                piece_type = piece.get("type")
                piece_text = piece.get("text", "")
                if not _has_meaningful_text(piece_text):
                    continue
                piece_text = _fix_contractions(piece_text)

                if piece_type == "narration":
                    hints = _extract_speaker_hints(piece_text, alias_to_id, id_to_display, characters)
                    for prev_hint in hints["prev"]:
                        _assign_speaker_to_previous_quote(rows, prev_hint)
                    for next_hint in hints["next"]:
                        if next_hint not in {"Narrator", "Unknown"}:
                            pending_speaker_hints.append(next_hint)
                    rows.append({
                        "speaker": "Narrator",
                        "text": piece_text,
                        "is_quote": False,
                    })
                    continue

                context_texts: List[str] = []
                if piece_idx + 1 < len(pieces) and pieces[piece_idx + 1].get("type") == "narration":
                    context_texts.append(pieces[piece_idx + 1].get("text", ""))
                if piece_idx > 0 and pieces[piece_idx - 1].get("type") == "narration":
                    context_texts.append(pieces[piece_idx - 1].get("text", ""))
                if idx + 1 < len(segments) and segments[idx + 1].get("type") == "narration":
                    context_texts.append(segments[idx + 1].get("text", ""))
                if idx > 0 and segments[idx - 1].get("type") == "narration":
                    context_texts.append(segments[idx - 1].get("text", ""))

                context_speaker = _contextual_speaker(context_texts, alias_to_id, id_to_display, characters)
                if not context_speaker:
                    weighted_contexts: List[Tuple[str, float]] = []
                    for pos, ctx in enumerate(context_texts):
                        if not ctx:
                            continue
                        weighted_contexts.append((ctx, 1.0 / (pos + 1)))
                    for back, prev_row in enumerate(reversed(rows[-8:]), start=1):
                        prev_text = str(prev_row.get("text") or "")
                        if not prev_text:
                            continue
                        weighted_contexts.append((prev_text, 0.75 / back))
                    context_speaker = _weighted_context_speaker(
                        weighted_contexts,
                        alias_to_id,
                        id_to_display,
                        characters,
                    )
                speaker_for_piece = context_speaker
                if not speaker_for_piece and pending_speaker_hints:
                    speaker_for_piece = pending_speaker_hints.popleft()
                if not speaker_for_piece:
                    speaker_for_piece = base_speaker or "Unknown"

                # Guarded fallback for first-person POV novels:
                # unresolved quotes with strong first-person language default to Narrator.
                if speaker_for_piece == "Unknown" and first_person_narration and _looks_first_person_quote(piece_text):
                    speaker_for_piece = pov_speaker if _is_valid_quote_speaker_label(pov_speaker) else "Narrator"

                rows.append({
                    "speaker": speaker_for_piece,
                    "text": piece_text,
                    "is_quote": True,
                    "booknlp_quote_speaker": booknlp_quote_speaker,
                })

        rows = _merge_adjacent_narration(rows)
    else:
        rows, parsed_order = _parse_book_rows(book_path, normalize)

    rows = _split_mixed_quote_rows(rows, first_person_narration)
    rows = _split_mixed_narrator_rows(rows, first_person_narration)
    rows = _demote_heading_quotes(rows)
    rows = _demote_inline_scare_quotes(rows)
    rows = _map_narrator_quotes_to_pov(rows, first_person_narration, pov_speaker)
    rows = _apply_first_person_narration_cues(rows, first_person_narration, pov_speaker)
    rows = _resolve_unknown_from_neighbor_narration(rows)
    rows = _apply_vocative_self_mention_guard(rows)
    rows = _apply_turn_taking_heuristic(rows)
    rows = _apply_dialogue_block_alternation(rows)
    rows = _apply_quote_confidence_threshold(
        rows,
        alias_to_id,
        id_to_display,
        characters,
        adaptive_priors,
        first_person_narration,
        pov_speaker,
        global_character_priors,
        allowed_speakers,
    )
    rows = _apply_vocative_self_mention_guard(rows)
    rows = _rebalance_long_quote_streaks(rows)
    rows = _reevaluate_long_quote_blocks(
        rows,
        alias_to_id,
        id_to_display,
        characters,
        adaptive_priors,
        global_character_priors,
        allowed_speakers,
        pov_speaker,
    )
    rows = _rebalance_first_person_pov_runs(rows, pov_speaker)
    rows = _apply_turn_taking_heuristic(rows)
    rows = _apply_dialogue_block_alternation(rows)
    rows = _apply_explicit_previous_quote_cues(
        rows,
        alias_to_id,
        id_to_display,
        characters,
    )
    rows = _arbitrate_quote_speakers(rows)
    rows = _apply_vocative_self_mention_guard(rows)
    rows = _fuse_speaker_evidence(rows)
    rows = _sanitize_quote_speakers(rows, allowed_speakers)
    rows = _canonicalize_speaker_aliases(rows)
    _update_adaptive_priors(adaptive_key, rows)

    if max_lines and max_lines > 0:
        rows = rows[:max_lines]

    order: List[str] = []
    for row in rows:
        speaker = row.get("speaker")
        if not speaker or speaker in {"Narrator", "Unknown"}:
            continue
        if not _is_valid_quote_speaker_label(str(speaker)):
            continue
        if speaker not in order:
            order.append(speaker)

    if not segments:
        for speaker in parsed_order:
            if speaker in {"Narrator", "Unknown"}:
                continue
            if speaker not in order:
                order.append(speaker)

    if any(row.get("speaker") == "Narrator" for row in rows):
        order = ["Narrator", *order]

    # Preserve visible cast from full narration, not only attributed dialogue.
    # This keeps BookNLP-detected names available in the GUI even if they have no quote turns.
    coverage = _build_booknlp_character_coverage(rows, id_to_display, characters)
    for item in coverage:
        name = str(item.get("name") or "").strip()
        if not name or name in order:
            continue
        if not _is_valid_quote_speaker_label(name):
            continue
        quote_count = int(item.get("quote_count", 0) or 0)
        narration_mentions = int(item.get("narration_mentions", 0) or 0)
        mention_count = int(item.get("mention_count", 0) or 0)
        if quote_count > 0:
            continue
        if narration_mentions >= 1 and mention_count >= 1:
            order.append(name)

    characters_payload: Dict[str, Dict[str, object]] = {}
    for cid, name in id_to_display.items():
        if name in order:
            characters_payload[name] = characters.get(cid, {})

    result = DetectionOutput(
        lines=rows,
        character_order=order,
        characters=characters_payload,
    )
    payload = result.as_dict()
    payload["booknlp_character_debug"] = {
        "total_booknlp_characters": len(coverage),
        "characters": [
            {
                "name": item.get("name"),
                "mention_count": int(item.get("mention_count", 0) or 0),
                "quote_count": int(item.get("quote_count", 0) or 0),
                "narration_mentions": int(item.get("narration_mentions", 0) or 0),
                "in_character_order": bool(item.get("name") in payload.get("character_order", [])),
            }
            for item in coverage[:80]
        ],
    }
    unknown_diagnostics = _diagnose_unknown_quotes(rows, alias_to_id, id_to_display, characters)
    reason_counts: Dict[str, int] = Counter(d.get("reason", "unknown") for d in unknown_diagnostics)
    payload["unknown_diagnostics"] = unknown_diagnostics
    payload["unknown_diagnostics_summary"] = {
        "total_unknown_quotes": sum(1 for r in rows if r.get("speaker") == "Unknown" and r.get("is_quote")),
        "diagnosed": len(unknown_diagnostics),
        "reasons": dict(reason_counts),
        "confidence_threshold": SPEAKER_CONFIDENCE_MIN,
        "effective_thresholds": {
            "min": min((float(r.get("speaker_threshold", SPEAKER_CONFIDENCE_MIN)) for r in rows if r.get("is_quote")), default=float(SPEAKER_CONFIDENCE_MIN)),
            "max": max((float(r.get("speaker_threshold", SPEAKER_CONFIDENCE_MIN)) for r in rows if r.get("is_quote")), default=float(SPEAKER_CONFIDENCE_MIN)),
            "avg": round(sum(float(r.get("speaker_threshold", SPEAKER_CONFIDENCE_MIN)) for r in rows if r.get("is_quote")) / max(1, sum(1 for r in rows if r.get("is_quote"))), 3),
        },
        "adaptive_book_key": adaptive_key,
        "adaptive_prior_count": int(sum(_BOOK_ADAPTIVE_PRIORS.get(adaptive_key, Counter()).values())) if adaptive_key else 0,
    }
    payload["main_character_inference"] = _infer_main_character(
        rows,
        id_to_display=id_to_display,
        characters=characters,
        first_person_narration=first_person_narration,
    )
    if _is_valid_quote_speaker_label(pov_speaker):
        payload["pov_speaker"] = pov_speaker
    if first_person_narration:
        fallback_main = _infer_first_person_protagonist_name(text, id_to_display)
        if fallback_main and fallback_main not in {"Narrator", "Unknown"} and fallback_main not in payload["character_order"]:
            payload["character_order"].append(fallback_main)
    inferred_main = payload.get("main_character_inference", {}).get("name")
    if first_person_narration and isinstance(inferred_main, str) and inferred_main not in {"", "Narrator", "Unknown"}:
        if inferred_main not in payload["character_order"]:
            payload["character_order"].append(inferred_main)
    return payload


def attribute_dialogue(text: str, use_spacy: bool = False, **kwargs):
    result = run_attribution(text, **kwargs)
    lines = result.get("lines", [])
    characters = result.get("character_order", [])
    return lines, [c for c in characters if c != "Narrator"]


def normalize_speakers(results: List[Dict[str, object]], persons: Iterable[str], path: Path):
    mapping = {person: person for person in persons}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return mapping


def fix_contractions_in_saved_chapter(chapter_path: Path) -> None:
    """Fix split contractions in a saved chapter JSON file without changing attributions."""
    if not chapter_path.exists():
        raise FileNotFoundError(f"Chapter file not found: {chapter_path}")

    with chapter_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        # Assume it's a list of lines
        lines = data
    elif isinstance(data, dict):
        # Assume it's a dict with "lines"
        lines = data.get("lines", [])
    else:
        raise ValueError(f"Unexpected JSON structure in {chapter_path}")

    for line in lines:
        if isinstance(line, dict) and "text" in line:
            line["text"] = _fix_contractions(line["text"])

    # Also fix detection_raw if present
    if isinstance(data, list) and len(data) > 0 and isinstance(data[-1], dict) and "detection_raw" in data[-1]:
        for line in data[-1]["detection_raw"]["lines"]:
            if isinstance(line, dict) and "text" in line:
                line["text"] = _fix_contractions(line["text"])

    with chapter_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
