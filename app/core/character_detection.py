from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app.core.english_booknlp import EnglishBookNLP

# -----------------------------------------------------------------------------
# Constants & configuration
# -----------------------------------------------------------------------------

BOOKNLP_PIPELINE = "entity,quote,coref"
BOOKNLP_MODEL_DEFAULT = "english"
CACHE_ROOT = Path(__file__).resolve().parents[2] / ".polyvox_tmp" / "booknlp_cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

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
        verb_regex = rf"\b{verb_pattern}\b"

        pattern_verb_first = re.compile(
            rf"{verb_regex}(?:\s+|\s*,\s*)(?P<name>{NAME_PATTERN})(?=\b|[^A-Za-z])"
        )
        for match in pattern_verb_first.finditer(cleaned):
            candidate = match.group("name").strip()
            speaker = _resolve_display_from_alias(candidate, alias_to_id, id_to_display, characters)
            if not speaker:
                speaker = _fallback_speaker_label(candidate)
            if speaker and speaker not in prev_hints:
                prev_hints.append(speaker)

        pattern_name_first = re.compile(
            rf"(?P<name>{NAME_PATTERN})(?:\s*,)?\s+{verb_regex}"
        )
        for match in pattern_name_first.finditer(cleaned):
            candidate = match.group("name").strip()
            speaker = _resolve_display_from_alias(candidate, alias_to_id, id_to_display, characters)
            if not speaker:
                speaker = _fallback_speaker_label(candidate)
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
    return None


def _assign_speaker_to_previous_quote(rows: List[Dict[str, object]], speaker: Optional[str]) -> None:
    if not speaker or speaker in {"Narrator", "Unknown"}:
        return
    for row in reversed(rows):
        if not row.get("is_quote"):
            continue
        row["speaker"] = speaker
        return

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

    def process(self, text: str, chapter_title: Optional[str]) -> Tuple[Path, str]:
        slug = _safe_slug(chapter_title)
        digest = _hash_text(text)[:12]
        prefix = f"{slug}_{digest}"
        out_dir = CACHE_ROOT / prefix
        book_path = out_dir / f"{prefix}.book.txt"

        if not book_path.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
            input_path = out_dir / f"{prefix}.txt"
            input_path.write_text(text, encoding="utf-8")
            pipeline = self._ensure_pipeline()
            pipeline.process(str(input_path), str(out_dir), prefix)

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
        return fallback

    return _normalize


def run_attribution(
    text: str,
    *,
    title: Optional[str] = None,
    model: str = BOOKNLP_MODEL_DEFAULT,
    max_lines: Optional[int] = None,
) -> Dict[str, object]:
    detector = _get_detector(model)

    try:
        out_dir, prefix = detector.process(text, title)
    except Exception:
        fallback = DetectionOutput(
            lines=[{"speaker": "Narrator", "text": text.strip(), "is_quote": False}],
            character_order=["Narrator"],
            characters={},
        )
        return fallback.as_dict()

    characters_path = out_dir / f"{prefix}.characters.json"
    entities_path = out_dir / f"{prefix}.entities"
    book_path = out_dir / f"{prefix}.book.txt"

    characters = _load_characters(characters_path)
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
        if display:
            id_to_display[cid] = display

    tokens_path = out_dir / f"{prefix}.tokens"
    quotes_path = out_dir / f"{prefix}.quotes"

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
                hints = _extract_speaker_hints(text_piece, alias_to_id, id_to_display, characters)
                for prev_hint in hints["prev"]:
                    _assign_speaker_to_previous_quote(rows, prev_hint)
                rows.append({
                    "speaker": "Narrator",
                    "text": text_piece,
                    "is_quote": False,
                })
                continue

            pieces = _split_quote_segments(text_piece)
            if not pieces:
                continue

            char_id = segment.get("char_id")
            base_speaker: Optional[str] = None
            if isinstance(char_id, int) and char_id >= 0:
                base_speaker = id_to_display.get(str(char_id))

            if not base_speaker:
                mention = segment.get("mention")
                if isinstance(mention, str):
                    base_speaker = normalize(mention)

            if not base_speaker:
                base_speaker = "Unknown"

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
                speaker_for_piece = context_speaker
                if not speaker_for_piece and pending_speaker_hints:
                    speaker_for_piece = pending_speaker_hints.popleft()
                if not speaker_for_piece:
                    speaker_for_piece = base_speaker or "Unknown"

                rows.append({
                    "speaker": speaker_for_piece,
                    "text": piece_text,
                    "is_quote": True,
                })

        rows = _merge_adjacent_narration(rows)
    else:
        rows, parsed_order = _parse_book_rows(book_path, normalize)
    if max_lines and max_lines > 0:
        rows = rows[:max_lines]

    order: List[str] = []
    for row in rows:
        speaker = row.get("speaker")
        if not speaker or speaker in {"Narrator", "Unknown"}:
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

    characters_payload: Dict[str, Dict[str, object]] = {}
    for cid, name in id_to_display.items():
        if name in order:
            characters_payload[name] = characters.get(cid, {})

    result = DetectionOutput(
        lines=rows,
        character_order=order,
        characters=characters_payload,
    )
    return result.as_dict()


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
