"""
book_processor# --- Heuristics / patterns ---
QUOTE_PAT = r'(".*?"|".*?"|'.*?'|\'[^\']+\')'
ATTRIB_VERBS = r"(said|asked|replied|whispered|shouted|muttered|cried|calle                                               # Extract the speaker name from attribution for continuation
                        # Pattern: "said Name" or ", said Name"
                        if attrib_match:
                            attrib_speaker = attrib_match.group(2)  # Captured name from ATTRIB_TAIL pattern
                            # Store for next iteration to attribute continuation quotes
                            last_attribution_speaker = attrib_speaker
                            # DEBUG
                                print(f"  from: {trailing_clean[:60]}") the speaker name from attribution for continuation
                        # Pattern: "said Name" or ", said Name"
                        if attrib_match:
                            attrib_speaker = attrib_match.group(2)  # Captured name from ATTRIB_TAIL pattern
                            # Store for next iteration to attribute continuation quotes
                            last_attribution_speaker = attrib_speaker
                            # DEBUG
                                print(f"  from: {trailing_clean[:60]}")
                    elif not _attrib_only(trailing):
                        # It's actual content, not attribution
                        results.append({"speaker": speaker, "text": trailing, "is_quote": False})
                        emitted_any = Truesed|breathed|growled|moaned|went\s+on|told|explained|snapped|laughed|reminded|queried|continued|responded|added|insisted|agreed|noted|remarked|observed|demanded|protested|announced|declared|yelled|murmured)"
# Allow optional adverbial phrases after the name: "said Hatfield with a grin." or "said Hatfield softly."
ATTRIB_TAIL = re.compile(rf'^\s*,?\s*(?P<verb>{ATTRIB_VERBS})\s+(?P<name>[A-Z][\w\'\-]+)(?:\s+[\w\s]+)?\.?\s*$', re.IGNORECASE)
ATTRIB_HEAD = re.compile(rf'^\s*([A-Z][\w\'\-]+)\s+{ATTRIB_VERBS}\b', re.IGNORECASE)
# Pattern to detect attribution starting with quotes: '"he said' or '"she asked' (allow pronouns/short words before verb)
ATTRIB_QUOTE_PREFIX = re.compile(rf'^["\u201c\u201d\'\u2018\u2019]\s*(?:[a-z]+\s+)?{ATTRIB_VERBS}\b', re.IGNORECASE)--------------
Standalone processor for extracting characters, quotes, and narrator prose
from raw book text. This replaces the heavy /booknlp dependency with a
simplified structured output.

Outputs a list of dicts like:
[
    {"speaker": "Narrator", "text": "It was a quiet evening in the city."},
    {"speaker": "Alice", "text": "Did you hear that noise?"},
    {"speaker": "Bob", "text": "Probably just the wind, Alice."}
]
"""

import re
from typing import List, Dict

# --- Heuristics / patterns ---
QUOTE_PAT = r'(".*?"|“.*?”|‘.*?’|\'[^\']+\')'
ATTRIB_VERBS = r"(said|asked|replied|whispered|shouted|muttered|cried|called|answered|hissed|breathed|growled|moaned|went\s+on|told|explained|snapped|laughed|reminded|queried|continued|responded|added|insisted|agreed|noted|remarked|observed|demanded|protested|announced|declared|yelled|murmured)"
ATTRIB_TAIL = re.compile(rf'^\s*,?\s*(?P<verb>{ATTRIB_VERBS})\s+(?P<name>[A-Z][\w\'\-]+)(?:\s+[\w\s]+)?\.?\s*$', re.IGNORECASE)
ATTRIB_HEAD = re.compile(rf'^\s*([A-Z][\w\'\-]+)\s+{ATTRIB_VERBS}\b', re.IGNORECASE)
# Pattern to detect attribution starting with quotes: '"he said' or '"she asked' (allow pronouns/short words before verb)
ATTRIB_QUOTE_PREFIX = re.compile(rf'^["\u201c\u201d\'\u2018\u2019]\s*(?:[a-z]+\s+)?{ATTRIB_VERBS}\b', re.IGNORECASE)
BAN_SPEAKERS = {
    "unknown", "unk", "narration", "voice", "speaker",
    "we", "they", "them", "you", "me", "us",
    "guys", "girls", "boys", "people", "folks",
    "man", "woman", "men", "women",
    "the older man", "older man", "old man", "young man", "the young man",
    "god", "lord", "jesus", "christ"
}


def parse_booktxt(path: str) -> List[Dict[str, str]]:
    def parse_booktxt_from_text(text: str) -> list:
        # Improved logic: always emit quoted text as a single row, split glued quote+attribution, never glue narration to character lines
        results = []
        # Regex to match: "quote" [optional attribution]
        quote_attrib_pat = re.compile(r'^(?P<quote>["\u201c\u201d][^"\u201c\u201d]+["\u201c\u201d])\s*(?P<attrib>(,?\s*(said|asked|replied|whispered|shouted|muttered|cried|called|answered|hissed|breathed|growled|moaned|went\s+on|told|explained|snapped|laughed|reminded|queried|continued|responded|added|insisted|agreed|noted|remarked|observed|demanded|protested|announced|declared|yelled|murmured)\s+[A-Z][\w\'\-]+(?:\s+[\w\s]+)?\.?))?$', re.IGNORECASE)
        m = quote_attrib_pat.match(text.strip())
        if m:
            quote = m.group('quote').strip()
            attrib = m.group('attrib')
            speaker = "Unknown"
            if attrib:
                name_match = re.search(r'(said|asked|replied|whispered|shouted|muttered|cried|called|answered|hissed|breathed|growled|moaned|went\s+on|told|explained|snapped|laughed|reminded|queried|continued|responded|added|insisted|agreed|noted|remarked|observed|demanded|protested|announced|declared|yelled|murmured)\s+([A-Z][\w\'\-]+)', attrib)
                if name_match:
                    speaker = normalize_name(name_match.group(2))
            results.append({"speaker": speaker, "text": quote, "is_quote": True})
            if attrib:
                results.append({"speaker": "Narrator", "text": attrib.strip(), "is_quote": False})
            return results
        # Fallback to previous logic
        quotes = list(re.finditer(QUOTE_PAT, text))
        if quotes:
            # If multiple quotes, emit each as a single row, never split into sentences
            for q in quotes:
                qtxt = q.group(0).strip()
                results.append({"speaker": "Unknown", "text": qtxt, "is_quote": True})
            # If trailing text after last quote, emit as Narrator
            trailing = text[quotes[-1].end():].strip()
            if trailing:
                trailing_clean = trailing.lstrip("\"\u201c\u201d\u2018\u2019")
                attrib_match = ATTRIB_TAIL.match(trailing_clean)
                # DEBUG: Log attribution detection
                if attrib_match or _attrib_only(trailing_clean):
                    results.append({"speaker": "Narrator", "text": trailing_clean, "is_quote": False})
                else:
                    results.extend(parse_booktxt_from_text(trailing))
        else:
            results.append({"speaker": "Narrator", "text": text, "is_quote": False})
        return results
    """
    Parse a .book.txt file produced by EnglishBookNLP into structured JSON.

    Example line in .book.txt:
      [Narrator] It was a quiet evening in the city. [/]
      [Narrator] "Did you hear that noise?" asked Alice. [/]
      [Narrator] “Probably just the wind, Alice,” whispered Bob. [/]

    Returns:
      list of {"speaker": str, "text": str}
    Returns:
      list of {"speaker": str, "text": str, "is_quote": bool}
    """
    results: List[Dict[str, str]] = []
    last_attribution_speaker = None
    pending_attribution_speaker = None

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            # DEBUG: Trace attribution logic for every line
            is_quote_line_debug = bool(re.match(r'^\s*["\u201c]', line))
            print(f"[DEBUG] LINE: pending={pending_attribution_speaker}, last={last_attribution_speaker}, is_quote_line={is_quote_line_debug}, text={repr(line)}")
            if not line:
                continue

            # Only assign pending attribution for non-empty quote lines
            if pending_attribution_speaker and bool(re.match(r'^\s*["\u201c]', line)):
                last_attribution_speaker = pending_attribution_speaker
                pending_attribution_speaker = None

            m = re.match(r"^\[(.*?)\](.*)\[/\]$", line)
            if not m:
                last_attribution_speaker = None
                continue

            raw_speaker = m.group(1).strip()
            speaker = normalize_name(raw_speaker)
            text = (m.group(2) or "").strip()
            is_quote_line = bool(re.match(r'^\s*["\u201c]', text))

            # --- APPLY CONTINUATION SPEAKER ---
            if last_attribution_speaker and is_quote_line:
                speaker = last_attribution_speaker
                last_attribution_speaker = None


            if not text:
                last_attribution_speaker = None  # Clear on empty lines
                continue
            
            # Remember if this was originally a non-Narrator speaker (i.e., a quote from BookNLP's perspective)
            # even if we normalize it to Narrator due to being descriptive
            was_originally_quote_speaker = raw_speaker.lower() not in {'narrator', 'the narrator'}

            # Demote junk/collectives to Narrator
            if speaker.lower() in BAN_SPEAKERS:
                speaker = "Narrator"

            # If the line is narrator but contains a clear quoted span + attribution,
            # promote the quoted text to the attributed speaker
            emitted_any = False
            
            # SPECIAL CASE: Text that starts with quote + attribution verb (e.g., '"he went on in a monotone')
            # These are attribution fragments, NOT dialogue. Emit as Narrator, skip quote extraction.
            # Strip the leading quote mark since it's not part of actual dialogue.
            # LOCK the speaker so pipeline doesn't override it.
            # 
            # IMPORTANT: Only treat as attribution fragment if it's SHORT (< 8 words).
            # Otherwise it might be actual dialogue that happens to start with "She said..." or "He asked..."
            # Example: `" She said because she was past 30..."` is NOT an attribution, it's dialogue.
            if ATTRIB_QUOTE_PREFIX.match(text):
                word_count = len(text.split())
                if word_count < 8:  # Short text, likely attribution fragment
                    # Strip leading quote marks (ASCII and Unicode variants)
                    cleaned_text = text.lstrip('"\u201c\u201d\'\u2018\u2019').strip()
                    results.append({
                        "speaker": "Narrator",
                        "text": cleaned_text,
                        "is_quote": False,
                        "_lock_speaker": True,
                        "_lock_reason": "attribution_fragment",
                        "_is_attribution": True
                    })
                    continue
                # Else: Long text, treat as normal quote even if it starts with attribution verb

            # 1) Pull quoted chunks (can be multiple per line)
            quotes = list(re.finditer(QUOTE_PAT, text))
            if quotes:
                cursor = 0
                for q in quotes:
                    before = text[cursor:q.start()].strip()
                    qtxt = q.group(0).strip()
                    after = text[q.end():].strip()

                    # Try to infer a speaker from "..., said Name." pattern in 'after'
                    inferred = None
                    m_tail = ATTRIB_TAIL.match(after)
                    if m_tail:
                        inferred = normalize_name(m_tail.group(2))

                    # Or from "Name said ..." at the start of 'before'
                    if not inferred:
                        m_head = ATTRIB_HEAD.match(before)
                        if m_head:
                            inferred = normalize_name(m_head.group(1))

                    # If we inferred a junk/collective, ignore
                    if inferred and inferred.lower() in BAN_SPEAKERS:
                        inferred = None

                    # Emit 'before' (narrative) if meaningful
                    if before and not _attrib_only(before):
                        # Recursively split glued content
                        for row in parse_booktxt_from_text(before):
                            results.append(row)
                        emitted_any = True

                    # Emit the quoted speech — prefer inferred speaker if present
                    if qtxt:
                        results.append({"speaker": inferred or speaker, "text": qtxt, "is_quote": True})
                        emitted_any = True

                    # Advance cursor past this quote; keep 'after' for next loop
                    cursor = q.end()
                # If there is trailing text after the last quote, check for glued attribution or narration/quote and split
                trailing = text[cursor:].strip()
                if trailing:
                    # DEBUG: Log attribution handling
                    # Recursively split glued content
                    for row in parse_booktxt_from_text(trailing):
                        results.append(row)
                    emitted_any = True

            # 2) No quotes → normal emit (but strip pure attribution fragments like "said Bob")
            if not quotes:
                if not _attrib_only(text):
                    # Check for trailing attribution even without matched quotes
                    # e.g., 'Some text" said Name.' where the opening quote is missing/on previous line
                    text_to_emit = text
                    
                    # Look for pattern: text ending with '" verb Name.' or '" Name verb.'
                    # Try splitting on various quote marks (ASCII and Unicode)
                    split_found = False
                    for quote_char in ['"', '\u201d', '\u201c']:  # ASCII, smart close, smart open
                        if quote_char in text and text.rstrip().endswith('.'):
                            parts = text.rsplit(quote_char, 1)
                            if len(parts) == 2:
                                after_quote = parts[1].strip()
                                # Check if it's attribution
                                attrib_match = ATTRIB_TAIL.match(after_quote)
                                if attrib_match or _attrib_only(after_quote):
                                    # Split the text: main part vs attribution
                                    text_to_emit = parts[0].strip()
                                    # Emit the attribution separately as Narrator
                                    results.append({"speaker": "Narrator", "text": after_quote, "is_quote": False})
                                    emitted_any = True
                                    split_found = True
                                    
                                    # Extract speaker name for continuation
                                    if attrib_match:
                                        last_attribution_speaker = attrib_match.group(1)
                                    break
                    
                    # Check if this is Narrator and starts with a quote mark followed by attribution verb
                    is_attrib = speaker == "Narrator" and ATTRIB_QUOTE_PREFIX.match(text_to_emit)
                    
                    # IMPORTANT: If speaker is not "Narrator", it's ALWAYS a quote (even without quote marks - it's a quote continuation from BookNLP)
                    # Only Narrator rows can be non-quote (narration/attribution)
                    is_quote_row = (speaker != "Narrator") and not is_attrib
                    
                    results.append({"speaker": speaker, "text": text_to_emit, "is_quote": is_quote_row})
                    emitted_any = True

            # Fallback: if nothing emitted (edge cases), keep the original
            if not emitted_any:
                # IMPORTANT: If speaker is not "Narrator", it's ALWAYS a quote (even without quote marks - it's a quote continuation from BookNLP)
                # Only Narrator rows can be non-quote (narration/attribution)
                is_quote = (speaker != "Narrator")
                
                # Normalize Unknowna/Unknownb to Unknown
                norm_speaker = speaker
                if isinstance(norm_speaker, str) and norm_speaker.lower().startswith("unknown"):
                    norm_speaker = "Unknown"
                results.append({"speaker": norm_speaker, "text": text, "is_quote": is_quote})

            # --- SET CONTINUATION SPEAKER FOR NEXT LINE ---
            # If this line is NOT a quote and is a pure attribution, emit as Narrator and DO NOT set continuation speaker
            trailing_clean = text.strip().lstrip("\"\u201c\u201d\u2018\u2019")
            attrib_match = ATTRIB_TAIL.match(trailing_clean)
            if attrib_match and not is_quote_line:
                print(f"[DEBUG] Attribution line treated as Narrator, no continuation speaker set.")
                print(f"  from attribution: {trailing_clean[:60]}")

    # DISABLED: This aggressive merge was causing problems where embedded dialogue
    # from other speakers (e.g., "asked King") gets merged into the wrong speaker's row.
    # Character_detection has smarter merge logic that respects embedded attribution.
    # Just return the parsed results as-is.
    # Deduplicate consecutive identical Unknown quotes
    deduped_results = []
    prev_row = None
    for row in results:
        norm_speaker = row["speaker"]
        if isinstance(norm_speaker, str) and norm_speaker.lower().startswith("unknown"):
            norm_speaker = "Unknown"
            row = dict(row)
            row["speaker"] = norm_speaker
        if prev_row and row["speaker"] == prev_row["speaker"] == "Unknown" and row["is_quote"] and prev_row["is_quote"] and row["text"] == prev_row["text"]:
            continue  # skip duplicate
        # Prevent narration from being glued to character lines
        if prev_row and prev_row["speaker"] != "Narrator" and row["speaker"] == "Narrator" and prev_row["is_quote"]:
            # Hard stop: do not merge, always emit as separate rows
            pass
        deduped_results.append(row)
        prev_row = row
    return deduped_results


def _attrib_only(text: str) -> bool:
    """
    True iff a fragment is just an attribution like "said Bob" / "asked Alice".
    Used to avoid creating empty pseudo-utterances.
    """
    t = text.strip()
    if not t:
        return True
    # Patterns like: ", said Bob." or "Bob said." (with no other content)
    if ATTRIB_TAIL.match(t):
        return True
    if ATTRIB_HEAD.match(t) and not re.search(QUOTE_PAT, t):
        # Head attribution with no actual quote content
        # e.g., "Bob said." (no quotes)
        tail = ATTRIB_TAIL.match(t)
        return True
    # Single very short tokens (not typical prose)
    if len(t.split()) == 1 and not re.search(QUOTE_PAT, t):
        return True
    return False


def normalize_name(name: str) -> str:
    """
    Normalize speaker names:
      - Collapse case (title case for characters, fixed "Narrator")
      - Drop placeholder values like UNKNOWN
      - Strip generic/collective nouns
      - Detect descriptive phrases (>4 words or contains articles/prepositions)
    """
    import re
    
    if not name:
        return "Unknown"

    # Convert CamelCase to spaces (e.g., "APoliceDispatcher" → "A Police Dispatcher")
    # Insert space before uppercase letters that follow lowercase letters
    name_with_spaces = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    
    lowered = name_with_spaces.lower().strip()
    if lowered in {"narrator", "the narrator"}:
        return "Narrator"
    if lowered in {"unknown", "unk"}:
        return "Unknown"

    if lowered in BAN_SPEAKERS:
        return "Narrator"
    
    # Detect descriptive phrases that BookNLP incorrectly marked as speakers
    # Examples: "a police dispatcher in the justice center", "the guard behind him"
    # But NOT simple names like "The Guard", "The Doctor", etc.
    words = lowered.split()
    
    # Generic plural groups are not character names
    generic_plurals = {'the girls', 'the boys', 'the men', 'the women', 'the children', 
                      'the people', 'the soldiers', 'the officers'}
    if lowered in generic_plurals:
        return "Unknown"
    
    # If name is very long (>4 words), it's likely a description
    if len(words) > 4:
        return "Unknown"
    
    # Check for prepositions (strong indicator of description, not a name)
    prepositions = {'in', 'at', 'on', 'behind', 'beside', 'with', 'of', 'from', 'under', 'over'}
    if any(word in prepositions for word in words):
        return "Unknown"
    
    # Check for lowercase articles (a, an) - these are always descriptive
    # "a police dispatcher", "an officer", etc.
    if words[0] in {'a', 'an'}:
        return "Unknown"

    # Title-case names, preserve multi-word names
    return " ".join([w.capitalize() for w in lowered.split()])


def merge_quote_spans(rows: List[Dict[str, str]], quotes_file_path: str) -> List[Dict[str, str]]:
    """
    Merge consecutive quote rows that belong to the same quote span according to BookNLP.
    
    BookNLP's .quotes file contains the true quote boundaries. When SpaCy splits a 
    multi-sentence quote, we need to merge those sentences back together to preserve
    quote integrity for TTS.
    
    Args:
        rows: List of row dicts from parse_booktxt
        quotes_file_path: Path to BookNLP's .quotes file
    
    Returns:
        List of rows with multi-sentence quotes merged into single rows
    """
    import os
    if not os.path.exists(quotes_file_path):
        # No quotes file, return rows as-is
        return rows
    
    try:
        # Read BookNLP's quote boundaries and speaker assignments
        quote_spans = []
        with open(quotes_file_path, 'r', encoding='utf-8') as f:
            f.readline()  # skip header
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    quote_start = int(parts[0])
                    quote_end = int(parts[1])
                    mention_phrase = parts[4]
                    char_id = parts[5]
                    quote_text = parts[6] if len(parts) > 6 else ""
                    quote_spans.append({
                        'start': quote_start,
                        'end': quote_end,
                        'speaker': normalize_name(mention_phrase) if mention_phrase else "Unknown",
                        'char_id': char_id,
                        'text': quote_text.strip()
                    })
        if not quote_spans:
            return rows
        # Build a mapping of quote texts for fast lookup
        quote_texts = set(span['text'] for span in quote_spans)
        quote_map = {span['text']: span for span in quote_spans}
        merged = []
        for row in rows:
            # If this row is a quote and matches a BookNLP quote span, use BookNLP speaker
            if row.get('is_quote') and row.get('text') in quote_texts:
                span = quote_map[row.get('text')]
                merged.append({
                    'speaker': span['speaker'],
                    'text': span['text'],
                    'is_quote': True
                })
            else:
                # Otherwise, keep the original row (narration, unmatched quote, etc.)
                merged.append(row)
        return merged
    except Exception as e:
        print(f"[merge_quote_spans] Error: {e}")
        return rows


def split_embedded_quotes_in_narration(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Split narrator rows that contain embedded indirect quotes.
    Example: "Hatfield went on. She said it was time for her first divorce."
    Should split into two narrator rows:
      1. "Hatfield went on."
      2. "She said it was time for her first divorce."
    
    This prevents attribution text from being merged with embedded quote content.
    """
    result = []
    
    for row in rows:
        speaker = (row.get('speaker') or '').strip()
        is_quote = row.get('is_quote')
        
        # Normalize is_quote to boolean
        if isinstance(is_quote, str):
            is_quote_bool = is_quote == 'True'
        else:
            is_quote_bool = bool(is_quote)
        
        # Only process narrator rows that aren't quotes
        if speaker.lower() != 'narrator' or is_quote_bool:
            result.append(row)
            continue
        
        text = row.get('text', '').strip()
        if not text:
            result.append(row)
            continue
        
        # Pattern: Attribution + indirect quote
        # e.g., "Hatfield went on. She said because..."
        #       "asked Ekstrom. It was a rhetorical question."
        # Split on sentence boundaries when we detect "X said/asked/replied..."
        import re
        
        # Find patterns like: ". She said" or ". He asked" or ". They told"
        split_pattern = r'(\.\s+(?:She|He|They|It)\s+(?:said|asked|replied|told|answered|explained|continued|added))'
        
        matches = list(re.finditer(split_pattern, text, re.IGNORECASE))
        
        if not matches:
            result.append(row)
            continue
        
        # Split the text
        parts = []
        last_end = 0
        
        for match in matches:
            # Include the period in the first part
            split_pos = match.start() + 1  # After the period
            if last_end < split_pos:
                part_text = text[last_end:split_pos].strip()
                if part_text:
                    parts.append(part_text)
            last_end = split_pos
        
        # Add remaining text
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                parts.append(remaining)
        
        # Create separate rows for each part
        # Mark parts after the first as "__EMBEDDED_QUOTE__" temporarily
        # so they won't be merged back together by merge_narrator_blocks
        for idx, part in enumerate(parts):
            result.append({
                'speaker': 'Narrator' if idx == 0 else '__EMBEDDED_QUOTE__',
                'is_quote': False,
                'text': part
            })
    
    return result


def merge_narrator_blocks(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Merge consecutive Narrator rows (is_quote='False') into single blocks.
    This consolidates all narration and attribution for the narrator voice in TTS.
    
    Only merges rows that are:
    - speaker: 'Narrator' (case-insensitive)
    - is_quote: 'False'
    - Consecutive (no quotes in between)
    
    Preserves quote blocks completely - they remain separate and atomic.
    """
    if not rows:
        return rows
    
    merged = []
    narrator_buffer = None
    
    for row in rows:
        speaker = (row.get('speaker') or '').strip()
        is_quote = row.get('is_quote')  # Can be True (bool) or 'True' (string)
        
        # Normalize is_quote to boolean
        if isinstance(is_quote, str):
            is_quote_bool = is_quote == 'True'
        else:
            is_quote_bool = bool(is_quote)
        
        # If this is a narrator row (not a quote), add to buffer
        if speaker.lower() == 'narrator' and not is_quote_bool:
            if narrator_buffer is None:
                # Start new narrator buffer
                narrator_buffer = {
                    'speaker': 'Narrator',
                    'is_quote': False,
                    'text': row.get('text', '')
                }
            else:
                # Append to existing narrator buffer with space separation
                narrator_buffer['text'] += ' ' + row.get('text', '')
        else:
            # This is a quote or non-narrator - flush narrator buffer if exists
            if narrator_buffer:
                merged.append(narrator_buffer)
                narrator_buffer = None
            # Add the quote row
            merged.append(row)
    
    # Flush any remaining narrator buffer
    if narrator_buffer:
        merged.append(narrator_buffer)
    
    return merged


def run_book_processor(booktxt_path: str) -> List[Dict[str, str]]:
    """
    Main entry point. Given a .book.txt file path, parse and return structured JSON.
    Also merges multi-sentence quotes using BookNLP's .quotes file for quote integrity.
    Also merges consecutive narrator blocks for consolidated narrator voice in TTS.
    """
    import os
    try:
        # Prefer reconstructing rows strictly from BookNLP .quotes + .book.plain.txt
        # so each quote span is atomic and flagged is_quote=True end-to-end.
        base_dir = os.path.dirname(booktxt_path)
        prefix = os.path.basename(booktxt_path).replace('.book.txt', '')
        quotes_path = os.path.join(base_dir, f"{prefix}.quotes")
        plain_path = os.path.join(base_dir, f"{prefix}.book.plain.txt")

        def _normalize_name(n: str) -> str:
            try:
                base = (n or '').strip()
                if not base:
                    return 'Unknown'
                # If mention is all lower or a simple pronoun/determiner, treat as Unknown
                low = base.lower()
                if low == base:
                    return 'Unknown'
                if low in {'he','she','they','him','her','them','his','hers','their','thy','the','a','an','it'}:
                    return 'Unknown'
                return normalize_name(base)
            except Exception:
                return (n or '').strip() or 'Unknown'

        def _build_hard_rows_from_quotes(qpath: str, plain_path: str, tokens_path: str | None) -> List[Dict[str, str]]:
            import csv
            # Read full document plain text once
            try:
                with open(plain_path, 'r', encoding='utf-8', errors='replace') as f:
                    doc_text = f.read()
            except Exception:
                return []

            # Optional: load characters mapping to prefer canonical names from char_id
            char_id_to_name: dict[int, str] = {}
            try:
                base = os.path.dirname(qpath)
                pref = os.path.basename(qpath).replace('.quotes', '')
                cands = [
                    os.path.join(base, f"{pref}.characters.json"),
                    os.path.join(base, f"{pref}.characters_simple.json"),
                ]
                import json as _json
                for cc in cands:
                    if os.path.exists(cc):
                        with open(cc, 'r', encoding='utf-8', errors='replace') as cf:
                            cdata = _json.load(cf)
                        # Try both schemas
                        chars = cdata.get('characters') or []
                        for c in chars:
                            cid = c.get('id', c.get('char_id'))
                            try:
                                cid = int(cid)
                            except Exception:
                                continue
                            name = (
                                c.get('canonical_name')
                                or c.get('normalized_name')
                                or c.get('name')
                            )
                            if name:
                                char_id_to_name[cid] = name
                        break
            except Exception:
                char_id_to_name = {}

            # Optional: token_id -> (char_begin, char_end)
            tok2char = {}
            if tokens_path and os.path.exists(tokens_path):
                try:
                    with open(tokens_path, 'r', encoding='utf-8', errors='replace') as tf:
                        header = None
                        for line in tf:
                            line = line.rstrip('\n')
                            if not line:
                                continue
                            parts = line.split('\t')
                            if header is None:
                                header = [c.strip().lower() for c in parts]
                                continue
                            row = {header[i]: parts[i] for i in range(min(len(header), len(parts)))}
                            try:
                                # token id within document (support various header names)
                                tid_s = (
                                    row.get('token_id')
                                    or row.get('id')
                                    or row.get('token_id_within_document')
                                    or row.get('tokenid')
                                )
                                cb_s = (
                                    row.get('char_begin')
                                    or row.get('char_start')
                                    or row.get('begin')
                                    or row.get('byte_onset')
                                )
                                ce_s = (
                                    row.get('char_end')
                                    or row.get('char_stop')
                                    or row.get('end')
                                    or row.get('byte_offset')
                                )
                                tid = int(tid_s)
                                cb = int(cb_s)
                                ce = int(ce_s)
                            except Exception:
                                continue
                            tok2char[tid] = (cb, ce)
                except Exception:
                    tok2char = {}

            # Helpers for text normalization and glyph expansion
            def _strip_outer_quotes(s: str) -> str:
                s = (s or '').strip()
                if not s:
                    return s
                pairs = {('“', '”'), ('"', '"'), ('«', '»')}
                for lo, hi in pairs:
                    if s.startswith(lo) and s.endswith(hi):
                        return s[len(lo):-len(hi)]
                if (s.startswith("'") and s.endswith("'")):
                    return s[1:-1]
                return s

            def _norm_for_match(s: str) -> str:
                """Normalize quote text so BookNLP token spacing matches document spans."""
                import re as _re

                text = (s or '')
                text = text.replace('\u2019', "'").replace('\u2018', "'")
                text = text.replace('\u201c', '"').replace('\u201d', '"')
                text = _strip_outer_quotes(text)
                # Some BookNLP rows are missing closing quotes; trim any stray edges
                text = text.lstrip('"').rstrip('"')
                # Collapse any run of whitespace to a single space so newlines align
                text = _re.sub(r"\s+", " ", text).strip()
                # BookNLP tokenization often inserts spaces before punctuation ("word ."),
                # which does not appear in the raw document. Remove those so sequences like
                # "That was last summer ." match "That was last summer." exactly.
                text = _re.sub(r"\s+([.,!?;:])", r"\1", text)
                return text

            def _build_fuzzy_pattern(raw: str, collapse_space: str = r'\s*') -> str:
                """Build a regex that tolerates curly quotes/apostrophes and flexible spacing."""
                import re as _re
                text = (raw or '')
                text = text.replace('\u2019', "'").replace('\u2018', "'")
                text = text.replace('\u201c', '"').replace('\u201d', '"')
                pat = _re.escape(text)
                # Allow variable whitespace between tokens
                pat = pat.replace(_re.escape(' '), collapse_space)
                # Let straight apostrophes match curly variants as well
                pat = pat.replace("'", "[’']")
                # Allow straight double-quotes to match smart quotes too
                pat = pat.replace('\\"', '["“”]')
                return pat

            def _expand_glyphs(doc: str, start: int, end: int) -> tuple[int, int]:
                # Expand [start,end) to include surrounding opening/closing quote glyphs with whitespace in-between
                OPEN = {"\u201c", '"', '\u00ab'}  # “, ", «
                CLOSE = {"\u201d", '"', '\u00bb'}  # ”, ", »
                # Look left for opening glyph
                li = start - 1
                while li >= 0 and doc[li].isspace():
                    li -= 1
                if li >= 0 and doc[li] in OPEN:
                    start = li
                # Look right for closing glyph
                ri = end
                nd = len(doc)
                while ri < nd and doc[ri].isspace():
                    ri += 1
                if ri < nd and doc[ri] in CLOSE:
                    end = ri + 1
                return start, end

            import difflib
            import re as _re

            # Pre-split the BookNLP quotes file into individual quote segments so that
            # multi-quote rows ("A?" "B...") can be aligned one-by-one with the
            # document text.
            RX_SEGMENT = _re.compile(r'(?:[\u201c"])(?:.*?)(?:[\u201d"])', _re.S)
            quote_segments = []
            with open(qpath, newline='', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row_index, r in enumerate(reader):
                    qtext = (r.get('quote') or r.get('text') or '').strip()
                    if not qtext:
                        continue
                    mention = (r.get('mention_phrase') or '').strip()
                    cid = r.get('char_id')
                    try:
                        cid = int(cid) if cid not in (None, '', '-1') else None
                    except Exception:
                        cid = None

                    matches = list(RX_SEGMENT.finditer(qtext))
                    # If no explicit quote glyphs were detected, treat the entire
                    # field as one quote segment.
                    if not matches:
                        matches = [None]

                    for seg_idx, seg_match in enumerate(matches):
                        if seg_match is None:
                            raw_seg = qtext
                        else:
                            raw_seg = seg_match.group(0)
                        norm_seg = _norm_for_match(raw_seg)
                        if not norm_seg:
                            continue
                        quote_segments.append({
                            'norm': norm_seg,
                            'raw': raw_seg,
                            'char_id': cid,
                            'mention': mention,
                            'source_row': row_index,
                            'source_seg': seg_idx,
                        })

            if not quote_segments:
                return []

            # Extract every quoted span from the plain document text.
            RX_DOC_QUOTE = _re.compile(r'(?:[\u201c"]?)(?:.*?)(?:[\u201d"])', _re.S)
            doc_quotes = []
            for match in RX_DOC_QUOTE.finditer(doc_text):
                chunk_text = match.group(0)
                norm_chunk = _norm_for_match(chunk_text)
                if not norm_chunk:
                    continue
                doc_quotes.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': chunk_text,
                    'norm': norm_chunk,
                })

            if not doc_quotes:
                return []

            # Align each document quote with the next best segment from the BookNLP
            # outputs using exact match first and SequenceMatcher as a soft fallback.
            seg_idx = 0
            max_debug_mismatch = 5
            for dq in doc_quotes:
                assigned = None
                assigned_index = None
                # Try exact match within a limited lookahead window.
                lookahead_limit = min(len(quote_segments), seg_idx + 12)
                for candidate_idx in range(seg_idx, lookahead_limit):
                    seg = quote_segments[candidate_idx]
                    if dq['norm'] == seg['norm']:
                        assigned = seg
                        assigned_index = candidate_idx
                        break
                    # Allow prefix/suffix containment when BookNLP truncates or spans
                    if seg['norm'] and (dq['norm'].startswith(seg['norm']) or seg['norm'].startswith(dq['norm'])):
                        assigned = seg
                        assigned_index = candidate_idx
                        break

                if assigned is None:
                    # Soft match using SequenceMatcher ratio.
                    best_score = 0.0
                    best_seg = None
                    best_idx = None
                    for candidate_idx in range(seg_idx, lookahead_limit):
                        seg = quote_segments[candidate_idx]
                        score = difflib.SequenceMatcher(None, dq['norm'], seg['norm']).ratio()
                        if score > best_score:
                            best_score = score
                            best_seg = seg
                            best_idx = candidate_idx
                        if score >= 0.995:  # practically identical
                            break
                    if best_seg is not None and best_score >= 0.72:
                        assigned = best_seg
                        assigned_index = best_idx

                if assigned is not None:
                    dq['char_id'] = assigned['char_id']
                    dq['mention'] = assigned['mention']
                    dq['source_row'] = assigned['source_row']
                    dq['source_seg'] = assigned['source_seg']
                    seg_idx = assigned_index + 1
                else:
                    dq['char_id'] = None
                    dq['mention'] = ''
                    if max_debug_mismatch > 0:
                        print(f"[DEBUG] Unmatched quote segment: {dq['text'][:80]!r}")
                        max_debug_mismatch -= 1

            # Emit narration/quote rows sequentially.
            rows_out: List[Dict[str, str]] = []
            cursor = 0
            for dq in doc_quotes:
                qs, qe = dq['start'], dq['end']
                if cursor < qs:
                    nbeg, nend = cursor, qs
                    narr = doc_text[nbeg:nend]
                    narr_s = narr.strip()
                    if narr_s:
                        rows_out.append({
                            'speaker': 'Narrator',
                            'text': narr_s,
                            'is_quote': False,
                            '_hard_quote': False,
                            '_char_begin': nbeg,
                            '_char_end': nend,
                        })

                cid = dq.get('char_id')
                mention = dq.get('mention') or ''
                if isinstance(cid, int) and cid in char_id_to_name:
                    speaker = char_id_to_name[cid]
                else:
                    cleaned = _re.sub(r'^(?:\w+ed|\w+s|said|asked|replied|answered|whispered|shouted|muttered|cried|called|yelled|murmured|hissed|breathed|snapped|growled|moaned|told)\s+', '', mention.strip(), flags=_re.I)
                    speaker = _normalize_name(cleaned)
                if not speaker or speaker.lower() in {'narrator', 'the narrator'}:
                    speaker = 'Unknown'

                rows_out.append({
                    'speaker': speaker,
                    'text': doc_text[qs:qe],
                    'is_quote': True,
                    '_hard_quote': True,
                    '_char_begin': qs,
                    '_char_end': qe,
                    '_char_id': cid,
                })
                cursor = qe

            if cursor < len(doc_text):
                nbeg, nend = cursor, len(doc_text)
                tail = doc_text[nbeg:nend]
                tail_s = tail.strip()
                if tail_s:
                    rows_out.append({
                        'speaker': 'Narrator',
                        'text': tail_s,
                        'is_quote': False,
                        '_hard_quote': False,
                        '_char_begin': nbeg,
                        '_char_end': nend,
                    })

            return rows_out

        # Try to locate tokens file alongside
        tokens_path = os.path.join(base_dir, f"{prefix}.tokens")
        if not os.path.exists(tokens_path):
            # tolerate .tokens.txt variant
            alt = os.path.join(base_dir, f"{prefix}.tokens.txt")
            tokens_path = alt if os.path.exists(alt) else None

        hard_rows: List[Dict[str, str]] = []
        if os.path.exists(quotes_path) and os.path.exists(plain_path):
            hard_rows = _build_hard_rows_from_quotes(quotes_path, plain_path, tokens_path)
            if hard_rows:
                print(f"[BookProcessor] Built {len(hard_rows)} hard-quote rows from {os.path.basename(quotes_path)}")

        if hard_rows:
            lines = hard_rows
        else:
            # Fallback to the parser + merging heuristics
            lines = parse_booktxt(booktxt_path)
            base_path = booktxt_path.replace('.book.txt', '.quotes')
            if os.path.exists(base_path):
                lines = merge_quote_spans(lines, base_path)
                print(f"[BookProcessor] Merged quote spans using {base_path}")

        # Split embedded quotes in narrator text BEFORE merging
        before_split = len(lines)
        lines = split_embedded_quotes_in_narration(lines)
        after_split = len(lines)
        if before_split != after_split:
            print(f"[BookProcessor] Split embedded quotes: {before_split} → {after_split} rows")

        # Merge consecutive narrator blocks for TTS narrator voice
        before_narrator_merge = len([r for r in lines if not r.get('is_quote') == 'True'])
        lines = merge_narrator_blocks(lines)
        after_narrator_merge = len([r for r in lines if not r.get('is_quote') == 'True'])
        if before_narrator_merge != after_narrator_merge:
            print(f"[BookProcessor] Merged narrator blocks: {before_narrator_merge} → {after_narrator_merge}")

        # Convert __EMBEDDED_QUOTE__ markers back to Narrator
        for row in lines:
            if row.get('speaker') == '__EMBEDDED_QUOTE__':
                row['speaker'] = 'Narrator'

        # Filter out stray/empty quotes (artifacts from BookNLP)
        filtered = []
        for row in lines:
            text = row.get('text', '').strip()
            if len(text) <= 2 and text in ('', '"', '""', "'", "''", '...'):
                continue
            filtered.append(row)

        if len(filtered) < len(lines):
            print(f"[BookProcessor] Filtered {len(lines) - len(filtered)} empty/stray quote rows")

        return filtered
    except Exception as e:
        print(f"[BookProcessor] Error parsing {booktxt_path}: {e}")
        return []


# CLI helper for testing
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) != 2:
        print("Usage: python book_processor.py <path/to/book.txt>")
        sys.exit(1)

    path = sys.argv[1]
    data = run_book_processor(path)
    print(json.dumps(data[:20], indent=2, ensure_ascii=False))  # preview first 20 lines
