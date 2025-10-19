# ===================== POST-PROCESS: MERGE ATTRIBUTION FRAGMENTS =====================
def merge_attrib_fragments_with_quotes(rows, max_attrib_len=120):
    """
    Merge short Narrator lines (attribution fragments) with adjacent quote rows.
    Only merges if the fragment is <max_attrib_len chars and directly follows or precedes a quote.
    """
    out = []
    i = 0
    while i < len(rows):
        row = rows[i]
        # If this is a short Narrator fragment and previous row is a quote, merge
        if (
            row.get("speaker", "").lower() == "narrator"
            and not row.get("is_quote")
            and len(row.get("text", "")) < max_attrib_len
            and i > 0
            and rows[i-1].get("is_quote")
        ):
            # Merge with previous quote row
            prev = out.pop() if out else rows[i-1]
            prev["text"] = (prev.get("text", "") + " " + row.get("text", "")).strip()
            out.append(prev)
            i += 1
            continue
        # If this is a short Narrator fragment and next row is a quote, merge
        elif (
            row.get("speaker", "").lower() == "narrator"
            and not row.get("is_quote")
            and len(row.get("text", "")) < max_attrib_len
            and i+1 < len(rows)
            and rows[i+1].get("is_quote")
        ):
            # Merge with next quote row
            next_row = rows[i+1]
            next_row["text"] = (row.get("text", "") + " " + next_row.get("text", "")).strip()
            out.append(next_row)
            i += 2
            continue
        else:
            out.append(row)
            i += 1
    return out
# ===================== FINAL QUOTE/NARRATION BLOCK OUTPUT =====================
def fix_misclassified_attribution_fragments(rows):
    """
    Fix attribution fragments that were incorrectly marked as is_quote=True or speaker=Unknown.
    These are rows like "said X", "asked Y", "he went on in a monotone" that should be narration, NOT character dialogue.
    
    Handles two cases:
    1. is_quote=True but text is actually attribution → change to is_quote=False, speaker=Narrator
    2. speaker=Unknown but text is actually attribution → change to speaker=Narrator
    """
    import re
    
    log(f"[fix_attrib] Called with {len(rows)} rows")
    fixed_count = 0
    unknown_to_narrator = 0
    
    # Define attribution verbs locally to avoid dependency issues
    attrib_verbs = {
        "said", "says", "say", "ask", "asks", "asked", "reply", "replies", "replied",
        "answer", "answers", "answered", "tell", "tells", "told", "call", "called",
        "yell", "yelled", "shout", "shouted", "cry", "cried", "whisper", "whispered",
        "murmur", "murmured", "mutter", "muttered", "snap", "snapped", "retort", "retorted",
        "laugh", "laughed", "sob", "sobbed", "hiss", "hissed", "note", "noted",
        "observe", "observed", "remark", "remarked", "insist", "insisted", "counter", "countered",
        "agree", "agreed", "warn", "warned", "offer", "offered", "beg", "begged",
        "demand", "demanded", "protest", "protested", "announce", "announced", "explain", "explained",
        "declare", "declared", "argue", "argued", "suggest", "suggested", "continue", "continued",
        "interject", "interjected", "interrupt", "interrupted", "concede", "conceded",
        "promise", "promised", "plead", "pleaded", "rejoin", "rejoined", "state", "stated",
        "blurt", "blurted", "query", "queried", "go", "went", "add", "added",
        "confirm", "confirmed", "gasp", "gasped", "repeat", "repeated", "persist", "persisted"
    }
    
    def is_attribution_fragment(text):
        """Check if text is an attribution fragment."""
        t = text.strip()
        if not t or len(t) > 150 or len(t) < 3:
            return False
        
        # Remove leading punctuation/dashes
        t_clean = re.sub(r'^[—\-–,\s]+', '', t)
        
        # Pattern 1: "said Name" / "asked his friend Name" / "Name said"
        # Verb + optional filler + Name OR Name + verb
        verb_pattern = r'\b(' + '|'.join(attrib_verbs) + r')\b'
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        
        # Check if it has a verb and a name
        has_verb = bool(re.search(verb_pattern, t_clean, re.IGNORECASE))
        has_name = bool(re.search(name_pattern, t_clean))
        
        if has_verb and has_name:
            # Make sure it's not a full sentence (shouldn't have "I", "you", "we" as subject)
            if not re.search(r'\b(I|you|we|they)\b.*\b(' + '|'.join(attrib_verbs) + r')\b', t_clean, re.IGNORECASE):
                return True
        
        # Pattern 2: Pronoun + verb pattern: "he went on", "she continued", "they asked"
        pronoun_verb = re.match(r'^\s*(he|she|they|it)\s+(' + '|'.join(attrib_verbs) + r')\b', t_clean, re.IGNORECASE)
        if pronoun_verb and len(t_clean.split()) <= 10:  # Keep it short
            return True
        
        # Pattern 3: Just a verb + adverb: "continued softly", "asked curiously"
        verb_adverb = re.match(r'^\s*(' + '|'.join(attrib_verbs) + r')\s+\w+ly\s*[.,;!?]*$', t_clean, re.IGNORECASE)
        if verb_adverb:
            return True
        
        # Pattern 4: "the/his/her old man/woman/friend continued"  - descriptive + name + verb
        descriptive_pattern = re.match(r'^\s*(?:the|his|her|their)\s+(?:\w+\s+)?(?:man|woman|friend|person|one|other)\s+(' + '|'.join(attrib_verbs) + r')\b', t_clean, re.IGNORECASE)
        if descriptive_pattern and len(t_clean.split()) <= 12:
            return True
        
        # Pattern 5: "Name persisted/continued" with just verb (2-4 words total)
        words = t_clean.split()
        if 2 <= len(words) <= 4:
            # Last word (minus punctuation) should be a verb
            last_word = re.sub(r'[.,;!?]+$', '', words[-1]).lower()
            if last_word in attrib_verbs:
                # First word should be capitalized (a name or pronoun)
                if words[0][0].isupper() or words[0].lower() in {'he', 'she', 'they', 'it'}:
                    return True
        
        return False
    
    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        
        if is_attribution_fragment(text):
            # Case 1: Marked as quote but is attribution
            if row.get("is_quote"):
                log(f"[fix_attrib] Quote→Narrator: {text[:80]}")
                row["is_quote"] = False
                row["speaker"] = "Narrator"
                fixed_count += 1
            
            # Case 2: Marked as Unknown but is attribution  
            elif row.get("speaker") == "Unknown":
                log(f"[fix_attrib] Unknown→Narrator: {text[:80]}")
                row["speaker"] = "Narrator"
                # Make sure it's marked as non-quote
                if row.get("is_quote") is None or row.get("is_quote"):
                    row["is_quote"] = False
                unknown_to_narrator += 1
    
    if fixed_count > 0 or unknown_to_narrator > 0:
        log(f"[fix_attrib] Fixed {fixed_count} misclassified quotes, {unknown_to_narrator} Unknown→Narrator")
    else:
        log(f"[fix_attrib] No misclassified attribution fragments found")
    
    return rows

def split_multi_quote_rows(rows):
    """
    BookNLP sometimes incorrectly merges multiple quotes from different speakers into one row.
    Example: "Quote 1," "Quote 2" - should be 2 separate rows, not 1.
    
    This splits rows that contain multiple complete quote pairs (open + close).
    Marks split rows with _was_multi_span=True to prevent re-merging in finalize.
    """
    result = []
    
    for row in rows:
        if not row.get("is_quote"):
            result.append(row)
            continue
            
        text = row.get("text", "").strip()
        
        # Find all complete quote spans: "..." or "..." (ASCII + smart quotes)
        import re
        # Match opening quote, content, closing quote
        quote_pattern = r'["""]([^"""]*?)["""]'
        matches = list(re.finditer(quote_pattern, text))
        
        if len(matches) <= 1:
            # Single quote or no quotes - keep as is
            result.append(row)
            continue
        
        # DEBUG: Log multi-quote rows
        if "Because it" in text or "What?" in text or len(matches) > 1:
            log(f"[split_multi] Found {len(matches)} quotes in row with speaker={row.get('speaker')}: {text[:100]}")
        
        # Multiple quotes found - split them and mark to prevent re-merging
        for i, match in enumerate(matches):
            new_row = dict(row)
            # Include the quotes in the text
            new_row["text"] = text[match.start():match.end()]
            # First quote keeps original speaker, others get Unknown
            if i > 0:
                new_row["speaker"] = "Unknown"
            # Mark to prevent consolidation in finalize
            new_row["_was_multi_span"] = True
            new_row["_split_index"] = i
            result.append(new_row)
            
            # DEBUG
            if "Because it" in text or "What?" in text:
                log(f"[split_multi]   Created row {i}: speaker={new_row['speaker']} _was_multi_span=True text={new_row['text']}")
    
    return result

def split_attribution_from_quotes(rows):
    """
    Split rows where attribution is mixed with quote text.
    Handles TWO patterns:
      1. Attribution BEFORE quote: 'explained Smith."Quote text"'
      2. Attribution AFTER quote: '"Quote text" said Smith.'
    
    Both become:
      1. Narrator: "explained/said Smith."
      2. Character: "Quote text"
    """
    result = []
    
    for row in rows:
        if not row.get("is_quote"):
            # Non-quote rows - pass through unchanged
            result.append(row)
            continue
            
        text = row.get("text", "").strip()
        if not text:
            result.append(row)
            continue
        
        import re
        
        # Pattern 1: Attribution BEFORE quote (existing logic)
        # e.g., "explained Smith." followed by quote
        start_attrib_pattern = r'^((?:said|asked|replied|whispered|shouted|cried|muttered|continued|responded|explained|added|insisted|agreed|laughed|answered|noted|remarked|observed|demanded|protested|announced|declared|yelled|called|murmured|snapped|hissed|breathed)\s+[A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+)*\.)\s*(["""].+)$'
        
        match = re.match(start_attrib_pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            attrib_text = match.group(1).strip()
            quote_text = match.group(2).strip()
            
            # Extract speaker name from attribution
            name_match = re.search(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b', attrib_text)
            speaker = name_match.group(1) if name_match else "Unknown"
            
            # Create quote row FIRST (character dialogue)
            quote_row = dict(row)
            quote_row["text"] = quote_text
            quote_row["speaker"] = speaker
            quote_row["is_quote"] = True
            result.append(quote_row)
            
            # Create attribution row AFTER (Narrator)
            attrib_row = dict(row)
            attrib_row["text"] = attrib_text
            attrib_row["speaker"] = "Narrator"
            attrib_row["is_quote"] = False
            result.append(attrib_row)
            continue
        
        # Pattern 2: Attribution AFTER quote (NEW)
        # e.g., "Quote text" said Smith.
        # Quote must use smart quotes or ASCII quotes
        end_attrib_pattern = r'^(["""][^"""]+["""])\s+((?:said|asked|replied|whispered|shouted|cried|muttered|continued|responded|explained|added|insisted|agreed|laughed|answered|noted|remarked|observed|demanded|protested|announced|declared|yelled|called|murmured|snapped|hissed|breathed)\s+[A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+)*\.)$'
        
        match = re.match(end_attrib_pattern, text, re.IGNORECASE)
        if match:
            quote_text = match.group(1).strip()
            attrib_text = match.group(2).strip()
            
            # Extract speaker name from attribution
            name_match = re.search(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b', attrib_text)
            speaker = name_match.group(1) if name_match else row.get("speaker", "Unknown")
            
            # Create quote row FIRST (character dialogue)
            quote_row = dict(row)
            quote_row["text"] = quote_text
            quote_row["speaker"] = speaker
            quote_row["is_quote"] = True
            result.append(quote_row)
            
            # Create attribution row AFTER (Narrator)
            attrib_row = dict(row)
            attrib_row["text"] = attrib_text
            attrib_row["speaker"] = "Narrator"
            attrib_row["is_quote"] = False
            result.append(attrib_row)
            continue
        
        # No attribution pattern matched - pass through unchanged
        result.append(row)
    
    return result

def finalize_quote_narration_blocks(rows):
    """
    Final pass for audiobook TTS:
    - Merge consecutive quotes from the SAME speaker into single character lines
    - Merge all is_quote=False rows as Narrator (narration + attribution, gets narrator voice)
    
    This ensures:
    - Multi-sentence character dialogue stays together with correct speaker
    - Character dialogue gets character voice
    - Narration + attribution gets narrator voice
    """
    import re
    
    def _has_multiple_quote_spans(text):
        """Check if text contains multiple complete quote spans (turn-taking dialogue)."""
        if not text:
            return False
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        # Count quote pairs - pattern: opening quote, content, closing quote
        quote_pattern = r'"[^"]*?"'
        matches = re.findall(quote_pattern, text)
        return len(matches) > 1
    
    out = []
    narr_buffer = None
    quote_buffer = None
    
    for idx, row in enumerate(rows):
        if row.get("is_quote"):
            # Flush narration buffer if any
            if narr_buffer:
                out.append(narr_buffer)
                narr_buffer = None
            
            # Check if this row has multiple quote spans (dialogue turn-taking)
            current_text = row.get("text", "")
            has_multi_spans = _has_multiple_quote_spans(current_text)
            
            # Do NOT merge if row has multiple quote spans (turn-taking)
            # OR if row was split from a multi-span row (preserve the split)
            if has_multi_spans or row.get("_was_multi_span"):
                # Flush any existing quote buffer
                if quote_buffer:
                    out.append(quote_buffer)
                    quote_buffer = None
                # Output this row as-is (don't merge turn-taking dialogue)
                out.append(row)
                continue
            
            # DISABLED: Do NOT merge consecutive quotes from the same speaker
            # User wants them separate so they can assign voices in GUI
            # Each quote stays as its own row for TTS voice assignment
            current_speaker = (row.get("speaker") or "").strip()
            
            # Just flush any existing buffer and output this quote
            if quote_buffer:
                out.append(quote_buffer)
                quote_buffer = None
            out.append(row)
        else:
            # Flush quote buffer if any
            if quote_buffer:
                out.append(quote_buffer)
                quote_buffer = None
            
            # Merge all narration (including attribution) - will get narrator voice
            if narr_buffer is None:
                narr_buffer = dict(row)
                narr_buffer["speaker"] = "Narrator"
                narr_buffer["is_quote"] = False
            else:
                narr_buffer["text"] = (narr_buffer.get("text", "") + " " + row.get("text", "")).strip()
    
    # Flush remaining buffers
    if quote_buffer:
        out.append(quote_buffer)
    if narr_buffer:
        out.append(narr_buffer)
    
    return out
def _merge_consecutive_narrator_rows(rows):
    """
    Merge consecutive Narrator rows (is_quote: False) into a single row.
    Preserves order and text, does not merge across quotes or character lines.
    """
    if not rows:
        return []
    merged = []
    buffer = None
    for row in rows:
        is_narr = (row.get("speaker", "").strip().lower() == "narrator") and not row.get("is_quote")
        if is_narr:
            if buffer is None:
                buffer = dict(row)
            else:
                buffer["text"] = (buffer["text"] + "\n" + (row.get("text") or "")).strip()
        else:
            if buffer is not None:
                merged.append(buffer)
                buffer = None
            merged.append(row)
    if buffer is not None:
        merged.append(buffer)
    return merged
# Consolidated imports moved here by tools/move_imports_top.py
import codecs
import csv
import datetime
import difflib
import html
import json
import math
import os
import re
import shutil
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from app.core.book_processor import run_book_processor
from app.core.booknlp_runner import run_booknlp


# ===================== MISCELLANEOUS UTILITIES =====================
def _glyph_budget(rows):
    """Count visible quote chars for budget checks."""
    if not rows:
        return 0
    QUOTES = {'"', "“", "”", "‘", "’", "«", "»"}
    total = 0
    for r in rows:
        for ch in r.get("text") or "":
            if ch in QUOTES:
                total += 1
    return total


def _profile(stage_name, fn, rows, output_dir, prefix, *args):
    t0 = time.time()
    out = fn(rows, *args)
    dt = int((time.time() - t0) * 1000)
    trace_stage(stage_name, out, output_dir, prefix, t_ms=dt)
    return out


def _safe_excerpt(text: str, n: int = 120) -> str:
    t = (text or "").replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _row_rid(row: dict) -> str:
    """Best-effort row id for logging."""
    if not isinstance(row, dict):
        return ""
    return str(row.get("_rid") or row.get("rid") or "")


# ===================== ATTRIBUTION & SPEAKER FUNCTIONS =====================
# LOGGING & DEBUGGING UTILITIES
def dbg_inc(key: str, by: int = 1) -> None:
    """Tiny helper so we don't crash if DBG isn't defined yet."""
    try:
        DBG[key] = DBG.get(key, 0) + by
    except Exception:
        pass


def _ensure_rid(row: dict):
    """Guarantee a stable id for TSVs; keep any existing."""
    rid = row.get("_rid")
    if rid is None:
        rid = row["_rid"] = id(
            row
        )  # fallback; better if you already assign rids earlier
    return rid


def log_attrib_op(
    stage: str,
    op: str,
    row: dict,
    prev_sp: str,
    new_sp: str,
    reason: str,
    idx: int | None = None,
):
    """Append a row-level attribution operation to the in-memory buffer."""
    try:
        rid = _ensure_rid(row)
        txt = (row.get("text") or "").replace("\t", " ").replace("\n", " ")
        _ATTRIB_OPS.append(
            {
                "stage": stage or "",
                "op": op or "",
                "rid": rid,
                "prev": prev_sp or "",
                "new": new_sp or "",
                "reason": reason or "",
                "idx": -1 if idx is None else idx,
                "text": txt[:240],
            }
        )
    except Exception:
        pass


def apply_speaker(
    row: dict, who: str, reason: str, stage: str = "", idx: int | None = None
) -> bool:
    """
    Centralized setter+logger+lock:
      - only overwrites Unknown/Narrator/empty or same speaker
      - locks the row
      - logs TSV + DBG counters
    Returns True if set/locked, False if refused (conflict).
    """
    if not row or not who:
        return False
    prev = (row.get("speaker") or "").strip()
    if prev in ("", "Unknown", "Narrator") or prev == who:
        row["speaker"] = who
        row["_lock_speaker"] = True
        row["_locked_to"] = who
        row["_lock_reason"] = reason
        dbg_inc("speaker_sets")
        dbg_inc("speaker_locks")
        log_attrib_op(stage, "set_speaker", row, prev, who, reason, idx)
        return True
    else:
        dbg_inc("speaker_skips_conflict")
        log_attrib_op(stage, "skip_conflict", row, prev, who, reason, idx)
        return False


def record_attrib_op(
    stage: str,
    op: str = "",
    rid: str | None = None,
    prev: str = "",
    new: str = "",
    reason: str = "",
    idx: int | None = None,
    text: str = "",
) -> None:
    """
    Generic recorder you can call from any heuristic (e.g., demotions, harvests).
    Writes a single row into _ATTRIB_OPS (flushed by _emit_attrib_ops).
    """
    try:
        _ATTRIB_OPS.append(
            {
                "stage": stage or "",
                "op": op or "",
                "rid": str(rid or ""),
                "prev": (prev or ""),
                "new": (new or ""),
                "reason": (reason or ""),
                "idx": "" if idx is None else str(idx),
                "text": _safe_excerpt(text),
            }
        )
    except Exception:
        # don't let logging break the pipeline
        pass


def record_attrib_op_row(
    stage: str,
    op: str,
    row: dict,
    prev: str,
    new: str,
    reason: str,
    idx: int | None = None,
) -> None:
    """Convenience wrapper that extracts rid/text from the row, then forwards to record_attrib_op()."""
    try:
        rid = row.get("_rid", "")
        text = (row.get("text") or "").replace("\n", " ")[:200]
    except Exception:
        rid, text = "", ""
    record_attrib_op(
        stage=stage,
        op=op,
        rid=rid,
        prev=prev,
        new=new,
        reason=reason,
        idx=idx,
        text=text,
    )


# ===================== QUOTE INTEGRITY & AUDIT FUNCTIONS (continued) =====================
def _qa_emit_quote_report(output_dir: str, prefix: str):
    """
    Emit two TSVs into output_dir:
      1) {prefix}quote_report.tsv  : full per-stage snapshots
      2) {prefix}quote_events.tsv  : only suspicious transitions per RID
    """
    try:
        series = DBG.get("_qa_series") or []
        if not series:
            _qa_safe_log("[qa] no series captured; skip report")

            # Removed stray, incorrectly indented code block that was outside any function.
        stage_maps = []
        for stage, snap in series:
            m = {row["rid"]: row for row in snap}
            stage_maps.append((stage, m))

        def excerpt(s):
            return (s or "").replace("\t", " ").replace("\n", "\\n")[:200]

        with open(events_path, "w", encoding="utf-8") as f:
            f.write(
                "prev_stage\tstage\trid\tevent\tspan_prev\tspan_cur\tglyph_prev\tglyph_cur\t"
                "isq_prev\tisq_cur\tdemoted_cur\tspeaker_prev\tspeaker_cur\texcerpt_prev\texcerpt_cur\n"
            )

            for k in range(1, len(stage_maps)):
                prev_stage, prev_map = stage_maps[k - 1]
                stage, cur_map = stage_maps[k]

                # union of RIDs so we detect rid_missing too
                rids = set(prev_map.keys()) | set(cur_map.keys())
                for rid in rids:
                    prev = prev_map.get(rid)
                    cur = cur_map.get(rid)

                    if prev and not cur:
                        # RID vanished completely at this stage
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\trid_missing\t"
                            f"{prev['span_cnt']}\tNA\t{prev['glyph_cnt']}\tNA\t"
                            f"{int(prev['is_quote'])}\tNA\tNA\t{prev['speaker']}\tNA\t"
                            f"{excerpt(prev['txt'])}\t\n"
                        )
                        continue
                    if not prev and cur:
                        # New RID appeared — not suspicious by itself
                        continue

                    # Both exist; evaluate transitions
                    span_prev, span_cur = prev["span_cnt"], cur["span_cnt"]
                    glyph_prev, glyph_cur = prev["glyph_cnt"], cur["glyph_cnt"]
                    isq_prev, isq_cur = bool(prev["is_quote"]), bool(cur["is_quote"])
                    demoted_ok = bool(cur.get("qa_demoted"))

                    # A) Quote spans vanished without intentional demote
                    if span_prev > 0 and span_cur == 0 and not demoted_ok:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tlost_spans_without_demote\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

                    # B) is_quote flipped to False but spans remain (flag misuse)
                    if isq_prev and (not isq_cur) and span_cur > 0:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tflag_flip_with_spans\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

                    # C) glyphs dropped (>=2) without demote (possible quote stripping)
                    if (glyph_prev - glyph_cur) >= 2 and not demoted_ok:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tglyphs_drop_without_demote\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

                    # D) demoted but OK (for reference)
                    if span_prev > 0 and span_cur == 0 and demoted_ok:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tdemoted_quote_ok\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

        _qa_safe_log(f"[qa] wrote {report_path}")
        _qa_safe_log(f"[qa] wrote {events_path}")

    except Exception as e:
        _qa_safe_log(f"[qa] report failed: {e}")


# ===================== QUOTE INTEGRITY & AUDIT FUNCTIONS =====================
def _qa_safe_log(msg: str):
    """Safely log a message for quote audit, fallback to print if log fails."""
    try:
        log(msg)
    except Exception:
        try:
            print(msg)
        except Exception:
            pass


def _qa_stage_snapshot(stage: str, results: list[dict]) -> list[dict]:
    """
    Build a compact snapshot for the evaluator: one dict per row with metrics
    we care about. Uses existing helpers in your module.
    """
    snap = []
    for idx, r in enumerate(results or []):
        txt = r.get("text") or ""
        tnorm = _norm_unicode_quotes(txt)
        spans = _quote_spans(tnorm) or []
        span_cnt = len(spans)
        glyph_cnt = (
            tnorm.count("“")
            + tnorm.count("”")
            + tnorm.count('"')
            + tnorm.count("«")
            + tnorm.count("»")
        )
        # 'balanced' means at least one matched span on this row; else 'none'
        bal = "balanced" if span_cnt > 0 else "none"
        rid = r.get("_rid")
        # Fallback RID so report still renders if upstream didn't assign _rid
        if rid is None:
            rid = f"idx:{idx}"
        snap.append(
            {
                "stage": stage,
                "rid": rid,
                "idx": idx,
                "is_quote": bool(r.get("is_quote")),
                "span_cnt": int(span_cnt),
                "glyph_cnt": int(glyph_cnt),
                "bal": bal,
                "speaker": (r.get("speaker") or ""),
                "qa_demoted": bool(r.get("_qa_demoted_quote")),
                "txt": txt,
            }
        )
    return snap


def _qa_collect_stage(stage: str, results: list[dict]):
    """
    Append a stage snapshot to a series stored in DBG["_qa_series"].
    Keeps memory light by storing only compact dicts.
    """
    try:
        series = DBG.setdefault("_qa_series", [])
        series.append((stage, _qa_stage_snapshot(stage, results)))
    except Exception as e:
        _qa_safe_log(f"[qa] collect failed @ {stage}: {e}")


# ================= GLOBAL VARIABLES AND CONSTANTS =================
CANON_WHITELIST = set()
SURNAME_TO_CANON = {}
WH_ALIAS = {}  # token -> Canonical (e.g., "smith"->"Smith")
QMAP_CACHE = None  # global cache of quotes rows for finalizer trust
ALIAS_INV_CACHE = {}  # latest alias_inv for finalization fallback
DEBUG_AUDIT = True
QUOTES_ARE_ATOMIC = True  # when True, we never break a speaker’s quoted run

# === Attribution debug counters ===
DBG = {
    "reassert_strict_runs": 0,
    "reassert_flag_changes": 0,
    "lonely_quote_stripped": 0,
    "narr_tail_splits": 0,
    "coalesce_skipped_kind": 0,
    "coalesce_skipped_quote2quote": 0,
    "coalesce_skipped_attribfrag": 0,
    "coalesce_merges": 0,
}

# ================= QUOTE AUDIT HARNESS CONFIG =================
AUDIT_QUOTES = True  # master switch
HARD_FAIL_ON_QUOTE_LOSS = False  # raise on first suspicious change
AUTO_RESTORE_ON_QUOTE_LOSS = True  # try to revert to prior text if quotes vanish
AUDIT_MAX_EXCERPT = 160  # how much text to show in logs
AUDIT_FILE_BASENAME = ".quote_audit.tsv"  # saved next to other outputs

# --- Heuristic Filters ---
SHORT_DIALOGUE = {
    "ok",
    "no",
    "yes",
    "yeah",
    "yep",
    "nah",
    "shit",
    "fuck",
    "damn",
    "hi",
    "hey",
    "bye",
    "hmm",
    "uh",
    "um",
}

# --- Attribution fragment size guards (used by _looks_like_attribution_fragment) ---
MAX_ATTRIB_FRAGMENT_LEN = 120  # characters; keep short tails like "— said Zack."
MAX_ATTRIB_FRAGMENT_WORDS = 24  # words; longer is probably narration, not a tail

# Build the verb set from your global list if available; else a tight core
_AF_VERBS = set(globals().get("_ATTRIB_VERBS", [])) or {
    "said",
    "says",
    "ask",
    "asks",
    "asked",
    "reply",
    "replies",
    "replied",
    "answer",
    "answers",
    "answered",
    "called",
    "yelled",
    "shouted",
    "cried",
    "whispered",
    "murmured",
    "muttered",
    "snapped",
    "retorted",
    "laughed",
    "sobbed",
    "hissed",
    "breathed",
    "noted",
    "observed",
    "remarked",
    "insisted",
    "countered",
    "agreed",
    "warned",
    "offered",
    "begged",
    "demanded",
    "protested",
    "announced",
    "explained",
    "declared",
    "continued",
    "interjected",
    "interrupted",
    "conceded",
    "promised",
    "pleaded",
    "went",
    "went on",
    "rejoined",
    "stated",
}

# Compile the shared patterns only once
if "_AF_VERB_NAME_RX" not in globals():
    _AF_VERBS_RX = r"(?:%s)" % "|".join(
        sorted(map(re.escape, _AF_VERBS), key=len, reverse=True)
    )
    _AF_FILLER = (
        r"(?:\s+(?:[a-z]{1,12}|then|again|softly|quietly|firmly|simply|just)){0,3}"
    )
    _AF_PROPER = r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}"

    # Verb → Name  (e.g., ", said softly John Smith.")
    _AF_VERB_NAME_RX = re.compile(
        rf"^[—\-–—,\s]*(?P<verb>{_AF_VERBS_RX}){_AF_FILLER}\s+(?P<who>{_AF_PROPER})[\s,.\-–—:;!?]*$",
        re.IGNORECASE,
    )
    # Name → Verb  (e.g., ", John Smith said softly.")
    _AF_NAME_VERB_RX = re.compile(
        rf"^[—\-–—,\s]*(?P<who>{_AF_PROPER})\s+(?P<verb>{_AF_VERBS_RX}){_AF_FILLER}[\s,.\-–—:;!?]*$",
        re.IGNORECASE,
    )

# --- Canonical character whitelist from characters_simple.json ---
CANON_WHITELIST = set()
SURNAME_TO_CANON = {}
WH_ALIAS = {}  # token -> Canonical (e.g., "smith"->"Smith")
QMAP_CACHE = None  # global cache of quotes rows for finalizer trust
ALIAS_INV_CACHE = {}  # latest alias_inv for finalization fallback
DEBUG_AUDIT = True
QUOTES_ARE_ATOMIC = True  # when True, we never break a speaker’s quoted run

# === Attribution debug counters ===
DBG = {
    "reassert_strict_runs": 0,
    "reassert_flag_changes": 0,
    "lonely_quote_stripped": 0,
    "narr_tail_splits": 0,
    "coalesce_skipped_kind": 0,
    "coalesce_skipped_quote2quote": 0,
    "coalesce_skipped_attribfrag": 0,
    "coalesce_merges": 0,
}

# ===================== QUOTE INTEGRITY EVALUATOR =====================


def _qa_safe_log(msg: str):
    try:
        log(msg)
    except Exception:
        try:
            print(msg)
        except Exception:
            pass


def _qa_stage_snapshot(stage: str, results: list[dict]) -> list[dict]:
    """
    Build a compact snapshot for the evaluator: one dict per row with metrics
    we care about. Uses existing helpers in your module.
    """
    snap = []
    for idx, r in enumerate(results or []):
        txt = r.get("text") or ""
        tnorm = _norm_unicode_quotes(txt)
        spans = _quote_spans(tnorm) or []
        span_cnt = len(spans)
        glyph_cnt = (
            tnorm.count("“")
            + tnorm.count("”")
            + tnorm.count('"')
            + tnorm.count("«")
            + tnorm.count("»")
        )
        # 'balanced' means at least one matched span on this row; else 'none'
        bal = "balanced" if span_cnt > 0 else "none"
        rid = r.get("_rid")
        # Fallback RID so report still renders if upstream didn't assign _rid
        if rid is None:
            rid = f"idx:{idx}"
        snap.append(
            {
                "stage": stage,
                "rid": rid,
                "idx": idx,
                "is_quote": bool(r.get("is_quote")),
                "span_cnt": int(span_cnt),
                "glyph_cnt": int(glyph_cnt),
                "bal": bal,
                "speaker": (r.get("speaker") or ""),
                "qa_demoted": bool(r.get("_qa_demoted_quote")),
                "txt": txt,
            }
        )
    return snap


def _qa_collect_stage(stage: str, results: list[dict]):
    """
    Append a stage snapshot to a series stored in DBG["_qa_series"].
    Keeps memory light by storing only compact dicts.
    """
    try:
        series = DBG.setdefault("_qa_series", [])
        series.append((stage, _qa_stage_snapshot(stage, results)))
    except Exception as e:
        _qa_safe_log(f"[qa] collect failed @ {stage}: {e}")


def _qa_emit_quote_report(output_dir: str, prefix: str):
    """
    Emit two TSVs into output_dir:
      1) {prefix}quote_report.tsv  : full per-stage snapshots
      2) {prefix}quote_events.tsv  : only suspicious transitions per RID
    """
    try:
        series = DBG.get("_qa_series") or []
        if not series:
            _qa_safe_log("[qa] no series captured; skip report")
            return

        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, f"{prefix}quote_report.tsv")
        events_path = os.path.join(output_dir, f"{prefix}quote_events.tsv")

        # 1) Write full per-stage snapshot
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(
                "stage\trid\tidx\tis_quote\tspan_cnt\tglyph_cnt\tbal\tspeaker\texcerpt\n"
            )
            for stage, snap in series:
                for row in snap:
                    ex = (row["txt"] or "").replace("\t", " ").replace("\n", "\\n")
                    f.write(
                        f"{stage}\t{row['rid']}\t{row['idx']}\t{int(row['is_quote'])}\t"
                        f"{row['span_cnt']}\t{row['glyph_cnt']}\t{row['bal']}\t"
                        f"{row['speaker']}\t{ex[:200]}\n"
                    )

        # 2) Compute events by RID across consecutive stages
        # Map: stage -> {rid -> row}
        stage_maps = []
        for stage, snap in series:
            m = {row["rid"]: row for row in snap}
            stage_maps.append((stage, m))

        def excerpt(s):
            return (s or "").replace("\t", " ").replace("\n", "\\n")[:200]

        with open(events_path, "w", encoding="utf-8") as f:
            f.write(
                "prev_stage\tstage\trid\tevent\tspan_prev\tspan_cur\tglyph_prev\tglyph_cur\t"
                "isq_prev\tisq_cur\tdemoted_cur\tspeaker_prev\tspeaker_cur\texcerpt_prev\texcerpt_cur\n"
            )

            for k in range(1, len(stage_maps)):
                prev_stage, prev_map = stage_maps[k - 1]
                stage, cur_map = stage_maps[k]

                # union of RIDs so we detect rid_missing too
                rids = set(prev_map.keys()) | set(cur_map.keys())
                for rid in rids:
                    prev = prev_map.get(rid)
                    cur = cur_map.get(rid)

                    if prev and not cur:
                        # RID vanished completely at this stage
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\trid_missing\t"
                            f"{prev['span_cnt']}\tNA\t{prev['glyph_cnt']}\tNA\t"
                            f"{int(prev['is_quote'])}\tNA\tNA\t{prev['speaker']}\tNA\t"
                            f"{excerpt(prev['txt'])}\t\n"
                        )
                        continue
                    if not prev and cur:
                        # New RID appeared — not suspicious by itself
                        continue

                    # Both exist; evaluate transitions
                    span_prev, span_cur = prev["span_cnt"], cur["span_cnt"]
                    glyph_prev, glyph_cur = prev["glyph_cnt"], cur["glyph_cnt"]
                    isq_prev, isq_cur = bool(prev["is_quote"]), bool(cur["is_quote"])
                    demoted_ok = bool(cur.get("qa_demoted"))

                    # A) Quote spans vanished without intentional demote
                    if span_prev > 0 and span_cur == 0 and not demoted_ok:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tlost_spans_without_demote\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

                    # B) is_quote flipped to False but spans remain (flag misuse)
                    if isq_prev and (not isq_cur) and span_cur > 0:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tflag_flip_with_spans\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

                    # C) glyphs dropped (>=2) without demote (possible quote stripping)
                    if (glyph_prev - glyph_cur) >= 2 and not demoted_ok:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tglyphs_drop_without_demote\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

                    # D) demoted but OK (for reference)
                    if span_prev > 0 and span_cur == 0 and demoted_ok:
                        f.write(
                            f"{prev_stage}\t{stage}\t{rid}\tdemoted_quote_ok\t"
                            f"{span_prev}\t{span_cur}\t{glyph_prev}\t{glyph_cur}\t"
                            f"{int(isq_prev)}\t{int(isq_cur)}\t{int(demoted_ok)}\t"
                            f"{prev['speaker']}\t{cur['speaker']}\t"
                            f"{excerpt(prev['txt'])}\t{excerpt(cur['txt'])}\n"
                        )

        _qa_safe_log(f"[qa] wrote {report_path}")
        _qa_safe_log(f"[qa] wrote {events_path}")

    except Exception as e:
        _qa_safe_log(f"[qa] report failed: {e}")


def _attrib_dbg_reset():
    try:
        for k in (
            "attrib_harvest_hits",
            "attrib_harvest_overrides",
            "attrib_harvest_skips",
            "attrib_frag_hits",
            "surname_resolutions",
            "surname_ambiguous",
            "unknown_before",
            "unknown_after",
            "quotes_seen",
            "narrator_in_quotes",
        ):
            DBG[k] = 0
    except Exception:
        pass


def _attrib_eval_snapshot(rows, stage: str, outdir=None, prefix="attrib_eval"):
    """
    Quick counts for attribution health at a given stage.
    Writes a 1-line TSV and returns the dict.
    """
    d = {
        "stage": stage,
        "quotes": 0,
        "unknown": 0,
        "narrator_in_quotes": 0,
        "harvest_hits": DBG.get("attrib_harvest_hits", 0),
        "harvest_overrides": DBG.get("attrib_harvest_overrides", 0),
        "harvest_skips": DBG.get("attrib_harvest_skips", 0),
        "frag_hits": DBG.get("attrib_frag_hits", 0),
        "surname_resolutions": DBG.get("surname_resolutions", 0),
        "surname_ambiguous": DBG.get("surname_ambiguous", 0),
    }
    for r in rows or []:
        if looks_like_direct_speech(r.get("text") or ""):
            d["quotes"] += 1
            spk = (r.get("speaker") or "").strip()
            if spk in ("", "Unknown"):
                d["unknown"] += 1
            if spk == "Narrator":
                d["narrator_in_quotes"] += 1

    # keep an in-memory trail too
    try:
        DBG.setdefault("attrib_eval", []).append(d.copy())
    except Exception:
        pass

    # optional: write tiny TSV
    try:
        if outdir:
            import os

            os.makedirs(outdir, exist_ok=True)
            fn = os.path.join(outdir, f"{prefix}.{stage}.tsv")
            with open(fn, "w", encoding="utf-8") as f:
                keys = [
                    "stage",
                    "quotes",
                    "unknown",
                    "narrator_in_quotes",
                    "harvest_hits",
                    "harvest_overrides",
                    "harvest_skips",
                    "frag_hits",
                    "surname_resolutions",
                    "surname_ambiguous",
                ]
                f.write("\t".join(keys) + "\n")
                f.write("\t".join(str(d[k]) for k in keys) + "\n")
    except Exception:
        pass
    return d


# ===== logger mini-pack =====
# safe globals
try:
    DBG
except NameError:
    DBG = {}
_ATTRIB_OPS = []  # collected ops we write at the end


def dbg_inc(key: str, n: int = 1):
    try:
        DBG[key] = DBG.get(key, 0) + n
    except Exception:
        pass


def _ensure_rid(row: dict):
    """Guarantee a stable id for TSVs; keep any existing."""
    rid = row.get("_rid")
    if rid is None:
        rid = row["_rid"] = id(
            row
        )  # fallback; better if you already assign rids earlier
    return rid


def _glyph_budget(rows):
    """Count visible quote chars for budget checks."""
    if not rows:
        return 0
    QUOTES = {'"', "“", "”", "‘", "’", "«", "»"}
    total = 0
    for r in rows:
        for ch in r.get("text") or "":
            if ch in QUOTES:
                total += 1
    return total


def log_attrib_op(
    stage: str,
    op: str,
    row: dict,
    prev_sp: str,
    new_sp: str,
    reason: str,
    idx: int | None = None,
):
    """Append a row-level attribution operation to the in-memory buffer."""
    try:
        rid = _ensure_rid(row)
        txt = (row.get("text") or "").replace("\t", " ").replace("\n", " ")
        _ATTRIB_OPS.append(
            {
                "stage": stage or "",
                "op": op or "",
                "rid": rid,
                "prev": prev_sp or "",
                "new": new_sp or "",
                "reason": reason or "",
                "idx": -1 if idx is None else idx,
                "text": txt[:240],
            }
        )
    except Exception:
        pass


def apply_speaker(
    row: dict, who: str, reason: str, stage: str = "", idx: int | None = None
) -> bool:
    """
    Centralized setter+logger+lock:
      - only overwrites Unknown/Narrator/empty or same speaker
      - locks the row
      - logs TSV + DBG counters
    Returns True if set/locked, False if refused (conflict).
    """
    if not row or not who:
        return False
    prev = (row.get("speaker") or "").strip()
    if prev in ("", "Unknown", "Narrator") or prev == who:
        row["speaker"] = who
        row["_lock_speaker"] = True
        row["_locked_to"] = who
        row["_lock_reason"] = reason
        dbg_inc("speaker_sets")
        dbg_inc("speaker_locks")
        log_attrib_op(stage, "set_speaker", row, prev, who, reason, idx)
        return True
    else:
        dbg_inc("speaker_skips_conflict")
        log_attrib_op(stage, "skip_conflict", row, prev, who, reason, idx)
        return False


def _emit_attrib_ops(output_dir: str, prefix: str):
    """Write book_input.attrib_ops.tsv (or <prefix>.attrib_ops.tsv) once at the end."""
    try:
        if not _ATTRIB_OPS:
            return
        path = os.path.join(output_dir, f"{prefix}.attrib_ops.tsv")
        with open(path, "w", encoding="utf-8") as f:
            f.write("stage\top\trid\tprev\tnew\treason\tidx\ttext\n")
            for e in _ATTRIB_OPS:
                f.write(
                    f"{e['stage']}\t{e['op']}\t{e['rid']}\t{e['prev']}\t{e['new']}\t{e['reason']}\t{e['idx']}\t{e['text']}\n"
                )
        log(f"[attrib-ops] wrote {os.path.basename(path)} | ops={len(_ATTRIB_OPS)}")
    except Exception as e:
        log(f"[attrib-ops] write failed: {e}")


# ===== /logger mini-pack =====

# --- Attribution logging helpers (wrapper + alias) ---


def record_attrib_op_row(
    stage: str,
    op: str,
    row: dict,
    prev: str,
    new: str,
    reason: str,
    idx: int | None = None,
) -> None:
    """Convenience wrapper that extracts rid/text from the row, then forwards to record_attrib_op()."""
    try:
        rid = row.get("_rid", "")
        text = (row.get("text") or "").replace("\n", " ")[:200]
    except Exception:
        rid, text = "", ""
    record_attrib_op(
        stage=stage,
        op=op,
        rid=rid,
        prev=prev,
        new=new,
        reason=reason,
        idx=idx,
        text=text,
    )


# If some parts of the code call log_attrib_op(...), alias it to the wrapper so they continue to work:
if "log_attrib_op" not in globals():

    def log_attrib_op(stage, op, row, prev, new, reason, idx=None):
        record_attrib_op_row(stage, op, row, prev, new, reason, idx)


# ---- attribution ops logger -----------------------------------------------
# one central buffer; flushed by _emit_attrib_ops(output_dir, prefix)
try:
    _ATTRIB_OPS
except NameError:
    _ATTRIB_OPS = []


def dbg_inc(key: str, by: int = 1) -> None:
    """Tiny helper so we don't crash if DBG isn't defined yet."""
    try:
        DBG[key] = DBG.get(key, 0) + by
    except Exception:
        pass


def _safe_excerpt(text: str, n: int = 120) -> str:
    t = (text or "").replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _row_rid(row: dict) -> str:
    """Best-effort row id for logging."""
    if not isinstance(row, dict):
        return ""
    return str(row.get("_rid") or row.get("rid") or "")


def record_attrib_op(
    stage: str,
    op: str = "",
    rid: str | None = None,
    prev: str = "",
    new: str = "",
    reason: str = "",
    idx: int | None = None,
    text: str = "",
) -> None:
    """
    Generic recorder you can call from any heuristic (e.g., demotions, harvests).
    Writes a single row into _ATTRIB_OPS (flushed by _emit_attrib_ops).
    """
    try:
        _ATTRIB_OPS.append(
            {
                "stage": stage or "",
                "op": op or "",
                "rid": str(rid or ""),
                "prev": (prev or ""),
                "new": (new or ""),
                "reason": (reason or ""),
                "idx": "" if idx is None else str(idx),
                "text": _safe_excerpt(text),
            }
        )
    except Exception:
        # don't let logging break the pipeline
        pass


def log_attrib_op(
    stage: str,
    op: str,
    row: dict,
    prev: str,
    new: str,
    reason: str,
    idx: int | None = None,
) -> None:
    """
    Row-aware wrapper used by apply_speaker(). Keeps the exact same TSV schema.
    """
    try:
        record_attrib_op(
            stage=stage,
            op=op,
            rid=_row_rid(row),
            prev=(prev or ""),
            new=(new or ""),
            reason=(reason or ""),
            idx=idx,
            text=(row.get("text") or ""),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------

# ================= QUOTE AUDIT HARNESS =================
AUDIT_QUOTES = True  # master switch
HARD_FAIL_ON_QUOTE_LOSS = False  # raise on first suspicious change
AUTO_RESTORE_ON_QUOTE_LOSS = True  # try to revert to prior text if quotes vanish
AUDIT_MAX_EXCERPT = 160  # how much text to show in logs
AUDIT_FILE_BASENAME = ".quote_audit.tsv"  # saved next to other outputs


def _qa_log(msg: str):
    try:
        log(f"[qaudit] {msg}")
    except Exception:
        print(f"[qaudit] {msg}")


def _qa_quote_counts(t: str):
    """Return (ascii_dq, smart_open, smart_close, guillemet_open, guillemet_close, total)."""
    if not t:
        return (0, 0, 0, 0, 0, 0)
    ascii_dq = t.count('"')
    smart_o = t.count("\u201c")  # “
    smart_c = t.count("\u201d")  # ”
    guil_o = t.count("\u00ab")  # «
    guil_c = t.count("\u00bb")  # »
    total = ascii_dq + smart_o + smart_c + guil_o + guil_c
    return (ascii_dq, smart_o, smart_c, guil_o, guil_c, total)


def _trace_glyph_budget(stage: str, rows: list[dict]):
    try:
        b = _glyph_budget(rows)
        log(f"[budget] {stage}: quote_glyphs={b}")
        DBG.setdefault("budget_trace", []).append((stage, b))
    except Exception:
        pass


def _qa_balance_status(t: str):
    """'balanced' if _quote_spans finds at least one span and all spans close; else 'unbalanced' or 'none'."""
    s = _norm_unicode_quotes(t or "")
    spans = _quote_spans(s)
    if not spans:
        # still treat as 'unbalanced' if there are any raw quote glyphs present
        return "none" if _qa_quote_counts(s)[-1] == 0 else "unbalanced"
    # crude balance check: if tail after last close has another opener, call unbalanced
    last_end = spans[-1][1]
    tail = s[last_end:]
    return (
        "balanced"
        if ("\u201c" not in tail and '"' not in tail and "\u00ab" not in tail)
        else "unbalanced"
    )


def _qa_excerpt(t: str):
    t = (t or "").replace("\n", " ⏎ ")
    return t[:AUDIT_MAX_EXCERPT] + ("…" if len(t) > AUDIT_MAX_EXCERPT else "")


def _qa_assign_row_ids(results):
    """Ensure each row has a stable _rid."""
    rid_counter = DBG.get("_qa_next_rid", 1)
    out = []
    for r in results:
        rr = dict(r)
        if "_rid" not in rr:
            rr["_rid"] = rid_counter
            rid_counter += 1
        out.append(rr)
    DBG["_qa_next_rid"] = rid_counter
    return out


def _qa_snapshot(stage: str, results):
    """Build a compact snapshot for comparison."""
    snap = []
    for idx, r in enumerate(results):
        txt = r.get("text") or ""
        isq = bool(looks_like_direct_speech(txt))
        spans = _quote_spans(_norm_unicode_quotes(txt))
        counts = _qa_quote_counts(txt)
        bal = _qa_balance_status(txt)
        snap.append(
            {
                "i": idx,
                "rid": r.get("_rid"),
                "is_quote": isq,
                "span_cnt": len(spans),
                "glyph_cnt": counts[-1],
                "bal": bal,
                "speaker": r.get("speaker") or "",
                "txt": txt,
            }
        )
    return snap


def _qa_compare(prev_stage: str, prev, stage: str, cur, outdir=None, prefix=""):
    """
    RID-aware comparison between audit snapshots.
    Flags 'lost_spans' ONLY when a RID that previously had spans now has zero spans across
    ALL of its current rows AND it was not an intentional demotion (_qa_demoted_quote=True).
    """
    if not (prev and cur):
        return

    from collections import defaultdict

    def _group(snap):
        g = defaultdict(list)
        for row in snap:
            g[row.get("rid")].append(row)
        return g

    prev_g = _group(prev)
    cur_g = _group(cur)

    tsv_path = None
    if outdir:
        tsv_path = os.path.join(outdir, f"{prefix}{AUDIT_FILE_BASENAME}")

    def _write_tsv_row(fields):
        if not tsv_path:
            return
        try:
            exists = os.path.exists(tsv_path)
            with open(tsv_path, "a", encoding="utf-8") as f:
                if not exists:
                    f.write(
                        "prev_stage\tstage\trid\tissue\tspan_prev\tspan_cur\tglyph_prev\tglyph_cur\tbal_prev\tbal_cur\tisq_prev\tisq_cur\tspeaker_prev\tspeaker_cur\texcerpt_prev\texcerpt_cur\n"
                    )
                f.write("\t".join(map(str, fields)) + "\n")
        except Exception as e:
            _qa_log(f"tsv write failed: {e}")

    lost_spans = lost_glyph = bal_drop = flag_flip = 0

    for rid in set(prev_g.keys()) & set(cur_g.keys()):
        prev_rows = prev_g[rid]
        cur_rows = cur_g[rid]

        span_prev = sum(r["span_cnt"] for r in prev_rows)
        span_cur = sum(r["span_cnt"] for r in cur_rows)
        glyph_prev = sum(r["glyph_cnt"] for r in prev_rows)
        glyph_cur = sum(r["glyph_cnt"] for r in cur_rows)
        bal_prev = (
            "balanced"
            if any(r["bal"] == "balanced" for r in prev_rows)
            else (
                "unbalanced"
                if any(r["bal"] == "unbalanced" for r in prev_rows)
                else "none"
            )
        )
        bal_cur = (
            "balanced"
            if any(r["bal"] == "balanced" for r in cur_rows)
            else (
                "unbalanced"
                if any(r["bal"] == "unbalanced" for r in cur_rows)
                else "none"
            )
        )
        isq_prev = any(r["is_quote"] for r in prev_rows)
        isq_cur = any(r["is_quote"] for r in cur_rows)

        # Was this RID intentionally demoted? (e.g., "said Zack" demoted to Narrator)
        demoted_ok = any(r.get("_qa_demoted_quote") for r in cur_rows)

        p0 = prev_rows[0]
        c0 = cur_rows[0]
        spk_prev = p0.get("speaker", "")
        spk_cur = c0.get("speaker", "")
        ex_prev = _qa_excerpt(p0.get("txt", ""))
        ex_cur = _qa_excerpt(c0.get("txt", ""))

        issue_tags = []

        if span_prev > 0 and span_cur == 0:
            if demoted_ok:
                issue_tags.append("demoted_quote_ok")
            else:
                issue_tags.append("lost_spans")
                lost_spans += 1

        if glyph_prev > glyph_cur:
            if not demoted_ok:
                issue_tags.append("lost_glyphs")
                lost_glyph += 1

        if bal_prev == "balanced" and bal_cur != "balanced":
            if not demoted_ok:
                issue_tags.append("bal_drop")
                bal_drop += 1

        if isq_prev and (not isq_cur) and (span_cur > 0):
            issue_tags.append("flag_flip")
            flag_flip += 1

        if issue_tags:
            issue = "+".join(issue_tags)
            _qa_log(
                f"{prev_stage} -> {stage} | {issue} | rid={rid} | spans {span_prev}→{span_cur} glyphs {glyph_prev}→{glyph_cur} bal {bal_prev}→{bal_cur} isq {isq_prev}→{isq_cur} | prev:`{ex_prev}` | cur:`{ex_cur}`"
            )
            _write_tsv_row(
                [
                    prev_stage,
                    stage,
                    rid,
                    issue,
                    span_prev,
                    span_cur,
                    glyph_prev,
                    glyph_cur,
                    bal_prev,
                    bal_cur,
                    isq_prev,
                    isq_cur,
                    spk_prev,
                    spk_cur,
                    ex_prev,
                    ex_cur,
                ]
            )

            if HARD_FAIL_ON_QUOTE_LOSS and ("lost_spans" in issue_tags):
                raise RuntimeError(
                    f"Quote loss at stage {stage} (from {prev_stage}) rid={rid} issue={issue}"
                )

    if (lost_spans + lost_glyph + bal_drop + flag_flip) > 0:
        _qa_log(
            f"SUMMARY {prev_stage} → {stage}: lost_spans={lost_spans} lost_glyphs={lost_glyph} bal_drop={bal_drop} flag_flip={flag_flip}"
        )


def _qaudit(stage: str, results, outdir=None, prefix=""):
    """
    Quote audit tap: snapshot after `stage`, compare to previous stage, optionally
    auto-restore any rows that *lost* quote spans/glyphs. Uses stable _rid so it
    works even when earlier stages split/merge/reorder rows.

    This version also feeds the Quote Integrity Evaluator series so we can emit
    {prefix}quote_report.tsv and {prefix}quote_events.tsv at the end.
    """
    if not AUDIT_QUOTES:
        return results

    # Ensure stable IDs so we can track rows across stages
    results = _qa_assign_row_ids(results)

    # NEW: collect a stage snapshot for the evaluator (RID-aware)
    try:
        _qa_collect_stage(stage, results)
    except Exception as e:
        _qa_safe_log(f"[qa] collect@{stage} failed: {e}")

    # Build the index-aligned audit snapshot for compare/auto-restore
    cur = _qa_snapshot(stage, results)

    # Compare to previous snapshot (RID-aware summary + TSV logging)
    prev = DBG.get("_qa_prev_snap")
    prev_stage = DBG.get("_qa_prev_stage", "start")
    _qa_compare(prev_stage, prev, stage, cur, outdir, prefix)

    # Robust auto-restore by _rid (safer than index-based restore)
    if AUTO_RESTORE_ON_QUOTE_LOSS and prev:
        # map current positions by rid
        cur_pos_by_rid = {r["rid"]: idx for idx, r in enumerate(cur)}
        prev_by_rid = {r["rid"]: r for r in prev}

        restores = 0
        for rid, a in prev_by_rid.items():
            idx = cur_pos_by_rid.get(rid)
            if idx is None:
                # row removed/merged; we can't restore it here
                continue
            b = cur[idx]
            # restore only when previous had spans and current has none + glyph drop
            if (
                (a["span_cnt"] > 0)
                and (b["span_cnt"] == 0)
                and (a["glyph_cnt"] > b["glyph_cnt"])
            ):
                try:
                    results[idx]["text"] = a["txt"]
                    results[idx]["is_quote"] = a["is_quote"]
                    restores += 1
                    _qa_log(f"{stage}: AUTO-RESTORE rid={rid} idx={idx}")
                except Exception as e:
                    _qa_log(f"{stage}: restore failed rid={rid} idx={idx}: {e}")

        if restores:
            # refresh the audit snapshot so the next comparison uses restored text
            cur = _qa_snapshot(stage + " (restored)", results)
            # NEW: also collect a post-restore snapshot for the evaluator
            try:
                _qa_collect_stage(stage + " (restored)", results)
            except Exception as e:
                _qa_safe_log(f"[qa] collect@{stage} (restored) failed: {e}")

    DBG["_qa_prev_snap"] = cur
    DBG["_qa_prev_stage"] = stage
    return results


# =======================================================


# ===== TRACE PACK: behavior-neutral instrumentation =====

# quote glyph helpers
_DQ = {'"', "“", "”"}


def _dq_count(s: str) -> int:
    return sum(1 for ch in (s or "") if ch in _DQ)


def _has_dq(s: str) -> bool:
    return any(ch in (s or "") for ch in _DQ)


def _quote_spans_simple(t: str):
    """Simple balanced-span finder for “ ” and ". No side effects, fast."""
    spans, stack = [], []
    for i, ch in enumerate(t or ""):
        if ch in {"“", '"'}:
            stack.append(i)
        elif ch in {"”", '"'} and stack:
            lo = stack.pop()
            spans.append((lo, i + 1))
    return spans


def _metrics(rows):
    rows = rows or []
    total = len(rows)
    qrows = sum(1 for r in rows if r.get("is_quote"))
    narr_has_dq = sum(
        1 for r in rows if (not r.get("is_quote")) and _has_dq(r.get("text"))
    )
    unknown_q = sum(
        1
        for r in rows
        if r.get("is_quote") and (r.get("speaker") in (None, "", "Unknown"))
    )
    narr_q = sum(
        1 for r in rows if r.get("is_quote") and (r.get("speaker") == "Narrator")
    )
    glyphs = sum(_dq_count(r.get("text")) for r in rows)
    multi_span_quotes = sum(
        1
        for r in rows
        if r.get("is_quote") and len(_quote_spans_simple(r.get("text"))) > 1
    )
    return {
        "rows": total,
        "quote_rows": qrows,
        "glyphs": glyphs,
        "unknown_quote_rows": unknown_q,
        "narration_with_quote_glyphs": narr_has_dq,
        "multi_span_quote_rows": multi_span_quotes,
    }


# suspicious seams: ”he | ”she | "he (no space) etc.
_SEAM_RX = re.compile(r'[”"]\s*[a-z]', re.MULTILINE)


def trace_init(output_dir, prefix, rows):
    """
    Create trace files (if missing) and stash outdir/prefix so other helpers
    (e.g., trace_note) can append to stage_stats.tsv without extra args.
    """
    import csv
    import os

    os.makedirs(output_dir or ".", exist_ok=True)

    # --- main trace table (rollup stats per stage) ---
    path = os.path.join(output_dir, f"{prefix}.trace.tsv")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(
                [
                    "stage",
                    "rows",
                    "quote_rows",
                    "glyphs",
                    "unknown_quote_rows",
                    "narration_with_quote_glyphs",
                    "multi_span_quote_rows",
                    "time_ms",
                ]
            )

    # --- suspects table (problem rows snapshots) ---
    s_path = os.path.join(output_dir, f"{prefix}.suspects.tsv")
    if not os.path.exists(s_path):
        with open(s_path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(
                ["stage", "idx", "reason", "speaker", "is_quote", "excerpt"]
            )

    # --- seams table (edge rows around merges/splits) ---
    seam_path = os.path.join(output_dir, f"{prefix}.seams.tsv")
    if not os.path.exists(seam_path):
        with open(seam_path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(
                ["stage", "idx", "speaker", "is_quote", "excerpt"]
            )

    # --- NEW: stage_stats.tsv (for free-form notes via trace_note) ---
    ss_path = os.path.join(output_dir, f"{prefix}.stage_stats.tsv")
    if not os.path.exists(ss_path):
        with open(ss_path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(["stage", "kind", "details"])

    # --- NEW (the one-liner you asked for): stash for later helpers ---
    try:
        DBG["_trace_outdir"] = output_dir
        DBG["_trace_prefix"] = prefix
    except NameError:
        # If DBG doesn't exist yet, create it
        try:
            globals()["DBG"] = {"_trace_outdir": output_dir, "_trace_prefix": prefix}
        except Exception:
            pass

    # Optional: keep an initial quote-glyph budget snapshot (handy for loss checks)
    try:

        def _glyphs_total(rs):
            if not rs:
                return 0
            qchars = ['"', "“", "”", "‘", "’", "«", "»"]
            total = 0
            for r in rs:
                t = r.get("text") or ""
                total += sum(t.count(ch) for ch in qchars)
            return total

        DBG["_glyph_budget_init"] = _glyphs_total(rows or [])
    except Exception:
        pass

    # trace log
    try:
        log(f"[trace_init] prefix={prefix} outdir={output_dir}")
    except Exception:
        pass


def trace_stage(stage, rows, output_dir, prefix, t_ms=None, sample_limit=12):
    """Record metrics + a few suspicious rows. Returns rows unchanged."""
    m = _metrics(rows)
    with open(
        os.path.join(output_dir, f"{prefix}.trace.tsv"),
        "a",
        encoding="utf-8",
        newline="",
    ) as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(
            [
                stage,
                m["rows"],
                m["quote_rows"],
                m["glyphs"],
                m["unknown_quote_rows"],
                m["narration_with_quote_glyphs"],
                m["multi_span_quote_rows"],
                t_ms or 0,
            ]
        )
    # suspects: narration that contains quotes, or quote rows with no glyphs, or narrator as quote
    sus = []
    for i, r in enumerate(rows or []):
        t = (r.get("text") or "").strip()
        if not t:
            continue
        if (not r.get("is_quote")) and _has_dq(t):
            sus.append((i, "narr_with_quote_glyph", r))
        elif r.get("is_quote") and _dq_count(t) == 0:
            sus.append((i, "quote_without_glyph", r))
        elif r.get("is_quote") and (r.get("speaker") == "Narrator"):
            sus.append((i, "quote_speaker_is_narrator", r))
        if len(sus) >= sample_limit:
            break
    if sus:
        with open(
            os.path.join(output_dir, f"{prefix}.suspects.tsv"),
            "a",
            encoding="utf-8",
            newline="",
        ) as f:
            w = csv.writer(f, delimiter="\t")
            for i, reason, r in sus:
                w.writerow(
                    [
                        stage,
                        i,
                        reason,
                        r.get("speaker", ""),
                        int(bool(r.get("is_quote"))),
                        (r.get("text") or "")[:180],
                    ]
                )
    # seams (no behavior change)
    seam_hits = 0
    with open(
        os.path.join(output_dir, f"{prefix}.seams.tsv"),
        "a",
        encoding="utf-8",
        newline="",
    ) as f:
        w = csv.writer(f, delimiter="\t")
        for i, r in enumerate(rows or []):
            t = r.get("text") or ""
            if _SEAM_RX.search(t):
                w.writerow(
                    [
                        stage,
                        i,
                        r.get("speaker", ""),
                        int(bool(r.get("is_quote"))),
                        t[
                            max(0, _SEAM_RX.search(t).start() - 20) : _SEAM_RX.search(
                                t
                            ).end()
                            + 40
                        ].replace("\n", " "),
                    ]
                )
                seam_hits += 1
                if seam_hits >= sample_limit:
                    break
    return rows


# Optional lightweight timer wrapper (no kwargs issues)
def _profile(stage_name, fn, rows, output_dir, prefix, *args):
    t0 = time.time()
    out = fn(rows, *args)
    dt = int((time.time() - t0) * 1000)
    trace_stage(stage_name, out, output_dir, prefix, t_ms=dt)
    return out


# --- Heuristic Filters ---
SHORT_DIALOGUE = {
    "ok",
    "no",
    "yes",
    "yeah",
    "yep",
    "nah",
    "shit",
    "fuck",
    "damn",
    "hi",
    "hey",
    "bye",
    "hmm",
    "uh",
    "um",
}

# --- Attribution fragment size guards (used by _looks_like_attribution_fragment) ---
MAX_ATTRIB_FRAGMENT_LEN = 120  # characters; keep short tails like "— said Zack."
MAX_ATTRIB_FRAGMENT_WORDS = 24  # words; longer is probably narration, not a tail

# === Attribution fragment size guards (pull existing values if set) ===
MAX_ATTRIB_FRAGMENT_LEN = globals().get("MAX_ATTRIB_FRAGMENT_LEN", 120)
MAX_ATTRIB_FRAGMENT_WORDS = globals().get("MAX_ATTRIB_FRAGMENT_WORDS", 24)

# Build the verb set from your global list if available; else a tight core
_AF_VERBS = set(globals().get("_ATTRIB_VERBS", [])) or {
    "said",
    "says",
    "ask",
    "asks",
    "asked",
    "reply",
    "replies",
    "replied",
    "answer",
    "answers",
    "answered",
    "called",
    "yelled",
    "shouted",
    "cried",
    "whispered",
    "murmured",
    "muttered",
    "snapped",
    "retorted",
    "laughed",
    "sobbed",
    "hissed",
    "breathed",
    "noted",
    "observed",
    "remarked",
    "insisted",
    "countered",
    "agreed",
    "warned",
    "offered",
    "begged",
    "demanded",
    "protested",
    "announced",
    "explained",
    "declared",
    "continued",
    "interjected",
    "interrupted",
    "conceded",
    "promised",
    "pleaded",
    "went",
    "went on",
    "rejoined",
    "stated",
}

# Compile the shared patterns only once
if "_AF_VERB_NAME_RX" not in globals():
    _AF_VERBS_RX = r"(?:%s)" % "|".join(
        sorted(map(re.escape, _AF_VERBS), key=len, reverse=True)
    )
    _AF_FILLER = (
        r"(?:\s+(?:[a-z]{1,12}|then|again|softly|quietly|firmly|simply|just)){0,3}"
    )
    _AF_PROPER = r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}"

    # Verb → Name  (e.g., ", said softly John Smith.")
    _AF_VERB_NAME_RX = re.compile(
        rf"^[—\-–—,\s]*(?P<verb>{_AF_VERBS_RX}){_AF_FILLER}\s+(?P<who>{_AF_PROPER})[\s,.\-–—:;!?]*$",
        re.IGNORECASE,
    )
    # Name → Verb  (e.g., ", John Smith said softly.")
    _AF_NAME_VERB_RX = re.compile(
        rf"^[—\-–—,\s]*(?P<who>{_AF_PROPER})\s+(?P<verb>{_AF_VERBS_RX}){_AF_FILLER}[\s,.\-–—:;!?]*$",
        re.IGNORECASE,
    )


_KINSHIP = {
    "Father",
    "Mother",
    "Mom",
    "Dad",
    "Daddy",
    "Mommy",
    "Grandpa",
    "Grandma",
    "Aunt",
    "Uncle",
    "Brother",
    "Sister",
    "Daughter",
    "Son",
    "Cousin",
}
_CAP_STOP = set(globals().get("_CAP_STOP", [])) | {
    # places & common cap junk
    "Apartment",
    "House",
    "Store",
    "Street",
    "Road",
    "Highway",
    "Bridge",
    "Center",
    "University",
    "County",
    "Jail",
    "Justice",
    "Court",
    "Toyota",
    "Oregon",
    "Astoria",
    "Seaside",
    "Gearhart",
    "Bay",
    "River",
    "The",
    "A",
    "An",
    "In",
    "On",
    "Of",
    "For",
    "To",
    "And",
    "But",
    "Or",
    "Cheap",
    "Furnished",
    "Broken",
    "Generic",
}

_POSSESSIVE_KINSHIP_RX = re.compile(
    rf"^[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+)*\s+['’]s\s+(?:{'|'.join(_KINSHIP)})\b"
)


def _is_possessive_kinship(s: str) -> bool:
    return bool(_POSSESSIVE_KINSHIP_RX.search(s or ""))


def _is_attrib_fragment_local(text: str, max_words: int = 24) -> bool:
    """
    Conservative detector for short attribution/action beats like:
      'said John Smith.' / 'asked his friend.' / 'Smith went on.'
      'laughed Jones bitterly.' / 'confirmed Smith.' / 'gasped Jones.' / 'nodded.'
    Returns True if likely a pure beat (no dialogue), short, and ends cleanly.
    """
    import re

    t = (text or "").strip()
    if not t:
        return False

    # Hard disqualifiers
    if any(q in t for q in ('"', "“", "”", "«", "»", "‘", "’")):
        return False
    # avoid long sentences
    if len(t.split()) > max_words:
        return False

    # Common “speech” and action verbs seen in your rows
    VERBS = r"(?:said|ask(?:ed|s)|repl(?:y|ied)|retort(?:ed|s)|demand(?:ed|s)|"
    VERBS += r"explain(?:ed|s)|tell(?:ed|s|told)|murmur(?:ed|s)|mutter(?:ed|s)|"
    VERBS += r"whisper(?:ed|s)|shout(?:ed|s)|yell(?:ed|s)|scream(?:ed|s)|"
    VERBS += r"snarl(?:ed|s)|snap(?:ped|s)|gasp(?:ed|s)|laugh(?:ed|s)|"
    VERBS += r"sob(?:bed|s)|cry(?:ed|ies|cried)|"
    VERBS += r"went\s+on|continued|added|repeated|insisted|"
    VERBS += r"nodd(?:ed|s)|shrugg(?:ed|s)|"
    VERBS += r"confirmed|reminded|persisted|interjected|queried)"

    NAME = r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
    PRON = r"(?:he|she|they|we|I|you)"
    MOD = r"(?:\s+\w+){0,6}"  # light adverbials/adjectives window
    END = r"(?:[.!?…])?"  # tolerant ending

    # Patterns:
    #   said X. / asked his friend NAME. / VERB alone. / NAME VERB ...
    patts = [
        rf"^(?:[-—–]\s*)?(?:{PRON}|{NAME}|(?:his|her|their)\s+\w+(?:\s+\w+)*){MOD}\s+{VERBS}{MOD}{END}$",
        rf"^(?:[-—–]\s*)?{VERBS}{MOD}(?:{PRON}|{NAME}|(?:his|her|their)\s+\w+(?:\s+\w+)*){MOD}{END}$",
        rf"^(?:[-—–]\s*)?{VERBS}{MOD}{END}$",
        rf"^(?:[-—–]\s*)?{NAME}{MOD}\s+{VERBS}{MOD}{END}$",
    ]
    for p in patts:
        if re.match(p, t, flags=re.I):
            return True
    return False


# Expanded set of common attribution verbs
_ATTRIB_VERBS = [
    "said",
    "asked",
    "replied",
    "whispered",
    "shouted",
    "cried",
    "muttered",
    "continued",
    "responded",
    "told",
    "called",
    "answered",
    "added",
    "hissed",
    "growled",
    "yelled",
    "snapped",
    "barked",
    "ordered",
    "pleaded",
    "exclaimed",
    "protested",
    "remarked",
    "murmured",
    "stated",
    "announced",
    "insisted",
    "suggested",
    "observed",
    "agreed",
    "retorted",
    "inquired",
    "interjected",
    "mused",
    "snorted",
    "grunted",
    "explained",
    "reminded",
    "nodded",
    "laughed",
    "smiled",
    "grinned",
    "shrugged",
    "sneered",
    "sighed",
    "rejoined",
    "countered",
    "noted",
    "admitted",
    "moaned",
    "clarified",
    "counseled",
    "jabbered",
    "yapped",
    "refuted",
    "pondered",
    "surmised",
    "verified",
    "guffawed",
    "tittered",
    "avowed",
    "convinced",
    "implored",
    "prodded",
    "insulted",
    "provoked",
    "smirked",
    "tempted",
    "grilled",
    "declared",
    "maintained",
    "vowed",
    "quizzed",
    "wondered",
    "hesitated",
    "warned",
    "croaked",
    "heaved",
    "lisped",
    "rattled on",
    "shrilled",
    "stuttered",
    "caterwauled",
    "condemned",
    "fumed",
    "raged",
    "scolded",
    "snarled",
    "threatened",
    "grimaced",
    "sniffed",
    "spluttered",
    "prayed",
    "squeaked",
    "worried",
    "whinged",
    "cackled",
    "congratulated",
    "gushed",
    "simpered",
    "whooped",
    "flattered",
    "purred",
    "swooned",
    "mumbled",
    "wished",
    "consoled",
    "sobbed",
    "wept",
    "marveled",
    "marvelled",
    "yelped",
    "yawned",
    "alliterated",
    "described",
    "emphasized",
    "imitated",
    "mouthed",
    "offered",
    "pressed",
    "recalled",
    "remembered",
    "rhymed",
    "tried",
    "accepted",
    "acknowledged",
    "affirmed",
    "assumed",
    "conferred",
    "confessed",
    "confirmed",
    "justified",
    "settled",
    "understood",
    "undertook",
    "accused",
    "bossed",
    "carped",
    "censured",
    "criticized",
    "gawped",
    "glowered",
    "grumbled",
    "remonstrated",
    "reprimanded",
    "scoffed",
    "seethed",
    "ticked off",
    "told off",
    "upbraided",
    "contemplated",
    "addressed",
    "advertised",
    "articulated",
    "bragged",
    "commanded",
    "confided",
    "decided",
    "dictated",
    "ended",
    "exacted",
    "finished",
    "informed",
    "made known",
    "necessitated",
    "pointed out",
    "promised",
    "reassured",
    "reported",
    "specified",
    "attracted",
    "requested",
    "wanted",
    "beamed",
    "blurted",
    "broadcasted",
    "burst",
    "cheered",
    "chortled",
    "chuckled",
    "cried out",
    "crooned",
    "crowed",
    "emitted",
    "giggled",
    "hollered",
    "howled",
    "praised",
    "preached",
    "presented",
    "proclaimed",
    "professed",
    "promulgated",
    "quaked",
    "ranted",
    "rejoiced",
    "roared",
    "screamed",
    "shrieked",
    "swore",
    "thundered",
    "trilled",
    "trumpeted",
    "vociferated",
    "wailed",
    "yawped",
    "yowled",
    "cautioned",
    "shuddered",
    "trembled",
    "comforted",
    "empathized",
    "invited",
    "proffered",
    "released",
    "volunteered",
    "advised",
    "alleged",
    "appealed",
    "asserted",
    "assured",
    "avered",
    "beckoned",
    "begged",
    "beseeched",
    "cajoled",
    "claimed",
    "conceded",
    "concluded",
    "concurred",
    "contended",
    "defended",
    "disposed",
    "encouraged",
    "entreated",
    "held",
    "hinted",
    "implied",
    "importuned",
    "inclined",
    "indicated",
    "pleaded",
    "postulated",
    "premised",
    "presupposed",
    "stressed",
    "touted",
    "vouched for",
    "wheedled",
    "chimed in",
    "circulated",
    "disseminated",
    "distributed",
    "expressed",
    "made public",
    "passed on",
    "publicized",
    "published",
    "put forth",
    "put out",
    "quipped",
    "quoted",
    "reckoned that",
    "required",
    "requisitioned",
    "taunted",
    "teased",
    "exposed",
    "joked",
    "leered",
    "lied",
    "mimicked",
    "mocked",
    "agonized",
    "bawled",
    "blubbered",
    "grieved",
    "groaned",
    "lamented",
    "mewled",
    "mourned",
    "puled",
    "denoted",
    "disclosed",
    "divulged",
    "imparted",
    "proposed",
    "revealed",
    "shared",
    "solicited",
    "sought",
    "testified",
    "transferred",
    "transmitted",
    "doubted",
    "faltered",
    "fretted",
    "guessed",
    "hypothesized",
    "lilted",
    "quavered",
    "queried",
    "questioned",
    "speculated",
    "supposed",
    "trailed off",
    "breathed",
    "choked",
    "drawled",
    "echoed",
    "keened",
    "panted",
    "sang",
    "sniffled",
    "sniveled",
    "uttered",
    "voiced",
    "whimpered",
    "whined",
    "probed",
    "backtracked",
    "communicated",
    "considered",
    "elaborated",
    "enunciated",
    "expounded",
    "greeted",
    "mentioned",
    "orated",
    "persisted",
    "predicted",
    "pronounced",
    "recited",
    "reckoned",
    "related",
    "slurred",
    "vocalized",
    "approved",
    "bubbled",
    "chattered",
    "complimented",
    "effused",
    "thanked",
    "yammered",
    "apologized",
    "cursed",
    "exploded",
    "screeched",
    "spat",
    "bleated",
    "exhaled",
    "groused",
    "gulped",
    "squalled",
    "warbled",
    "bloviated",
    "exhorted",
    "gloated",
    "moralized",
    "sermonized",
    "swaggered",
    "swallowed",
    "vacillated",
    "derided",
    "jeered",
    "heckled",
    "lampooned",
    "parodied",
    "ridiculed",
    "satirized",
    "scorned",
    "spoofed",
    "snickered",
    "challenged",
    "interrogated",
    "puzzled",
    "prattled",
    "preened",
    "cooed",
    "bantered",
    "blathered",
    "blithered",
    "hooted",
    "jested",
    "soothed",
    "chorused",
    "piped",
    "yakked",
    "gurgled",
    "disparaged",
    "rejected",
    "griped",
    "reproached",
    "berated",
    "sassed",
    "chided",
    "clucked",
    "corrected",
    "rebuffed",
    "gawked",
    "spouted",
    "let slip",
    "gaped",
    "ogled",
    "gasped",
    "spilled",
    "blanched",
    "spooked",
    "paled",
    "brooded",
    "panicked",
    "tensed",
    "cowered",
    "quaked",
    "cringed",
    "recoiled",
    "shivered",
    "depicted",
    "elucidated",
    "defined",
    "illustrated",
    "delineated",
    "portrayed",
    "returned",
    "advanced",
    "corroborated",
    "posited",
    "attested",
    "authenticated",
    "bespoke",
    "substantiated",
    "certified",
    "critiqued",
    "gauged",
    "appraised",
    "estimated",
    "assayed",
    "evaluated",
    "interpreted",
    "assessed",
    "examined",
    "judged",
    "explicated",
    "reviewed",
    "figured",
    "surveyed",
    "adumbrated",
    "alluded",
    "connoted",
    "signaled",
    "foreshadowed",
    "insinuated",
    "signified",
    "forewarned",
    "intimated",
    "heralded",
    "portended",
    "adjured",
    "inspected",
    "perused",
    "researched",
    "explored",
    "searched",
    "owned",
    "recognized",
    "betrayed",
    "acquiesced",
    "bellyached",
    "bickered",
    "blabbed",
    "blabbered",
    "brayed",
    "broke in",
    "coached",
    "coaxed",
    "contradicted",
    "contributed",
    "deduced",
    "demurred",
    "disagreed",
    "dissented",
    "dribbled",
    "droned",
    "ejaculated",
    "exulted",
    "fussed",
    "gibbered",
    "gibed",
    "guaranteed",
    "harangued",
    "huffed",
    "intoned",
    "joined in",
    "nattered",
    "neighed",
    "nitpicked",
    "objected",
    "opined",
    "pestered",
    "pled",
    "pledged",
    "prated",
    "resounded",
    "resumed",
    "retaliated",
    "shot",
    "tattled",
    "theorized",
    "toasted",
    "tutted",
    "weighed in",
    "whickered",
    "whinnied",
    "brought forth",
    "denounced",
    "disrupted",
    "enjoined",
    "condescended",
    "contested",
    "feared",
    "foretold",
    "cracked",
    "haggled",
    "hedged",
    "relented",
    "petitioned",
    "inferred",
    "propounded",
    "intimidated",
    "itemized",
    "proved",
    "sanctioned",
    "quibbled",
    "rambled",
    "reaffirmed",
    "reciprocated",
    "referred",
    "regretted",
    "restated",
    "ruled",
    "stipulated",
    "twitted",
    "whistled",
    "thought",
    "wrangled",
    "went on",
    "interposed",
    "urged",
    "demanded",
    "began",
    "spoke up",
    "went on grimly",
    "said simply",
    "said softly",
]

# ======= VERB REGEX BUILDER  =======


# ---- Attribution fragment regexes (single source of truth) -------------------
def _ensure_attrib_fragment_regexes():
    """
    Initializes shared regexes used by _speaker_from_attrib_fragment and
    _speaker_verb_from_attrib_fragment. Safe to call multiple times.
    Also aliases _SVAF_* to _AF_* for backward-compatibility.

    Notes:
      - Rebuilds patterns if the underlying verb list changes (tracked by _AF_VERBS_KEY).
      - Uses _ATTRIB_VERBS ∪ _MULTIWORD_VERBS_SAFE ∪ _MULTIWORD_VERBS_PREP.
      - Blocks prepositional objects in VERB→NAME ('said to X', 'yelled at Y').
    """
    import re

    global _NAME_RX, _ATTRIB_VERBS_RX_STRICT
    global _AF_VERB_NAME_RX, _AF_NAME_VERB_RX
    global _SVAF_VERB_NAME_RX, _SVAF_NAME_VERB_RX
    global _AF_VERBS_KEY

    proper_token = r"[A-Z][A-Za-z'’\-]+"
    _NAME_RX = rf"{proper_token}(?:\s+{proper_token}){{0,2}}"

    _verbs_fallback = {
        "said",
        "says",
        "say",
        "ask",
        "asks",
        "asked",
        "reply",
        "replies",
        "replied",
        "answer",
        "answers",
        "answered",
        "tell",
        "tells",
        "told",
        "called",
        "yelled",
        "shouted",
        "cried",
        "whispered",
        "murmured",
        "muttered",
        "snapped",
        "retorted",
        "laughed",
        "sobbed",
        "hissed",
        "noted",
        "observed",
        "remarked",
        "insisted",
        "countered",
        "agreed",
        "warned",
        "offered",
        "begged",
        "demanded",
        "protested",
        "announced",
        "explained",
        "declared",
        "argued",
        "suggested",
        "continued",
        "interjected",
        "interrupted",
        "conceded",
        "promised",
        "pleaded",
        "rejoined",
        "stated",
        "blurted",
    }
    union = (
        set(globals().get("_ATTRIB_VERBS", []))
        | set(globals().get("_MULTIWORD_VERBS_SAFE", []))
        | set(globals().get("_MULTIWORD_VERBS_PREP", []))
    ) or _verbs_fallback

    verbs_key = "\x1f".join(sorted(union))
    if (
        globals().get("_AF_VERBS_KEY") == verbs_key
        and globals().get("_AF_VERB_NAME_RX") is not None
        and globals().get("_AF_NAME_VERB_RX") is not None
    ):
        return
    _AF_VERBS_KEY = verbs_key

    _ATTRIB_VERBS_RX_STRICT = r"(?:%s)" % "|".join(
        sorted(map(re.escape, union), key=len, reverse=True)
    )

    # Filler between verb and name that EXCLUDES prepositions leading to an object (to/at/with/…)
    filler = r"(?:\s+(?!(?:to|at|with|toward|towards|into|onto|upon|of|about)\b)[a-z]{2,12}){0,3}"

    _AF_VERB_NAME_RX = re.compile(
        rf"^[—\-–—,\s]*(?P<verb>{_ATTRIB_VERBS_RX_STRICT}){filler}\s+(?P<who>{_NAME_RX})[\s,.\-–—:;!?]*$",
        re.IGNORECASE,
    )
    _AF_NAME_VERB_RX = re.compile(
        rf"^[—\-–—,\s]*(?P<who>{_NAME_RX})\s+(?P<verb>{_ATTRIB_VERBS_RX_STRICT}){filler}[\s,.\-–—:;!?]*$",
        re.IGNORECASE,
    )

    _SVAF_VERB_NAME_RX = _AF_VERB_NAME_RX
    _SVAF_NAME_VERB_RX = _AF_NAME_VERB_RX


def _verbs_to_regex(verbs_iterable):
    """
    Build a regex alternation that:
      • escapes tokens,
      • uses \s+ between tokens for multiword phrases,
      • adds \b word boundaries,
      • sorts longest-first to avoid shadowing.
    """
    parts = []
    for v in verbs_iterable:
        v = (v or "").strip()
        if not v:
            continue
        toks = [re.escape(tok) for tok in v.split()]
        if len(toks) == 1:
            parts.append(r"\b" + toks[0] + r"\b")
        else:
            parts.append(r"\b" + r"\s+".join(toks) + r"\b")
    # de-dup + sort longest-first
    parts = sorted(set(parts), key=len, reverse=True)
    return r"(?:%s)" % "|".join(parts) if parts else r"(?:$a)"  # $a => never matches


# Define multiword verb phrases (can be empty; keep conservative to avoid false positives)
_MULTIWORD_VERBS = list(globals().get("_MULTIWORD_VERBS", [])) or [
    "went on",
    "called out",
    "cried out",
    "shouted back",
    "yelled back",
    "told them",
    "told him",
    "told her",
    "called back",
    "cried back",
    "whispered to",
    "shouted to",
    "yelled to",
    "muttered to",
    "murmured to",
    "replied to",
    "answered back",
    "spoke to",
    "said to",
    "screamed at",
    "shouted at",
    "yelled at",
    "whispered back",
    "muttered back",
    "murmured back",
    "called to",
    "cried to",
    "asked him",
    "asked her",
    "asked them",
    "told me",
    "told you",
    "replied with",
    "answered with",
    "spoke with",
    "whispered softly",
    "muttered softly",
    "murmured softly",
    "cried softly",
    "shouted loudly",
    "yelled loudly",
    "called loudly",
    "spoke loudly",
    "answered softly",
    "replied softly",
    "growled at",
    "snarled at",
    "hissed at",
    "grumbled to",
    "moaned to",
    "sighed to",
    "whined to",
    "mumbled to",
    "chattered to",
    "confided in",
    "explained to",
    "reported to",
    "warned of",
    "cautioned about",
    "advised of",
    "reminded of",
    "pointed out",
]

# --- Build a LOOSE verb regex (legacy/back-compat) ----------------------------


def _verbs_union_for_loose():
    # Union of single-word + multiword (safe + prep-sensitive) + loose list if present
    return (
        set(globals().get("_ATTRIB_VERBS", []))
        | set(globals().get("_MULTIWORD_VERBS_SAFE", []))
        | set(globals().get("_MULTIWORD_VERBS_PREP", []))
        | set(globals().get("_ATTRIB_VERBS_LOOSE", []))
    )


# Conservative fallback in case nothing is defined yet
_FALLBACK_VERBS = {
    "said",
    "says",
    "say",
    "ask",
    "asks",
    "asked",
    "reply",
    "replies",
    "replied",
    "answer",
    "answers",
    "answered",
    "tell",
    "tells",
    "told",
    "called",
    "yelled",
    "shouted",
    "cried",
    "whispered",
    "murmured",
    "muttered",
    "snapped",
    "retorted",
    "laughed",
    "sobbed",
    "hissed",
    "noted",
    "observed",
    "remarked",
    "insisted",
    "countered",
    "agreed",
    "warned",
    "offered",
    "begged",
    "demanded",
    "protested",
    "announced",
    "explained",
    "declared",
    "argued",
    "suggested",
    "continued",
    "interjected",
    "interrupted",
    "conceded",
    "promised",
    "pleaded",
    "rejoined",
    "stated",
    "blurted",
}


def _make_rx_from_verbs(verbs: set[str] | list[str]) -> str:
    vs = set(verbs) if verbs else set()
    if not vs:
        vs = set(_FALLBACK_VERBS)
    # Longest-first to prefer multiword phrases
    return "(?:%s)" % "|".join(sorted(map(re.escape, vs), key=len, reverse=True))


# Define the loose regex string and keep the legacy alias
_ATTRIB_VERBS_RX_LOOSE = _make_rx_from_verbs(_verbs_union_for_loose())
_VERBS_RX = _ATTRIB_VERBS_RX_LOOSE  # legacy name expected elsewhere

# --- Sanitize multiword verbs into safe vs. prep-sensitive, with head lemmatization ----


def _sanitize_multiword_verb_list(phrases):
    """
    Split phrases into:
      safe: usable in strict matching without a preposition (e.g., 'shot back', 'went on', 'chimed in')
      prep_sensitive: often take 'to/at/with/toward(s)/into/onto/upon/of/about' and must *not* drive VERB→NAME
    Non-speech actions are discarded to protect precision.
    """
    # Accept *base* speech heads; we will lemmatize 'said/asked/told' → 'say/ask/tell'
    HEAD_SPEECH = {
        "say",
        "ask",
        "reply",
        "answer",
        "call",
        "yell",
        "shout",
        "cry",
        "whisper",
        "murmur",
        "mutter",
        "snap",
        "retort",
        "laugh",
        "sob",
        "hiss",
        "note",
        "observe",
        "remark",
        "insist",
        "counter",
        "agree",
        "warn",
        "offer",
        "beg",
        "demand",
        "protest",
        "announce",
        "explain",
        "declare",
        "argue",
        "suggest",
        "continue",
        "interject",
        "interrupt",
        "concede",
        "promise",
        "plead",
        "rejoin",
        "state",
        "blurt",
        "speak",
        "talk",
        "add",
        "chime",
        "pipe",
        "butt",
        "cut",
        "break",
        "ring",
        "sing",
        "read",
        "shoot",
        "fire",
        "go",
        "growl",
        "snarl",
        "scoff",
        "sneer",
        "jeer",
        "taunt",
        "grumble",
        "groan",
        "moan",
        "sigh",
        "whine",
        "complain",
        "mumble",
        "babble",
        "ramble",
        "chatter",
        "confide",
        "recount",
        "report",
        "inform",
        "advise",
        "remind",
        "describe",
        "reveal",
        "disclose",
        "point",
        "tell",
    }
    PREP_BLOCK = {
        "to",
        "at",
        "with",
        "toward",
        "towards",
        "into",
        "onto",
        "upon",
        "of",
        "about",
    }
    OK_PARTICLES = {
        "back",
        "out",
        "up",
        "in",
        "on",
        "forth",
        "again",
        "softly",
        "loudly",
    }

    # light-weight lemma for head token
    IRREG_HEADS = {
        "said": "say",
        "says": "say",
        "saying": "say",
        "asked": "ask",
        "asks": "ask",
        "asking": "ask",
        "told": "tell",
        "tells": "tell",
        "telling": "tell",
        "replied": "reply",
        "replies": "reply",
        "replying": "reply",
        "answered": "answer",
        "answers": "answer",
        "answering": "answer",
        "explained": "explain",
        "explains": "explain",
        "explaining": "explain",
        "declared": "declare",
        "declares": "declare",
        "declaring": "declare",
        "continued": "continue",
        "continues": "continue",
        "continuing": "continue",
    }

    def _head_lemma(h):
        h = h.lower()
        if h in IRREG_HEADS:
            return IRREG_HEADS[h]
        # crude regulars
        if h.endswith("ies"):
            return h[:-3] + "y"
        if h.endswith("ing") and len(h) > 5:
            return h[:-3]
        if h.endswith("ed") and len(h) > 4:
            if h.endswith("ied"):
                return h[:-3] + "y"
            if h[-3] == h[-4]:  # e.g., "stopped" → "stop" (very rough)
                return h[:-3]
            return h[:-2]
        if h.endswith("es") and len(h) > 3:
            return h[:-2]
        if h.endswith("s") and len(h) > 3:
            return h[:-1]
        return h

    safe, prep_sensitive = [], []
    for p in phrases:
        s = " ".join((p or "").strip().split())
        if not s:
            continue
        toks = s.split()
        head = _head_lemma(toks[0])
        if head not in HEAD_SPEECH:
            continue  # discard non-speech heads
        # prepositions → prep-sensitive
        if any(t.lower() in PREP_BLOCK for t in toks[1:]):
            prep_sensitive.append(s)
            continue
        # known dialogue particles or single-word phrasal
        if len(toks) == 1 or any(t.lower() in OK_PARTICLES for t in toks[1:]):
            safe.append(s)
        else:
            prep_sensitive.append(s)
    return safe, prep_sensitive


# Expand multiword verbs to simple inflections (base/3sg/past with a few irregulars)
def _expand_multiword_verbs(base_list):
    import re

    _IRREG_PAST = {
        "shoot": ["shot"],
        "spit": ["spat", "spit"],
        "cut": ["cut"],
        "shut": ["shut"],
        "read": ["read"],
        "ring": ["rang"],
        "sing": ["sang"],
        "go": ["went"],
        "speak": ["spoke"],
        "tell": ["told"],
        "say": ["said"],
        "ask": ["asked"],
    }

    def _s_form(v):
        if re.search(r"(s|sh|ch|x|z|o)$", v):
            return v + "es"
        if re.search(r"[^aeiou]y$", v):
            return v[:-1] + "ies"
        return v + "s"

    def _ed_form(v):
        if v in _IRREG_PAST:
            return None
        if v.endswith("e"):
            return v + "d"
        if re.search(r"[^aeiou]y$", v):
            return v[:-1] + "ied"
        return v + "ed"

    out, seen = [], set()
    for phrase in base_list:
        parts = phrase.split()
        if not parts:
            continue
        head, tail = parts[0], parts[1:]
        base = head.lower()
        for word in {head, _s_form(base)}:
            cand = " ".join([word] + tail)
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
        for past in _IRREG_PAST.get(base, []):
            cand = " ".join([past] + tail)
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
        rpast = _ed_form(base)
        if rpast:
            cand = " ".join([rpast] + tail)
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
    return out


try:
    _MW_SAFE_BASE, _MW_PREP_BASE = _sanitize_multiword_verb_list(_MULTIWORD_VERBS)
    _MULTIWORD_VERBS_SAFE = _expand_multiword_verbs(_MW_SAFE_BASE)
    _MULTIWORD_VERBS_PREP = _expand_multiword_verbs(_MW_PREP_BASE)
except Exception:
    _MULTIWORD_VERBS_SAFE = list(_MULTIWORD_VERBS)
    _MULTIWORD_VERBS_PREP = []

# Keep broad union for vpat + stats
_ATTRIB_VERBS = set(globals().get("_ATTRIB_VERBS", set()))
# also add single-word tell/tells/told in case project didn't include them
_ATTRIB_VERBS.update({"tell", "tells", "told"})
_ATTRIB_VERBS_LOOSE = list(
    dict.fromkeys(list(_ATTRIB_VERBS) + _MULTIWORD_VERBS_SAFE + _MULTIWORD_VERBS_PREP)
)

# --- Robust multiword / phrasal dialogue verbs --------------------------------
# Curated base forms (we auto-expand to past/3sg where sensible).
# Keep these conservative to avoid false positives on non-speech senses.
_MULTIWORD_VERBS_BASE = [
    # back
    "snap back",
    "shout back",
    "yell back",
    "call back",
    "shoot back",
    "fire back",
    "whisper back",
    "hiss back",
    "bark back",
    # out
    "blurt out",
    "call out",
    "cry out",
    "yell out",
    "shout out",
    "spit out",
    "bark out",
    "hiss out",
    "sing out",
    # up
    "speak up",
    "pipe up",
    # in
    "chime in",
    "butt in",
    "cut in",
    "break in",
    "pipe in",
    "put in",
    "jump in",
    "chip in",
    "weigh in",
    # on (continuations)
    "go on",
    "carry on",
    # misc (ring/sing/read... out often mark a loud/clear utterance)
    "ring out",
    "read out",
]

# STRICT core for line/tail attribution (kept tight to avoid false positives)
_ATTRIB_VERBS_STRICT = {
    "said",
    "asked",
    "replied",
    "told",
    "added",
    "explained",
    "continued",
    "went on",
    "murmured",
    "whispered",
    "yelled",
    "shouted",
    "cried",
    "called",
    "answered",
    "retorted",
    "insisted",
    "agreed",
    "warned",
    "demanded",
    "begged",
    "protested",
    "announced",
    "declared",
    "stated",
    "remarked",
    "observed",
    "suggested",
    "interjected",
    "interrupted",
    "rejoined",
    "pleaded",
    "inquired",
    "admitted",
    "noted",
    "joked",
    "quipped",
}
# Keep only items that really exist in LOSE (plus multi-words)
_ATTRIB_VERBS_STRICT = {
    v
    for v in _ATTRIB_VERBS_STRICT
    if (v in _ATTRIB_VERBS_LOOSE) or (v in _MULTIWORD_VERBS)
}
_ATTRIB_VERBS_RX_STRICT = _verbs_to_regex(_ATTRIB_VERBS_STRICT)

# For compatibility with the rest of your code:
#  - Use the LOOSE set where you previously used _VERBS_RX (broad checks)
#  - Use the STRICT set for _ATTRIB_LINE_RX / tail-head detectors
_VERBS_RX = _ATTRIB_VERBS_RX_LOOSE

# Lines like 'said Alex.' or 'Alex said softly.'
# NOTE: Use STRICT verbs here to reduce narration false-positives.
_ATTRIB_LINE_RX = re.compile(
    rf"^\s*(?:"
    rf"(?P<verb1>{_ATTRIB_VERBS_RX_STRICT})"  # verb … name
    rf"(?:\s+\w+){{0,4}}\s+"
    rf"(?P<name1>[A-Za-z][\w\'\-]+(?:\s+[A-Za-z][\w\'\-]+){{0,2}})"
    rf"|"
    rf"(?P<name2>[A-Za-z][\w\'\-]+(?:\s+[A-Za-z][\w\'\-]+){{0,2}})"  # name … verb
    rf"\s+(?:\w+\s+)?"
    rf"(?P<verb2>{_ATTRIB_VERBS_RX_STRICT})"
    rf')\s*(?:[^"“”]*)$',
    re.IGNORECASE,
)

# If other code expects _ATTRIB_VERBS_RX, make it STRICT by default for precision:
_ATTRIB_VERBS_RX = _ATTRIB_VERBS_RX_STRICT

_NAME_RX = r"[A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+){0,2}"

# Tail attribution detectors (use STRICT verbs)
_TAIL_ATTRIB_VERB_FIRST_RX = re.compile(
    rf"(?P<body>.*?)"
    rf"(?P<sep>[,;:—-]?\s*)"
    rf"(?P<verb>{_ATTRIB_VERBS_RX_STRICT})"
    rf"(?:\s+\w+){{0,2}}\s+"
    rf"(?P<who>{_NAME_RX})"
    rf'\s*(?P<end>[.!?]["”]?\s*)?$',
    re.IGNORECASE | re.DOTALL,
)

_TAIL_ATTRIB_NAME_FIRST_RX = re.compile(
    rf"(?P<body>.*?)"
    rf"\s+(?P<who>{_NAME_RX})\s+"
    rf"(?P<verb>{_ATTRIB_VERBS_RX_STRICT})"
    rf"(?:\s+\w+){{0,2}}"
    rf'\s*(?P<end>[.!?]["”]?\s*)?$',
    re.IGNORECASE | re.DOTALL,
)

# If you still have an older _ATTRIB_VERB_SET/_ATTRIB_VERBS_RX elsewhere,
# keep them in sync with this:
try:
    _ATTRIB_VERB_SET = set(_ATTRIB_VERBS_LOOSE)
except Exception:
    pass


_NAME_COLON_RX = re.compile(
    r'^\s*(?:["”\']\s*)?'  # tolerate a stray quote before the name
    r"(?P<name>[A-Za-z][\w\'\-]+(?:\s+[A-Za-z][\w\'\-]+){0,2})"  # 1–3 name tokens
    r"\s*:\s*"
    r"(?P<rest>.*)$"  # everything after the colon (can be empty)
)

# (Keep your demotion patterns if you use them in clean_results)
ATTRIBUTION_PATTERNS = [
    rf"^\s*{_VERBS_RX}\s+\w+",
    rf"^\s*\w+\s+{_VERBS_RX}\b",
]

# Pure attribution fragments (used by pre/mid/tail logic)
_ATTRIB_TAIL = re.compile(
    rf"^\s*(?:[,–—\-]\s*)?(?:{_VERBS_RX})\s+[A-Za-z][\w\'\-]+(?:\s+[A-Za-z][\w\'\-]+){{0,2}}(?:\s*[:–—\-]\s*)?\.?\s*$",
    re.IGNORECASE,
)
_ATTRIB_HEAD = re.compile(
    rf"^\s*(?:[,–—\-]\s*)?[A-Za-z][\w\'\-]+(?:\s+[A-Za-z][\w\'\-]+){{0,2}}\s+(?:{_VERBS_RX})\b.*?(?:\s*[:–—\-]\s*)?$",
    re.IGNORECASE,
)


BAN_SPEAKERS = {
    # generic groups / pronouns / crowd-ish
    "narration",
    "narrator",
    "god",
    "guys",
    "we",
    "boys",
    "people",
    "old men",
    "older man",
    "the older man",
    "young man",
    "the young man",
    "man",
    "woman",
    "men",
    "women",
    "voice",
    "crowd",
    "they",
    "them",
    "everybody",
    "anybody",
    "somebody",
    "I",
    "me",
    "you",
    "he",
    "him",
    "she",
    "her",
    "it",
    "us",
    "everyone",
    "anyone",
    "no one",
    "nobody",
    "someone",
    "person",
    "individual",
    "stranger",
    "figure",
    "shadow",
    "group",
    "team",
    "family",
    "friends",
    "class",
    "audience",
    "mob",
    "assembly",
    "child",
    "kid",
    "teenager",
    "adult",
    "elder",
    "senior",
    "lady",
    "gentleman",
    "guy",
    "gal",
    "fellow",
    "girls",
    "ladies",
    "gentlemen",
    "folks",
    "children",
    "kids",
    "voices",
    "chorus",
    "all",
    "both",
    "a man",
    "the man",
    "a woman",
    "the woman",
    "a boy",
    "the boy",
    "a girl",
    "the girl",
    "a child",
    "the child",
    "a person",
    "the person",
    "young woman",
    "the young woman",
    "old man",
    "the old man",
    "old woman",
    "the old woman",
    "young boy",
    "the young boy",
    "young girl",
    "the young girl",
    "elderly man",
    "the elderly man",
    "elderly woman",
    "the elderly woman",
    "middle-aged man",
    "the middle-aged man",
    "middle-aged woman",
    "the middle-aged woman",
    "teenage boy",
    "the teenage boy",
    "teenage girl",
    "the teenage girl",
    "strange man",
    "the strange man",
    "strange woman",
    "the strange woman",
    "tall man",
    "the tall man",
    "short woman",
    "the short woman",
    "mysterious figure",
    "the mysterious figure",
    "unknown voice",
    "the unknown voice",
    "distant voice",
    "the distant voice",
    "whispering voice",
    "the whispering voice",
    "ghost",
    "spirit",
    "deity",
    "entity",
    "being",
    "creature",
    "spectator",
    "onlooker",
    "bystander",
    "passerby",
    "witness",
    "observer",
    "crowds",
    "masses",
    "public",
    "society",
    "community",
    "village",
    "townsfolk",
    "villagers",
    "citizens",
    "residents",
    "inhabitants",
    "neighbors",
    "colleagues",
    "coworkers",
    "classmates",
    "teammates",
    "companions",
    "allies",
    "enemies",
    "opponents",
    "rivals",
    "adversaries",
    "parents",
    "siblings",
    "relatives",
    "ancestors",
    "descendants",
    "heirs",
    "offspring",
    "progeny",
    "kin",
    "clan",
    "tribe",
    "nation",
    "country",
    "world",
    "universe",
    "humanity",
    "mankind",
    "humankind",
    "beings",
    "creatures",
    "animals",
    "beast",
    "monster",
    "demon",
    "angel",
    "devil",
    "saint",
    "sinner",
    "hero",
    "villain",
    "protagonist",
    "antagonist",
    "narrative voice",
    "omniscient narrator",
    "third person",
    "first person",
    "second person",
    "perspective",
    "viewpoint",
    "thoughts",
    "mind",
    "consciousness"
    # NEW obvious junk seen in logs
    "shrug",
    "sneer",
    "sneered",
    "dead",
    "or",
    "re",
    "athreemanteam",
    # adverbial tokens that leaked as “names”
    "simply",
    "softly",
    "firmly",
    "curiously",
    "quietly",
    "dryly",
}
# normalized (no spaces/hyphens) forms to catch "oldmen", "olderman", etc.
BAN_SPEAKERS_NORM = {re.sub(r"[\s\-]+", "", s) for s in BAN_SPEAKERS}

PRONOUN_BLACKLIST = {
    "he",
    "she",
    "him",
    "her",
    "his",
    "hers",
    "they",
    "them",
    "their",
    "theirs",
    "we",
    "us",
    "our",
    "ours",
    "i",
    "me",
    "my",
    "mine",
    "you",
    "your",
    "yours",
}

# --- Carve out tail attributions trapped inside quotes (verb-first & name-first) ---
_ATTRIB_VERBS = {
    "said",
    "asked",
    "explained",
    "added",
    "replied",
    "murmured",
    "whispered",
    "yelled",
    "shouted",
    "called",
    "told",
    "went on",
    "continued",
    "interposed",
    "agreed",
    "reminded",
    "repeated",
    "urged",
    "demanded",
    "began",
    "spoke up",
    "went on grimly",
    "said simply",
    "said softly",
    "clarified",
    "counseled",
    "interjected",
    "stated",
    "jabbered",
    "yapped",
    "refuted",
    "pondered",
    "rejoined",
    "surmised",
    "verified",
    "guffawed",
    "tittered",
    "avowed",
    "convinced",
    "implored",
    "prodded",
    "insulted",
    "provoked",
    "smirked",
    "tempted",
    "grilled",
    "declared",
    "maintained",
    "vowed",
    "inquired",
    "quizzed",
    "wondered",
    "hesitated",
    "warned",
    "croaked",
    "heaved",
    "lisped",
    "rattled on",
    "shrilled",
    "stuttered",
    "caterwauled",
    "condemned",
    "fumed",
    "raged",
    "scolded",
    "snarled",
    "threatened",
    "grimaced",
    "sniffed",
    "snorted",
    "spluttered",
    "prayed",
    "squeaked",
    "worried",
    "protested",
    "whinged",
    "cackled",
    "congratulated",
    "gushed",
    "simpered",
    "whooped",
    "flattered",
    "purred",
    "swooned",
    "mumbled",
    "wished",
    "consoled",
    "sobbed",
    "wept",
    "marveled",
    "marvelled",
    "yelped",
    "yawned",
    "alliterated",
    "described",
    "emphasized",
    "imitated",
    "insisted",
    "mouthed",
    "offered",
    "pressed",
    "recalled",
    "remembered",
    "rhymed",
    "tried",
    "accepted",
    "acknowledged",
    "admitted",
    "affirmed",
    "assumed",
    "conferred",
    "confessed",
    "confirmed",
    "justified",
    "settled",
    "understood",
    "undertook",
    "accused",
    "barked",
    "bellowed",
    "bossed",
    "carped",
    "censured",
    "criticized",
    "gawped",
    "glowered",
    "grumbled",
    "hissed",
    "remonstrated",
    "reprimanded",
    "retorted",
    "scoffed",
    "seethed",
    "snapped",
    "ticked off",
    "told off",
    "upbraided",
    "contemplated",
    "addressed",
    "advertised",
    "articulated",
    "bragged",
    "commanded",
    "confided",
    "decided",
    "dictated",
    "ended",
    "exacted",
    "finished",
    "informed",
    "made known",
    "necessitated",
    "pointed out",
    "promised",
    "reassured",
    "remarked",
    "reported",
    "specified",
    "attracted",
    "requested",
    "wanted",
    "beamed",
    "blurted",
    "broadcasted",
    "burst",
    "cheered",
    "chortled",
    "chuckled",
    "cried out",
    "crooned",
    "crowed",
    "emitted",
    "exclaimed",
    "giggled",
    "hollered",
    "howled",
    "laughed",
    "praised",
    "preached",
    "presented",
    "proclaimed",
    "professed",
    "promulgated",
    "quaked",
    "ranted",
    "rejoiced",
    "roared",
    "screamed",
    "shrieked",
    "swore",
    "thundered",
    "trilled",
    "trumpeted",
    "vociferated",
    "wailed",
    "yawped",
    "yowled",
    "cautioned",
    "shuddered",
    "trembled",
    "comforted",
    "empathized",
    "invited",
    "proffered",
    "released",
    "volunteered",
    "advised",
    "alleged",
    "appealed",
    "asserted",
    "assured",
    "avered",
    "beckoned",
    "begged",
    "beseeched",
    "cajoled",
    "claimed",
    "conceded",
    "concluded",
    "concurred",
    "contended",
    "defended",
    "disposed",
    "encouraged",
    "entreated",
    "held",
    "hinted",
    "implied",
    "importuned",
    "inclined",
    "indicated",
    "pleaded",
    "postulated",
    "premised",
    "presupposed",
    "stressed",
    "suggested",
    "touted",
    "vouched for",
    "wheedled",
    "chimed in",
    "circulated",
    "disseminated",
    "distributed",
    "expressed",
    "grinned",
    "made public",
    "passed on",
    "publicized",
    "published",
    "put forth",
    "put out",
    "quipped",
    "quoted",
    "reckoned that",
    "required",
    "requisitioned",
    "taunted",
    "teased",
    "exposed",
    "joked",
    "leered",
    "lied",
    "mimicked",
    "mocked",
    "agonized",
    "bawled",
    "blubbered",
    "grieved",
    "groaned",
    "lamented",
    "mewled",
    "mourned",
    "puled",
    "announced",
    "answered",
    "denoted",
    "disclosed",
    "divulged",
    "imparted",
    "noted",
    "observed",
    "proposed",
    "revealed",
    "shared",
    "solicited",
    "sought",
    "testified",
    "transferred",
    "transmitted",
    "doubted",
    "faltered",
    "fretted",
    "guessed",
    "hypothesized",
    "lilted",
    "quavered",
    "queried",
    "questioned",
    "shrugged",
    "speculated",
    "supposed",
    "trailed off",
    "breathed",
    "choked",
    "drawled",
    "echoed",
    "grunted",
    "keened",
    "moaned",
    "panted",
    "sang",
    "sniffled",
    "sniveled",
    "uttered",
    "voiced",
    "whimpered",
    "whined",
    "probed",
    "backtracked",
    "communicated",
    "considered",
    "elaborated",
    "enunciated",
    "expounded",
    "greeted",
    "mentioned",
    "orated",
    "persisted",
    "predicted",
    "pronounced",
    "recited",
    "reckoned",
    "related",
    "responded",
    "slurred",
    "vocalized",
    "approved",
    "bubbled",
    "chattered",
    "complimented",
    "effused",
    "thanked",
    "yammered",
    "apologized",
    "cried",
    "sighed",
    "sniveled",
    "badgered",
    "chastised",
    "cursed",
    "exploded",
    "insulted",
    "screeched",
    "spat",
    "bleated",
    "exhaled",
    "groused",
    "gulped",
    "squalled",
    "warbled",
    "yowled",
    "bloviated",
    "exhorted",
    "gloated",
    "moralized",
    "sermonized",
    "swaggered",
    "swallowed",
    "vacillated",
    "derided",
    "jeered",
    "heckled",
    "lampooned",
    "parodied",
    "ridiculed",
    "satirized",
    "scorned",
    "spoofed",
    "sneered",
    "snickered",
    "challenged",
    "interrogated",
    "mused",
    "puzzled",
    "prattled",
    "preened",
    "cooed",
    "bantered",
    "blathered",
    "blithered",
    "hooted",
    "jested",
    "soothed",
    "chorused",
    "nodded",
    "spoke",
    "piped",
    "yakked",
    "gurgled",
    "sniffed",
    "disparaged",
    "rejected",
    "griped",
    "reproached",
    "berated",
    "sassed",
    "chided",
    "clucked",
    "corrected",
    "rebuffed",
    "gawked",
    "spouted",
    "let slip",
    "gaped",
    "ogled",
    "gasped",
    "spilled",
    "shrilled",
    "blanched",
    "spooked",
    "paled",
    "brooded",
    "panicked",
    "tensed",
    "cowered",
    "quaked",
    "cringed",
    "recoiled",
    "shivered",
    "depicted",
    "elucidated",
    "defined",
    "illustrated",
    "delineated",
    "portrayed",
    "returned",
    "advanced",
    "corroborated",
    "posited",
    "attested",
    "counters",
    "authenticated",
    "refuted",
    "bespoke",
    "substantiated",
    "certified",
    "critiqued",
    "gauged",
    "appraised",
    "estimated",
    "assayed",
    "evaluated",
    "interpreted",
    "assessed",
    "examined",
    "judged",
    "explicated",
    "reviewed",
    "figured",
    "surveyed",
    "adumbrated",
    "alluded",
    "connoted",
    "signaled",
    "foreshadowed",
    "insinuated",
    "signified",
    "forewarned",
    "intimated",
    "heralded",
    "portended",
    "adjured",
    "inspected",
    "perused",
    "researched",
    "explored",
    "searched",
    "owned",
    "recognized",
    "betrayed",
    "acquiesced",
    "bellyached",
    "bickered",
    "blabbed",
    "blabbered",
    "blathered",
    "brayed",
    "broke in",
    "coached",
    "coaxed",
    "contradicted",
    "contributed",
    "cooed",
    "deduced",
    "demurred",
    "disagreed",
    "dissented",
    "dribbled",
    "droned",
    "ejaculated",
    "exulted",
    "fussed",
    "gibbered",
    "gibed",
    "guaranteed",
    "harangued",
    "huffed",
    "intoned",
    "joined in",
    "nattered",
    "neighed",
    "nitpicked",
    "objected",
    "opined",
    "pestered",
    "pled",
    "pledged",
    "prated",
    "resounded",
    "resumed",
    "retaliated",
    "shot",
    "sniveled",
    "tattled",
    "theorized",
    "toasted",
    "tutted",
    "weighed in",
    "whickered",
    "whinnied",
    "brought forth",
    "denounced",
    "disrupted",
    "enjoined",
    "condescended",
    "contested",
    "feared",
    "foretold",
    "cracked",
    "haggled",
    "hedged",
    "relented",
    "orated",
    "remonstrated",
    "petitioned",
    "inferred",
    "propounded",
    "intimidated",
    "itemized",
    "proved",
    "sanctioned",
    "quibbled",
    "rambled",
    "reaffirmed",
    "reciprocated",
    "referred",
    "regretted",
    "restated",
    "ruled",
    "stipulated",
    "twitted",
    "whistled",
    "thought",
    "wrangled",
}

_NAME_RX = r"[A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+){0,2}"

# === ENLP caches (globals + loader) ==========================================
ENLP_CID2CANON: dict[int, str] = {}  # char_id -> canonical name
ENLP_QUOTE_INDEX: list[dict] = (
    []
)  # list of {quote, char_id, mention_phrase, ... , _norm_quote}
ENLP_COREF_MAP: dict[str, int] = {}  # surface form -> char_id (very conservative)

# last-initialized key so we don't rebuild repeatedly
_ENLP_CACHE_KEY: tuple[str, str] | None = None


def _norm_quote_text(s: str) -> str:
    """
    Normalize a quote's text for matching:
      - unify unicode quotes
      - strip leading/trailing quotes
      - collapse whitespace
      - lowercase
    """
    if not s:
        return ""
    t = _norm_unicode_quotes(s)
    # strip outer quotes if present
    t = t.strip().strip('“”"')
    # collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t.lower()


def _build_enlp_index_once(alias_inv=None):
    """
    Build a consistent in-memory index from ENLP_* sources and cache it in DBG['_enlp_index'].
    Accepts multiple shapes:
      - ENLP_QUOTE_INDEX: list[str]
      - ENLP_QUOTE_INDEX: list[dict] with fields like {'text' or 'quote', 'char_id' or 'speaker' or 'canonical'}
      - ENLP_QUOTE_INDEX: dict[str -> char_id or canonical]
    Optional: ENLP_CID2CANON maps char_id -> canonical name.
    If neither is available, index remains empty.
    """
    if DBG.get("_enlp_index_built"):
        return

    items = []
    try:
        src = globals().get("ENLP_QUOTE_INDEX", None)
        cid2canon = globals().get("ENLP_CID2CANON", None)
        if isinstance(src, dict):
            # dict: normalized_text -> cid_or_name
            for k, v in src.items():
                norm = _norm_quote_text(k)
                canon = None
                cid = None
                if isinstance(v, (str,)):
                    # could be canonical name or cid; attempt to map as cid first
                    if cid2canon and v in cid2canon:
                        cid = v
                        canon = cid2canon.get(v) or v
                    else:
                        canon = v
                elif isinstance(v, dict):
                    cid = v.get("char_id") or v.get("cid")
                    if cid and cid2canon:
                        canon = cid2canon.get(cid) or canon
                    canon = (
                        canon or v.get("canonical") or v.get("speaker") or v.get("name")
                    )
                items.append({"_norm_quote": norm, "char_id": cid, "canonical": canon})
        elif isinstance(src, list):
            for it in src:
                if isinstance(it, str):
                    norm = _norm_quote_text(it)
                    items.append(
                        {"_norm_quote": norm, "char_id": None, "canonical": None}
                    )
                elif isinstance(it, dict):
                    # Try common field names
                    text = (
                        it.get("_norm_quote")
                        or it.get("text")
                        or it.get("quote")
                        or it.get("q")
                        or ""
                    )
                    norm = _norm_quote_text(text)
                    cid = it.get("char_id") or it.get("cid")
                    canon = it.get("canonical") or it.get("speaker") or it.get("name")
                    if cid and cid2canon:
                        canon = cid2canon.get(cid) or canon
                    items.append(
                        {"_norm_quote": norm, "char_id": cid, "canonical": canon}
                    )
        else:
            # Unknown / None → empty
            items = []
    except Exception as e:
        log(f"[enlp-index] failed to build index: {e}")
        items = []

    # Collapse to fastest lookup: norm_text -> best canonical
    # If multiple entries for the same norm text exist, prefer one that has canonical.
    index = {}
    for row in items:
        norm = row.get("_norm_quote") or ""
        if not norm:
            continue
        cur = index.get(norm)
        # prefer rows with canonical names; otherwise keep the first
        if cur is None or (not cur.get("canonical") and row.get("canonical")):
            index[norm] = {
                "canonical": row.get("canonical"),
                "char_id": row.get("char_id"),
            }

    DBG["_enlp_index"] = index
    DBG["_enlp_index_built"] = True
    log(f"[enlp-index] built with {len(index)} entries")


def _first_existing_path(dirpath: str, stem_no_ext: str) -> str | None:
    """
    Prefer the raw BookNLP output 'prefix.quotes' (no extension), but
    also support '.txt', '(edit).txt', and '(mod).txt' for convenience.
    """
    import os

    cands = [
        os.path.join(dirpath, stem_no_ext),  # book_input.quotes
        os.path.join(dirpath, f"{stem_no_ext}.txt"),  # book_input.quotes.txt
        os.path.join(
            dirpath, f"{stem_no_ext}(edit).txt"
        ),  # book_input.quotes(edit).txt
        os.path.join(dirpath, f"{stem_no_ext}(mod).txt"),  # book_input.quotes(mod).txt
    ]
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def init_enlp_caches(outdir: str, prefix: str) -> None:
    """
    Build ENLP_CID2CANON, ENLP_QUOTE_INDEX, ENLP_COREF_MAP from EnglishBookNLP output.
    Safe to call many times; rebuilds only if (outdir, prefix) changed.
    Expects:
      - {prefix}.characters_simple.json
      - {prefix}.quotes
      - (optional) {prefix}.entities
    """
    global ENLP_CID2CANON, ENLP_QUOTE_INDEX, ENLP_COREF_MAP, _ENLP_CACHE_KEY

    if not outdir or not prefix:
        return

    cache_key = (outdir, prefix)
    if _ENLP_CACHE_KEY == cache_key and ENLP_CID2CANON and ENLP_QUOTE_INDEX:
        return  # already loaded for this book

    # 1) characters_simple.json -> CID -> Canonical
    chars_path = os.path.join(outdir, f"{prefix}.characters_simple.json")
    cid2canon: dict[int, str] = {}
    if os.path.exists(chars_path):
        try:
            data = json.load(open(chars_path, "r", encoding="utf-8"))
            for c in data.get("characters", []):
                cid = c.get("char_id")
                nm = (c.get("normalized_name") or "").strip()
                if isinstance(cid, int) and nm:
                    cid2canon[cid] = nm
        except Exception as e:
            log(f"[enlp] failed to read characters_simple.json: {e}")
    ENLP_CID2CANON = cid2canon

    # 2) quotes.tsv -> index rows
    quotes_path = _first_existing_path(outdir, f"{prefix}.quotes")
    qrows: list[dict] = []
    if quotes_path:
        try:
            with open(quotes_path, "r", encoding="utf-8") as f:
                header = f.readline().rstrip("\n").split("\t")
                # Expect: quote_start, quote_end, mention_start, mention_end, mention_phrase, char_id, quote
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 7:
                        continue
                    try:
                        qstart = int(parts[0])
                        qend = int(parts[1])
                        mstart = int(parts[2])
                        mend = int(parts[3])
                        mphrase = parts[4]
                        cid = int(parts[5]) if parts[5] not in ("", None) else -1
                        quote_txt = parts[6]
                    except Exception:
                        continue
                    row = {
                        "quote_start": qstart,
                        "quote_end": qend,
                        "mention_start": mstart,
                        "mention_end": mend,
                        "mention_phrase": mphrase,
                        "char_id": cid,
                        "quote": quote_txt,
                        "_norm_quote": _norm_quote_text(quote_txt),
                    }
                    qrows.append(row)
        except Exception as e:
            log(f"[enlp] failed to read quotes: {e}")
    ENLP_QUOTE_INDEX = qrows

    # 3) very conservative surface->char_id map from quote mention phrases
    #    (skip pure pronouns; allow capitalized names and multiword)
    ENLP_COREF_MAP = {}
    PRON_LIKE = {
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        "mine",
        "yours",
        "ours",
        "theirs",
    }
    for q in ENLP_QUOTE_INDEX:
        phrase = (q.get("mention_phrase") or "").strip()
        cid = q.get("char_id")
        if not phrase or not isinstance(cid, int):
            continue
        # Skip single pronouns
        if phrase.lower() in PRON_LIKE:
            continue
        # Minimal cleanliness: prefer phrases that look like names or multiword refs
        if re.match(r"^[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+)*$", phrase) or (
            " " in phrase
        ):
            ENLP_COREF_MAP[normalize_name(phrase)] = cid

    _ENLP_CACHE_KEY = cache_key
    log(
        f"[enlp] caches initialized: cid={len(ENLP_CID2CANON)} quotes={len(ENLP_QUOTE_INDEX)} coref={len(ENLP_COREF_MAP)}"
    )


# Merge simple quote counts (by cluster) into CLUSTER_STATS for subject-only demotion ---
def _merge_quote_counts_into_cluster_stats(qmap):
    try:
        from collections import Counter

        qc = Counter()
        for q in qmap or []:
            cid = q.get("char_id")
            try:
                cid = int(cid) if cid not in (None, "", "-1") else None
            except Exception:
                cid = None
            if cid is not None:
                qc[cid] += 1
        for cid, cnt in qc.items():
            CLUSTER_STATS.setdefault(cid, {}).update({"quote": int(cnt)})
        log("[mentions] merged quote counts into CLUSTER_STATS")
    except Exception as e:
        log(f"[mentions] merge quote counts failed: {e}")


QUOTE_CHARS = {'"', "“", "”"}

# Tokens that should never become part of a person name
NAME_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "for",
    "nor",
    "in",
    "with",
    "of",
    "to",
    "at",
    "by",
    "on",
    "from",
    "as",
    "than",
    "into",
    "onto",
    "upon",
    "over",
    "under",
    "after",
    "before",
    "around",
    "through",
    "between",
    "without",
    "within",
}
# Strict dialogue/narration guardrail
STRICT_DIALOGUE_RULE = False
ADDRESS_HEURISTIC = True  # enable the “mention name ⇒ other speaker” rule
ADDRESS_WINDOW = 5  # how many quoted lines around to search for the other speaker
SHORT_QUOTE_MAX_CHARS = (
    80  # treat short quotes as replies (e.g., “Yes, your life is ruined.”)
)
ECHO_MIN_OVERLAP = 0.35  # Jaccard overlap of content words to treat as an echo
UNKNOWN_SPEAKER = "Unknown"  # used when a quoted line has no reliable speaker
FINALIZE_TRUST_QSCORE = (
    0.65  # if a quote matched .quotes this well, prefer keeping its speaker
)

# ---- Atomic quotes mode: never break / demote quoted text ----
QUOTES_ARE_ATOMIC = True  # hard "do not split quote rows"
GLUE_DANGLING_TO_NEXT = False  # optional: if a quote opens but doesn’t close, glue the next short non-quote line
MAX_GLUE_TAIL_CHARS = 80  # safety cap for the glue step


# --- Quote detection settings (must exist before runtime uses of _quote_spans) ---
if "MIN_QUOTE_CHARS" not in globals():
    MIN_QUOTE_CHARS = 1  # allow very short quotes like "No."

# If you already define these elsewhere, keep only one definition.
if "OPEN_Q" not in globals():
    OPEN_Q = {"“", '"', "‘"}
if "CLOSE_Q" not in globals():
    CLOSE_Q = {"”", '"', "’"}

# (Optional) unify if you use QUOTE_CHARS in other helpers
if "QUOTE_CHARS" not in globals():
    QUOTE_CHARS = OPEN_Q | CLOSE_Q


# --- Logging Setup ---
def get_log_path():
    log_dir = os.path.join("output", "logs")
    os.makedirs(log_dir, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    return os.path.join(log_dir, f"character_detection_{run_id}.log")


LOG_PATH = get_log_path()


def log(msg: str):
    """Append debug info to the log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def _explicit_name_from_any(text: str):
    m = _ATTRIB_LINE_RX.match((text or "").strip())
    if not m:
        return None
    name = m.group("name1") or m.group("name2")
    return normalize_name(name).title() if name else None


# === Speaker extractor for your attribution fragment detector ===
# Minimal core in case _ATTRIB_VERBS isn't populated yet
CORE_ATTRIB_VERBS = {
    "said",
    "says",
    "ask",
    "asks",
    "asked",
    "reply",
    "replies",
    "replied",
    "answer",
    "answers",
    "answered",
    "added",
    "add",
    "adds",
    "yell",
    "yells",
    "yelled",
    "shout",
    "shouts",
    "shouted",
    "cry",
    "cries",
    "cried",
    "whisper",
    "whispers",
    "whispered",
    "murmur",
    "murmurs",
    "murmured",
    "mutter",
    "mutters",
    "muttered",
    "remark",
    "remarks",
    "remarked",
    "observe",
    "observes",
    "observed",
    "state",
    "states",
    "stated",
    "declare",
    "declares",
    "declared",
    "insist",
    "insists",
    "insisted",
    "explain",
    "explains",
    "explained",
    "retort",
    "retorts",
    "retorted",
    "warn",
    "warns",
    "warned",
    "agree",
    "agrees",
    "agreed",
    "interject",
    "interjects",
    "interjected",
    "interrupt",
    "interrupts",
    "interrupted",
    "continue",
    "continues",
    "continued",
    "went on",
    "go on",
    "goes on",
}

# If you already defined _ATTRIB_VERBS (your big list), this will use it.
try:
    _ATTRIB_VERBS  # may exist
except NameError:
    _ATTRIB_VERBS = set()

# Strict verb regex (supports multi-word verbs; longest first to avoid substrings)
_VERB_SET_FOR_RX = _ATTRIB_VERBS or CORE_ATTRIB_VERBS
_ATTRIB_VERBS_RX_STRICT = r"(?:%s)" % "|".join(
    sorted(map(re.escape, _VERB_SET_FOR_RX), key=len, reverse=True)
)

# Proper-name: 1–3 capitalized tokens
_NAME_RX = r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}"

# Allow up to 3 adverbs/fillers after the verb
_AF_FILLER = r"(?:\s+(?:\w+ly|then|again|softly|quietly|firmly|evenly|calmly|angrily|sharply|dryly|simply)){0,3}"

# Verb → Name  (e.g., ", said softly John Smith.")
_AF_VERB_NAME_RX = re.compile(
    rf"^[—\-–—,\s]*(?P<verb>{_ATTRIB_VERBS_RX_STRICT}){_AF_FILLER}\s+(?P<who>{_NAME_RX})[\s,.\-–—:;!?]*$",
    re.IGNORECASE,
)

# Name → Verb  (e.g., ", John Smith said softly.")
_AF_NAME_VERB_RX = re.compile(
    rf"^[—\-–—,\s]*(?P<who>{_NAME_RX})\s+(?P<verb>{_ATTRIB_VERBS_RX_STRICT}){_AF_FILLER}[\s,.\-–—:;!?]*$",
    re.IGNORECASE,
)
_AF_VERBS_RX = _ATTRIB_VERBS_RX_STRICT  # backwards-compat alias


def _speaker_from_attrib_fragment(text: str, alias_inv: dict | None = None):
    """
    Use the shared AF regexes to pull (who, verb).
    Returns (who, verb) or (None, None). 'who' is normalized Title Case,
    with alias correction if alias_inv is provided (and _alias_correct exists).
    """
    _ensure_attrib_fragment_regexes()

    t = (text or "").strip()
    if not t:
        return None, None

    try:
        # If you have a detector, gate recall tightly
        if "_looks_like_attribution_fragment" in globals():
            if not _looks_like_attribution_fragment(t):
                return None, None
    except Exception:
        pass

    m = _AF_VERB_NAME_RX.match(t) or _AF_NAME_VERB_RX.match(t)
    if not m:
        return None, None

    who = (m.group("who") or "").strip()
    verb = (m.group("verb") or "").strip().lower()

    # Normalize / title-case the name
    try:
        who_norm = normalize_name(who).title()
    except Exception:
        who_norm = who.title() if who else who

    # Optional alias correction
    if alias_inv and "_alias_correct" in globals():
        try:
            who_norm = _alias_correct(who_norm, alias_inv or {})
        except Exception:
            pass

    # Trace (best-effort)
    try:
        DBG["attrib_frag_hits"] = DBG.get("attrib_frag_hits", 0) + 1
    except Exception:
        pass
    try:
        log(f"[attrib-frag] who='{who_norm}' verb='{verb}' | {t[:80]}…")
    except Exception:
        pass

    return who_norm, (verb or None)


def _looks_like_attribution_fragment(text: str) -> bool:
    """
    True for short narrator fragments that are *pure* attribution/action beats:
      — said Zack. / asked his friend Mike Jones. / he muttered softly. / asked Johnson in a leaden voice.
    """
    import re

    t = (text or "").strip()
    if not t:
        return False

    # Length guards (relaxed for complex)
    MAX_ATTRIB_FRAGMENT_LEN = 120
    MAX_ATTRIB_FRAGMENT_WORDS = 24
    if (
        len(t) > MAX_ATTRIB_FRAGMENT_LEN
        or len(t.split()) > MAX_ATTRIB_FRAGMENT_WORDS
        or len(t) <= 1
    ):
        return False

    # Verbs (same as splitter)
    verbs = _ATTRIB_VERBS or {
        "said",
        "says",
        "say",
        "ask",
        "asks",
        "asked",
        "reply",
        "replies",
        "replied",
        "answer",
        "answers",
        "answered",
        "tell",
        "tells",
        "told",
        "call",
        "called",
        "yell",
        "yelled",
        "shout",
        "shouted",
        "cry",
        "cried",
        "whisper",
        "whispered",
        "murmur",
        "murmured",
        "mutter",
        "muttered",
        "snap",
        "snapped",
        "retort",
        "retorted",
        "laugh",
        "laughed",
        "sob",
        "sobbed",
        "hiss",
        "hissed",
        "note",
        "noted",
        "observe",
        "observed",
        "remark",
        "remarked",
        "insist",
        "insisted",
        "counter",
        "countered",
        "agree",
        "agreed",
        "warn",
        "warned",
        "offer",
        "offered",
        "beg",
        "begged",
        "demand",
        "demanded",
        "protest",
        "protested",
        "announce",
        "announced",
        "explain",
        "explained",
        "declare",
        "declared",
        "argue",
        "argued",
        "suggest",
        "suggested",
        "continue",
        "continued",
        "interject",
        "interjected",
        "interrupt",
        "interrupted",
        "concede",
        "conceded",
        "promise",
        "promised",
        "plead",
        "pleaded",
        "rejoin",
        "rejoined",
        "state",
        "stated",
        "blurt",
        "blurted",
        "query",
        "queried",
        "go",
        "went",
        "add",
        "added",
        "went on",
        "carried on",
        "went on grimly",
        "said simply",
        "said softly",
    }
    vpat = r"(?:%s)" % "|".join(sorted(map(re.escape, verbs), key=len, reverse=True))

    # Proper with optional possessive/modifier (his/her/their)
    modifier = r"(?:his|her|their|the)\s+"
    proper = rf"(?:{modifier})?(?:[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}|he|she|they|we|i|him|her|them|He|She|They|We|I)"

    # Expanded filler (added "leaden", "curiously")
    filler = (
        r"\s*(?:\w+ly|then|again|softly|quietly|firmly|evenly|calmly|angrily|sharply|dryly|simply|wryly|grimly|sadly|leaden|curiously|in a monotone|with a shrug|with a sigh|in a low voice){0,5}?"
        r"(?:\s+(?:in|with)\s+(?:a|an|the)\s+[a-z]{{2,20}}(?:\s+[a-z]{{2,20}}){{0,2}})?\s*"
    )

    # Redesigned: (proper)? vpat filler (proper)?
    # Handles all orders and adverbs anywhere after verb
    head_tail_rx = re.compile(
        rf"^[—\-–—,\s]*"
        rf"(?:(?:{proper})\s*)?"
        rf"{vpat}"
        rf"{filler}"
        rf"(?:\s*(?:{proper}))?"
        rf"[\s,.\-–—:;!?]*$",
        re.IGNORECASE,
    )

    # Simplified action_rx (merged into head_tail)
    # No separate action_rx needed now

    # Disqualify too many commas without verb
    if t.count(",") >= 2 and not re.search(rf"\b{vpat}\b", t, re.IGNORECASE):
        return False

    return bool(head_tail_rx.match(t))


# === Surname disambiguation support ==========================================
try:
    SURNAME_TO_CANON
except NameError:
    SURNAME_TO_CANON = {}  # 'king' -> {'Steve King','Liddy King', ...}


def _build_surname_map(canon_list):
    """
    Build a map from lowercase surname → set of canonical full names.
    """
    from collections import defaultdict

    mp = defaultdict(set)
    for name in canon_list or []:
        parts = normalize_name(name).split()
        if parts:
            mp[parts[-1].lower()].add(name)
    return {k: set(v) for k, v in mp.items()}


def _ensure_surname_map(rows: list[dict] | None = None):
    """
    Ensure SURNAME_TO_CANON is initialized.
    Sources (in order of strength):
      1) Speakers found in current rows (if provided)
      2) ALIAS_INV_CACHE (if present)
      3) CANON_WHITELIST (fallback)
    Safe to call multiple times.
    """
    global SURNAME_TO_CANON
    from collections import defaultdict

    m = defaultdict(set)

    # 1) Build from current book rows (best reflection of who appears)
    if rows:
        for r in rows:
            sp = (r.get("speaker") or "").strip()
            if not sp or sp in ("Unknown", "Narrator"):
                continue
            parts = sp.split()
            if not parts:
                continue
            m[parts[-1].lower()].add(sp)

    # 2) Alias cache canon names
    try:
        alias_inv_cache = globals().get("ALIAS_INV_CACHE") or {}
        for canon in set(alias_inv_cache.values()):
            parts = str(canon).split()
            if parts:
                m[parts[-1].lower()].add(canon)
    except Exception:
        pass

    # 3) Canon whitelist fallback
    try:
        for canon in globals().get("CANON_WHITELIST") or []:
            parts = normalize_name(canon).split()
            if parts:
                m[parts[-1].lower()].add(canon)
    except Exception:
        pass

    # Keep existing if we already had something and rows=None (don’t blow away)
    if not m and SURNAME_TO_CANON:
        return

    SURNAME_TO_CANON = {k: set(v) for k, v in m.items()}


def _canonicalize_who_ctx(
    raw_name: str, alias_inv, rows, idx, window: int = 8
) -> str | None:
    """sanitize → ban → location check → (surname disambig) → alias clamp"""
    if not raw_name:
        return None
    who = _sanitize_person_name(raw_name)
    if not who or _looks_like_locationish(who):
        return None

    # If it's a single token (likely surname), try context disambig BEFORE alias map
    parts = who.split()
    if len(parts) == 1:
        low = parts[0].lower()
        try:
            resolved = _resolve_surname_by_context(low, rows, idx, window=window)
            if resolved:
                who = resolved
        except Exception:
            pass

    # Alias correction last
    try:
        if alias_inv and "_alias_correct" in globals():
            who = _alias_correct(who, alias_inv or {})
    except Exception:
        pass
    return who


def _resolve_surname_by_context(
    lastname_low: str, rows, idx: int, window: int = 12
) -> str | None:
    """
    If 'lastname_low' maps to multiple canonical speakers, choose the one
    most consistent with nearby dialogue context.

    Preference:
      (1) most recent previous QUOTE row with that surname
      (2) next forward QUOTE row with that surname
      (3) nearest LOCKED quote with that surname (within window)
      (4) if exactly one canonical exists overall, return it; else None
    """
    _ensure_surname_map(rows)
    cands = list(SURNAME_TO_CANON.get(lastname_low, []))
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]

    def _is_quote(j):
        return bool(rows[j].get("is_quote"))

    def _spk(j):
        return (rows[j].get("speaker") or "").strip()

    def _locked(j):
        return bool(rows[j].get("_lock_speaker"))

    # (1) backward scan
    for j in range(idx - 1, max(-1, idx - window), -1):
        if _is_quote(j) and _spk(j) in cands:
            return _spk(j)

    # (2) forward scan
    for j in range(idx + 1, min(len(rows), idx + window)):
        if _is_quote(j) and _spk(j) in cands:
            return _spk(j)

    # (3) prefer a locked one if any in window (tie-break by proximity)
    near = [
        (j, _spk(j), _locked(j))
        for j in range(max(0, idx - window), min(len(rows), idx + window))
        if _is_quote(j) and _spk(j) in cands
    ]
    locked = [(j, sp) for (j, sp, lk) in near if lk]
    if locked:
        locked.sort(key=lambda tup: abs(idx - tup[0]))
        return locked[0][1]

    # (4) no signal
    return None


def _extract_surname_candidate(text: str) -> str | None:
    """
    Return a bare surname (lowercased) present in 'text' if it exists in SURNAME_TO_CANON.
    Handles King's/King’s.
    """
    import re

    t = (text or "").strip().lower()
    if not t or not SURNAME_TO_CANON:
        return None
    for ln in SURNAME_TO_CANON.keys():
        if re.search(rf"\b{ln}(?:['’]s)?\b", t):
            return ln
    return None


# safe default if not already present
try:
    ADDRESS_WINDOW
except NameError:
    ADDRESS_WINDOW = 8

# --- Descriptor stripping + "tail" name collapse ---
_DESC_LEADER_RX = re.compile(
    r"^(?:his|her|their|the)\s+(?:old|young|dear\s+)?(?:friend|brother|sister|mother|father|wife|husband|son|daughter|"
    r"companion|partner|buddy|pal|sergeant|officer|captain|colonel|lieutenant)\s+",
    re.IGNORECASE,
)

_TITLES_RX = re.compile(
    r"^(?:Mr|Mrs|Ms|Miss|Mister|Dr|Sir|Lady|Lord|Col|Capt|Gen|Sgt|Prof)\.?\s+",
    re.IGNORECASE,
)


# --- NEW: strip any character speakers from narration rows (final safety) ---
def _strip_character_speaker_from_narration(rows):
    out = []
    for r in rows:
        rr = dict(r)
        if not rr.get("is_quote"):
            sp = rr.get("speaker")
            if sp and sp not in ("Narrator", "Unknown"):
                rr["speaker"] = "Narrator"
        out.append(rr)
    return out


def _collapse_to_name_tail(s: str) -> str | None:
    """
    Drop descriptors like 'his friend' / titles and keep a clean person name,
    preferring the tail of the phrase (last 2 capitalized tokens).
    e.g. 'his friend Len Johnson' -> 'Len Johnson'
    """
    if not s:
        return None
    t = (s or "").strip()
    t = _DESC_LEADER_RX.sub("", t)
    t = _TITLES_RX.sub("", t)

    caps = re.findall(r"[A-Z][A-Za-z'-]+", t)
    if not caps:
        return None
    if len(caps) >= 2:
        return f"{caps[-2]} {caps[-1]}"
    return caps[-1]


# --- final precision gate using whitelist and sanity rules ---
def _final_precision_gate(
    results, whitelist: set | None, alias_inv: dict | None = None
):
    if not results:
        return results
    wl = set(whitelist or [])
    out, demoted = [], 0
    for r in results:
        rr = r
        sp = rr.get("speaker")
        if rr.get("is_quote") and sp and sp not in ("Unknown", "Narrator"):
            # alias-correct for whitelist check
            try:
                sp2 = _alias_correct(sp, alias_inv or {})
            except Exception:
                sp2 = sp
            bad = False
            # 1) require either whitelist membership (if non-empty) or pass our sanity test
            if wl and sp2 not in wl:
                bad = True
            # attempt to shrink before we judge
            sp2_shrunk = _shrink_long_person_phrase(sp2)
            if sp2_shrunk and sp2_shrunk not in {"Narrator", "Unknown"}:
                sp2 = sp2_shrunk
            # 2) sanity: >3 tokens, digits/underscores, or group phrases → bad
            parts = normalize_name(sp2).split()
            if len(parts) == 0 or len(parts) > 3:
                bad = True
            if re.search(r"[0-9_/]", sp2) or sp2.count("-") > 1:
                bad = True
            if " ".join(p.lower() for p in parts) in _GROUP_PHRASES:
                bad = True
            if bad:
                rr = dict(rr)
                rr["speaker"] = "Unknown"
                rr["_gate"] = "final_precision"
                demoted += 1
        out.append(rr)
    try:
        log(f"[gate] final_precision demoted: {demoted}")
    except Exception:
        pass
    return out


# === Safer narration sentence splitting (zero-bleed friendly) =================
# Replaces the old `_SENT_SPLIT_RX` and any narration splitter helpers.
# Guarantees:
#   • Never splits INSIDE quoted spans
#   • Preserves ellipses "..."
#   • Splits only at ., !, ? where it's plausible a new sentence starts

# Boundary detector for ., !, ? (we'll vet each match for safety)
_SENT_SPLIT_BOUNDARY = re.compile(r"([.!?])")


def _split_narration_into_sentences_safe(txt: str) -> list[str]:
    """
    Conservative narration splitter:
      - never splits inside quoted spans
      - preserves ellipses '...'
      - tries to split only when a new sentence likely starts (space + Capital)
    Applies to *narration only*. Do not use for quoted dialogue.
    """
    t = (txt or "").strip()
    if not t:
        return []

    spans = _quote_spans(t)  # list[(start, end)] of quoted segments

    def _in_quote(ix: int) -> bool:
        # True if index `ix` falls inside any quoted span
        for a, b in spans:
            if a <= ix < b:
                return True
        return False

    out: list[str] = []
    cur: list[str] = []
    i = 0
    while i < len(t):
        m = _SENT_SPLIT_BOUNDARY.search(t, i)
        if not m:
            cur.append(t[i:])
            break

        j = m.start(1)  # punctuation index (., !, or ?)

        # 1) Don't split inside quotes
        if _in_quote(j):
            i = j + 1
            continue

        # 2) Keep ellipses intact
        if j + 2 < len(t) and t[j : j + 3] == "...":
            i = j + 3
            continue

        # 3) Don't split if a second dot follows (.. or ...)
        k = j + 1
        if k < len(t) and t[k] == ".":
            i = k + 1
            continue

        # 4) Require plausible sentence start ahead: whitespace then Capital
        while k < len(t) and t[k].isspace():
            k += 1
        if k < len(t) and t[k : k + 1].isupper():
            # Commit split before k, start new sentence at k
            cur.append(t[i:k])
            seg = "".join(cur).strip()
            if seg:
                out.append(seg)
            cur = []
            i = k
            continue

        # Otherwise keep scanning
        i = j + 1

    last = "".join(cur).strip()
    if last:
        out.append(last)

    # Remove empties
    return [s for s in out if s]


# --- Backward-compat adapter so existing code using `_SENT_SPLIT_RX.split(...)` still works
class _SentSplitSafeAdapter:
    def split(self, s: str) -> list[str]:
        return _split_narration_into_sentences_safe(s)


# Replace the old regex object with our adapter
_SENT_SPLIT_RX = _SentSplitSafeAdapter()
# ==============================================================================


_ATTRIB_VERBS_COMMON = [
    "said",
    "asked",
    "explained",
    "added",
    "replied",
    "murmured",
    "whispered",
    "yelled",
    "shouted",
    "called",
    "told",
    "continued",
    "went on",
    "interposed",
    "agreed",
    "reminded",
    "repeated",
    "urged",
    "demanded",
    "began",
    "spoke up",
    "insisted",
    "remarked",
    "noted",
]
_ACTION_VERBS_COMMON = [
    "nodded",
    "smiled",
    "shrugged",
    "laughed",
    "grinned",
    "glanced",
    "looked",
    "sighed",
    "winced",
    "frowned",
    "gasped",
    "groaned",
    "snorted",
    "stared",
    "scowled",
]
_NAME_RX = r"[A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+){0,2}"

# verb-first end-of-sentence: "… explained Smith."
_ATTRIB_NARR_RX = re.compile(
    rf'\b(?:{ "|".join(re.escape(v) for v in _ATTRIB_VERBS_COMMON) })\b\s+{_NAME_RX}\s*[.!?]$',
    re.IGNORECASE,
)
# name-first end-of-sentence: "… Smith nodded."
_NAME_FIRST_BEAT_RX = re.compile(
    rf'\b{_NAME_RX}\s+\b(?:{ "|".join(re.escape(v) for v in (_ATTRIB_VERBS_COMMON + _ACTION_VERBS_COMMON)) })\b\s*[.!?]$',
    re.IGNORECASE,
)


def _promote_post_quote_attrib(rows, *_args):
    """
    If a non-quote beat immediately FOLLOWS a quote, and it looks like an attribution/action
    fragment, promote it to is_quote=True and inherit the PREV quote's speaker.
    Works even if the beat already has a non-empty (possibly wrong) speaker.
    """
    if not rows:
        return rows
    out = list(rows)
    for i in range(len(out) - 1):
        cur = out[i]
        nxt = out[i + 1]
        if not cur.get("is_quote"):
            # We only care when PREV is a quote and current is a beat; shift window by 1
            continue
        # candidate beat is the row right AFTER a quote
        beat_idx = i + 1
        beat = out[beat_idx]
        if beat.get("is_quote"):  # already a quote → leave
            continue
        txt = (beat.get("text") or "").strip()
        if not txt:
            continue
        if not _is_attrib_fragment_local(txt, max_words=24):
            continue
        sp = (cur.get("speaker") or "").strip()
        if not sp:
            # If previous quote somehow Unknown, don't fabricate — let triplet handle it
            continue

        newb = dict(beat)
        newb["is_quote"] = True
        newb["speaker"] = sp
        newb["_post_quote_promoted"] = True
        newb["_promoted_quote"] = True
        # do NOT lock; allow later heuristics to adjust if needed
        out[beat_idx] = newb
        try:
            _ensure_surname_map(out)  # build surname map from current rows
            sname = _extract_surname_candidate(
                txt
            )  # pull 'king' / 'hatfield' / 'washburn'...
            if sname:
                resolved = _resolve_surname_by_context(sname, out, beat_idx, window=12)
                if resolved and resolved != newb["speaker"]:
                    newb["speaker"] = resolved
                    newb["_surname_resolved"] = sname
        except Exception:
            pass
        try:
            record_attrib_op_row(
                "post_quote_attrib",
                "promote",
                newb,
                beat.get("speaker"),
                sp,
                "post",
                beat_idx,
            )
        except Exception:
            pass
    return out


def _row_has_any_quote_char(s: str) -> bool:
    """
    True if the string contains any double or single quote glyph we care about.
    (Fixes the "'‘" bug and covers ASCII + curly quotes.)
    """
    if not s:
        return False
    # ASCII
    if '"' in s or "'" in s:
        return True
    # Curly / “smart” quotes
    return ("\u201c" in s) or ("\u201d" in s) or ("\u2018" in s) or ("\u2019" in s)


def _edge_peel_and_attach(rows: list[dict], i: int, alias_inv) -> None:
    """
    For a *narrator* row that contains quote glyphs:
      - If there's an attribution HEAD before the first quote → attach+LOCK to the NEXT quote.
      - If there's an attribution TAIL after the last quote  → attach+LOCK to the PREVIOUS quote.
    We DO NOT split inside quoted spans. We leave the narrator text intact unless
    KEEP_ATTRIB_TEXT and ATTACH_ATTRIB_TO_QUOTE are set, in which case we also
    copy the attrib string into the neighbor quote's text.
    """
    r = rows[i]
    txt = r.get("text") or ""
    spans = _quote_spans(txt)
    if not spans:
        return

    # 1) HEAD (before first quote) → NEXT quote
    pre = txt[: spans[0][0]].strip()
    if pre and _looks_like_attribution_fragment(pre):
        who = _speaker_from_attrib_fragment(pre)
        if who and who != "Narrator":
            who = _alias_correct(who, alias_inv or {})
            j = i + 1
            while j < len(rows) and not _looks_like_direct_speech_strict(
                rows[j].get("text") or ""
            ):
                j += 1

            if j < len(rows):
                nxt = dict(rows[j])
                prev_sp = (nxt.get("speaker") or "").strip()
                if prev_sp in ("", "Unknown", "Narrator"):
                    nxt["speaker"] = who
                    nxt["_lock_speaker"] = True
                    nxt["_locked_to"] = who
                    nxt["_lock_reason"] = "head_attrib_edge"
                    if KEEP_ATTRIB_TEXT and ATTACH_ATTRIB_TO_QUOTE:
                        nxt["text"] = (
                            pre + " " + (nxt.get("text") or "").lstrip()
                        ).strip()
                    rows[j] = nxt
                    log(
                        f"[attrib-head-edge] -> '{who}' | {(nxt.get('text','')[:60]).replace(chr(10),' ')}…"
                    )

    # 2) TAIL (after last quote) → PREVIOUS quote
    tail = txt[spans[-1][1] :].strip()
    if tail and _looks_like_attribution_fragment(tail):
        who = _speaker_from_attrib_fragment(tail)
        if who and who != "Narrator":
            who = _alias_correct(who, alias_inv or {})
            j = i - 1
            while j >= 0 and not _looks_like_direct_speech_strict(
                rows[j].get("text") or ""
            ):
                j -= 1

            if j >= 0:
                prev = dict(rows[j])
                prev_sp = (prev.get("speaker") or "").strip()
                if prev_sp in ("", "Unknown", "Narrator"):
                    prev["speaker"] = who
                    prev["_lock_speaker"] = True
                    prev["_locked_to"] = who
                    prev["_lock_reason"] = "tail_attrib_edge"
                    if KEEP_ATTRIB_TEXT and ATTACH_ATTRIB_TO_QUOTE:
                        prev["text"] = (
                            (prev.get("text") or "").rstrip() + " " + tail
                        ).strip()
                    rows[j] = prev
                    log(
                        f"[attrib-tail-edge] -> '{who}' | {(prev.get('text','')[:60]).replace(chr(10),' ')}…"
                    )


def _split_narrator_on_inline_attrib_and_actions(results, alias_inv):
    """
    Split long *narrator* rows that contain inline attribution/action mini-clauses,
    while preserving zero-bleed:
      - NEVER split inside quoted spans.
      - If a narrator row contains quote glyphs, we do NOT peel here (index unstable while building).
        We defer peeling to a post-pass on the fully built list so indices are correct.
      - Otherwise, conservatively split narration (not inside quotes; preserves ellipses) and
        only emit multiple narrator rows when at least one sentence looks like an attrib/action beat.
    """
    if not results:
        return results

    out = []
    for r in results:
        txt = r.get("text") or ""
        # Preserve pre-marked quotes exactly
        if r.get("is_quote"):
            out.append(r)
            continue

        # Defer: if row has any quote glyphs, just copy it through for now
        # (peeling is done in a stable post-pass)
        if _row_has_any_quote_char(txt):
            out.append(r)
            continue

        # Cheap guard: skip work if only one sentence likely
        if not re.search(r"[.!?].+[.!?]", txt):
            out.append(r)
            continue

        # Conservative narration splitter (no splits inside quotes; preserves ellipses)
        sents = _split_narration_into_sentences_safe(txt.strip())
        if len(sents) <= 1:
            out.append(r)
            continue

        # Only split if at least one sentence looks like an attribution/action beat
        ATTRIB_NARR_RX = globals().get("_ATTRIB_NARR_RX")
        NAME_FIRST_BEAT_RX = globals().get("_NAME_FIRST_BEAT_RX")
        should_split = True  # default to split if detectors are absent
        if (ATTRIB_NARR_RX is not None) or (NAME_FIRST_BEAT_RX is not None):
            should_split = any(
                (ATTRIB_NARR_RX.search(s) if ATTRIB_NARR_RX else False)
                or (NAME_FIRST_BEAT_RX.search(s) if NAME_FIRST_BEAT_RX else False)
                for s in sents
            )
        if not should_split:
            out.append(r)
            continue

        # Emit each sentence as its own narrator row
        for s in sents:
            s = (s or "").strip()
            if not s:
                continue
            out.append({"text": s, "speaker": "Narrator", "is_quote": False})

    return out


def _edge_peel_pass_inplace(results, alias_inv):
    """
    Walk the *finalized list* and safely peel HEAD/TAIL attribution around quoted spans
    found in narrator rows that contain quote glyphs. Indices are stable here.
    """
    if not results:
        return results
    for i, r in enumerate(results):
        if r.get("is_quote"):
            continue
        txt = r.get("text") or ""
        if not _row_has_any_quote_char(txt):
            continue
        try:
            _edge_peel_and_attach(results, i, alias_inv)
        except Exception as e:
            try:
                log(f"[edge-peel pass] skipped at {i}: {e}")
            except Exception:
                pass
    return results


def _reassert_quote_flags_inplace(results):
    """
    If a row has any real quote span, force is_quote=True.
    This collapses residual bleed where a narrator row still contains quotes.
    """
    if not results:
        return results
    changes = 0
    out = results
    for r in out:
        t = _norm_unicode_quotes(r.get("text") or "")
        spans = _quote_spans(t)
        if spans and not r.get("is_quote", False):
            r["is_quote"] = True
            changes += 1
    try:
        DBG.setdefault("reassert_flag_changes", 0)
        DBG["reassert_flag_changes"] += changes
    except Exception:
        pass
    return out


def _split_results_on_multiple_quote_spans(rows, alias_inv=None):
    """
    Split any row that contains >1 opening→closing quote spans into alternating
    Narrator/Quote rows. Preserves order and keeps any between-quote narration.

    GUARANTEES:
      • Never emits an empty `""` child row.
      • Every speech child retains an opening and a closing quote; will synthesize if missing.
      • Between-quote connectors are Narrator and tagged as intentional demotions.
      • Only the first emitted child keeps the original _rid (keeps auto-restore sane).
    """
    if globals().get("QUOTES_ARE_ATOMIC"):
        return rows
    if not rows:
        return rows

    out = []

    for r in rows:
        base = dict(r)
        t_norm = _norm_unicode_quotes(base.get("text") or "")
        spans = _quote_spans_balanced(t_norm)

        # 0 or 1 span → passthrough
        if len(spans) <= 1:
            out.append(base)
            continue

        pieces = []
        last = 0
        for lo, hi in spans:
            # pre/mid connector
            if lo > last:
                conn = t_norm[last:lo]
                if conn and conn.strip():
                    pieces.append(("connector", conn))
            # speech piece
            speech = t_norm[lo:hi]
            pieces.append(("speech", speech))
            last = hi

        # trailing connector
        if last < len(t_norm):
            tail = t_norm[last:]
            if tail and tail.strip():
                pieces.append(("connector", tail))

        cleaned = []
        for kind, seg in pieces:
            s = (seg or "").strip()
            if not s:
                continue
            if kind == "speech":
                # Ensure both sides quoted; synthesize if needed.
                has_open = s.startswith('"') or s.startswith("“")
                has_close = s.endswith('"') or s.endswith("”")
                if not has_open:
                    s = '"' + s
                if not has_close:
                    s = s + '"'
                # Drop truly empty quotes like "" or “”
                if s in ('""', "“”"):
                    continue
                cleaned.append(("speech", s))
            else:
                # Never emit empty connector or "" artefact
                if s not in ('""', "“”"):
                    cleaned.append(("connector", s))

        if not cleaned:
            # Nothing safe to split → passthrough original row
            out.append(base)
            continue

        first = True
        for kind, seg in cleaned:
            rr = dict(base)
            rr["text"] = seg
            if kind == "speech":
                rr["is_quote"] = True
            else:
                rr["is_quote"] = False
                rr["speaker"] = "Narrator"
                rr["_qa_demoted_quote"] = True  # intentional demote (connector)
            if first:
                first = False
            else:
                rr.pop("_rid", None)  # avoid RID collisions
            out.append(rr)

    return out


# --- REPLACE: universal-strict person-name sanitizer ---
_FUNC_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "for",
    "nor",
    "if",
    "who",
    "that",
    "which",
    "because",
    "as",
    "than",
    "in",
    "with",
    "of",
    "to",
    "at",
    "by",
    "on",
    "from",
    "into",
    "onto",
    "upon",
    "over",
    "under",
    "after",
    "before",
    "around",
    "through",
    "between",
    "without",
    "within",
    "behind",
    "beside",
    "near",
    "inside",
    "outside",
}
_GROUP_PHRASES = {
    "you men",
    "you guys",
    "old men",
    "men",
    "people",
    "crowd",
    "comrades",
    "each of you",
    "each of ya",
    "each of y'all",
    "every one of you",
    "both of you",
    "you two",
    "you three",
    "you boys",
    "you girls",
}

_BAD_CAP_TOKS = {
    # common location/object words that show up title-cased
    "Apartment",
    "Street",
    "Road",
    "Avenue",
    "Boulevard",
    "County",
    "State",
    "City",
    "Oregon",
    "Washington",
    "California",
    "Astoria",
    "Portland",
    "Ilwaco",
    "Longview",
    "Club",
    "Camp",
    "Room",
    "House",
    "Hotel",
    "Bridge",
    "Jail",
    "Car",
    "Toyota",
    "Lexus",
    "Subaru",
    "Army",
    "United",
    "States",
}
_PREP_TAIL_RX = re.compile(
    r"\b(?:in|at|on|of|from|near|inside|outside|behind)\b.*$", re.IGNORECASE
)


# --- NEW: shrink overlong person phrases down to a plausible name tail ---
def _shrink_long_person_phrase(name: str) -> str | None:
    """
    Try to reduce long junky 'names' to a real person name tail.
    Examples:
      'Zack S Cheap Furnished Apartment In Astoria Oregon' -> 'Zack'
      'Mr. Steven King of Portland' -> 'Steven King'
    If nothing plausible remains, return None.
    """
    if not name:
        return None
    t = normalize_name(name).strip()

    # Drop trailing scene/location tails
    t = re.sub(
        r"\b(?:in|at|on|of|from|near|inside|outside|behind)\b.*$",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()

    # Kill possessive orphan letters: "Zack 's Cheap..." or "Zack S Cheap..."
    t = re.sub(r"\b([A-Za-z])\b", "", t)  # remove single-letter tokens
    t = re.sub(r"\s+", " ", t).strip()

    # Prefer the last 1–2 capitalized tokens (a 'tail' like 'Steven King')
    caps = re.findall(r"[A-Z][A-Za-z'\-]+", t)
    if caps:
        tail = " ".join(caps[-2:]) if len(caps) >= 2 else caps[-1]
    else:
        tail = t

    # Run through your normal sanitizer
    tail = _sanitize_person_name(tail) or None
    return tail


def _sanitize_person_name(s: str) -> str | None:
    if not s:
        return None
    # role canon first if you have it
    try:
        rc = _canonicalize_role(s)
        if rc:
            return rc
    except Exception:
        pass

    cand = normalize_name(s).strip()
    cand = re.sub(r"\s+", " ", cand)

    # drop trailing prepositional scene tails
    cand = _PREP_TAIL_RX.sub("", cand).strip()

    # strip possessive "'s"
    cand = re.sub(r"\b([A-Za-z][\w'\-]*)'s\b", r"\1", cand)

    # tokenize and build a clean short name
    toks = cand.split()
    clean = []
    for tok in toks:
        low = tok.lower().strip(".")
        # kill single-letter tokens (e.g., 'S' from "Zack's")
        if len(tok) == 1:
            break
        # stop on function/connector words
        if low in _FUNC_STOP:
            break
        # reject lowercase tokens (except titles)
        if not tok[0].isupper() and low not in {
            "mr",
            "mrs",
            "ms",
            "dr",
            "sir",
            "lady",
            "lord",
        }:
            break
        # reject obvious object/location cap words
        if tok in _BAD_CAP_TOKS:
            break
        clean.append(tok)
        if len(clean) == 3:
            break

    cand = " ".join(clean).strip()
    if not cand or len(cand) < 2:
        return None

    # groups / vocatives
    if cand.lower() in _GROUP_PHRASES:
        return None

    # digits or too many hyphens → junk
    if re.search(r"[0-9_/]", cand) or cand.count("-") > 1:
        return None

    cand = cand.title()

    # final ban check if you have one
    try:
        if _is_banned(cand):
            return None
    except Exception:
        pass

    return cand


_BAN_TOKENS = {
    # place/thing words you never want in a person name
    "apartment",
    "store",
    "hardware",
    "street",
    "road",
    "avenue",
    "county",
    "state",
    "oregon",
    "washington",
    "seaside",
    "astoria",
    "cheap",
    "furnished",
    "office",
    "chapter",
    "scene",
}

# ---- Speaker candidate canonicalizer (uses your existing helpers) ----


# Light heuristic to reject place/thing phrases that sometimes slip in as "names"
def _looks_like_locationish(name: str) -> bool:
    low = (name or "").strip().lower()
    if not low:
        return False
    toks = re.findall(r"[a-z]+", low)
    if not toks:
        return False
    # phrases with prepositions → likely locations/things (e.g., "House on the Hill")
    if len(toks) >= 4 and any(t in {"in", "of", "at", "on"} for t in toks):
        return True
    # common location/venue words
    if any(
        t
        in {
            "street",
            "road",
            "avenue",
            "blvd",
            "lane",
            "highway",
            "county",
            "state",
            "city",
            "town",
            "office",
            "store",
            "hotel",
            "motel",
            "room",
            "suite",
            "building",
            "hospital",
            "school",
            "university",
            "church",
            "library",
            "station",
        }
        for t in toks
    ):
        return True
    # trailing proper-nouny location tokens
    if toks[-1] in {"oregon", "washington", "avenue", "street", "road"}:
        return True
    return False


def _canonicalize_who(raw_name: str, alias_inv=None) -> str | None:
    """
    Best-effort: sanitize → ban-check → location-guard → alias-correct.
    Returns canonical speaker or None.
    """
    if not raw_name:
        return None
    # Your sanitizer already handles role canon + banning via _is_banned
    who = _sanitize_person_name(raw_name)
    if not who:
        return None
    if _looks_like_locationish(who):
        return None
    # Optional alias correction
    try:
        if alias_inv and "_alias_correct" in globals():
            who = _alias_correct(who, alias_inv or {})
    except Exception:
        pass
    return who or None


# --- NEW: extract leading attribution clause from long narrator lines ---
_LEAD_ATTRIB_VERBS = [
    "said",
    "asked",
    "explained",
    "added",
    "replied",
    "murmured",
    "whispered",
    "yelled",
    "shouted",
    "called",
    "told",
    "continued",
    "went on",
    "interposed",
    "agreed",
    "reminded",
    "repeated",
    "urged",
    "demanded",
    "began",
    "spoke up",
    "said simply",
    "said softly",
]
_LEAD_ATTRIB_VERBS_RX = r"(?:%s)" % "|".join(
    re.escape(v) for v in sorted(set(_LEAD_ATTRIB_VERBS), key=len, reverse=True)
)
_LEAD_NAME_RX = r"[A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+){0,2}"

_LEADING_ATTRIB_RXES = [
    # verb-first: "said Red contemplatively, …"
    re.compile(
        rf"^(?P<verb>{_LEAD_ATTRIB_VERBS_RX})\s+(?P<who>{_LEAD_NAME_RX})\b",
        re.IGNORECASE,
    ),
    # name-first: "Red said softly, …"
    re.compile(
        rf"^(?P<who>{_LEAD_NAME_RX})\s+(?P<verb>{_LEAD_ATTRIB_VERBS_RX})\b",
        re.IGNORECASE,
    ),
]


def _extract_leading_attrib_clause(text: str, alias_inv: dict) -> str | None:
    t = (text or "").strip()
    if not t:
        return None
    for rx in _LEADING_ATTRIB_RXES:
        m = rx.search(t)
        if not m:
            continue
        who_raw = (m.group("who") or "").strip()
        who = _sanitize_person_name(who_raw) or ""
        if not who or _is_banned(who):
            return None
        try:
            who = _alias_correct(who, alias_inv or {})
        except Exception:
            pass
        return who
    return None


# --- NEW/REPLACE: final junk-speaker demotion before finalize --


def _post_speaker_sanity(rows):
    """
    Final sweep before finalize:
      - Normalize any '...guard...' variants to 'Guard'
      - Demote silly speakers (too many tokens, function words, digits, etc.)
        to Unknown (for quotes) or Narrator (for narration).
    """
    out = []
    # tokens that shouldn't appear in a clean person name
    _BAD_NAME_TOKS = {
        "if",
        "who",
        "that",
        "which",
        "because",
        "as",
        "than",
        "of",
        "in",
        "on",
        "at",
        "by",
        "from",
        "into",
        "onto",
        "upon",
        "over",
        "under",
        "after",
        "before",
        "around",
        "through",
        "between",
        "without",
        "within",
        "behind",
        "beside",
        "near",
        "inside",
        "outside",
        "guys",
        "men",
        "old",
        "young",
        "you",
    }
    role_guard_rx = re.compile(r"\bguard\b", re.IGNORECASE)

    for r in rows:
        rr = dict(r)  # work on a copy
        txt = rr.get("text") or ""
        sp = rr.get("speaker") or ""

        # Role canon: any 'guard' phrase -> Guard
        if sp and role_guard_rx.search(sp):
            rr["speaker"] = "Guard"
            sp = "Guard"  # refresh local var

        # attempt to shrink silly long phrases into a clean name
        shrunk = _shrink_long_person_phrase(sp)
        if shrunk and shrunk not in {"Narrator", "Unknown"}:
            rr["speaker"] = shrunk
            sp = shrunk  # re-evaluate with the shrunk name

        # Demote silly speakers
        if sp and sp not in ("Narrator", "Unknown"):
            parts = (normalize_name(sp) or "").split()
            junk = (
                len(parts) == 0
                or len(parts) > 3
                or any(p.lower() in _BAD_NAME_TOKS for p in parts)
                or re.search(r"[0-9_/]", sp) is not None
                or sp.count("-") > 1
            )
            if junk:
                rr["speaker"] = (
                    "Unknown" if looks_like_direct_speech(txt) else "Narrator"
                )

        out.append(rr)

    return out


def _resolve_unknowns(results, qmap, alias_inv, window=4):
    """
    Final pass to resolve lingering Unknown speakers on quote rows.

    Order of strategies:
      1) Two-party ping-pong in local clusters:
         • A ? B → ? = A   (classic alternation)
         • A ? A with another participant nearby → ? = that other participant
      2) Carry monologue across short gaps:
         • A ?? A (with only brief narration in-between) → fill ? with A
      3) Fallback: nearest known quote speaker within `window`.

    Notes:
      • Never glue narration into quotes; only set/lock the target quote's speaker.
      • Uses ROLE_CANON (if present) and surname disambiguation (if available).
    """
    if not results:
        return results

    out = list(results)
    n = len(out)

    def is_quote(i):
        return 0 <= i < n and looks_like_direct_speech(out[i].get("text") or "")

    def spk(i):
        return (out[i].get("speaker") or "").strip() if 0 <= i < n else ""

    def contains_name(i, name):
        if i < 0 or i >= n or not name:
            return False
        fn = globals().get("_contains_name")
        try:
            return bool(fn and fn(out[i].get("text") or "", name, alias_inv))
        except Exception:
            return False

    def surname_disambig(name, i):
        if not name or " " in name:
            return name
        fn = globals().get("_resolve_surname_by_context")
        if not fn:
            return name
        try:
            resolved = fn(
                name.lower(), out, i, window=globals().get("ADDRESS_WINDOW", 6)
            )
            return resolved or name
        except Exception:
            return name

    def canon(name):
        nm = (name or "").strip()
        if not nm:
            return ""
        # optional role canon (e.g., "the guard" → "Guard")
        if "ROLE_CANON" in globals():
            nm = globals()["ROLE_CANON"].get(nm.lower(), nm)
        nm = _sanitize_person_name(nm) or ""
        if nm and nm not in {"Narrator", "Unknown"} and not _is_banned(nm):
            nm = _alias_correct(nm, alias_inv or {})
            nm = surname_disambig(nm, i_cur)
            return nm
        return ""

    def set_spk(i, name, reason):
        nm = canon(name)
        if not nm:
            return False
        prev = spk(i)
        if prev in ("", "Unknown", "Narrator"):
            out[i]["speaker"] = nm
        out[i]["_lock_speaker"] = True
        out[i]["_locked_to"] = nm
        out[i]["_lock_reason"] = reason
        try:
            DBG["unknown_filled"] = DBG.get("unknown_filled", 0) + 1
        except Exception:
            pass
        return True

    def nearest_known_quote_speaker(idx):
        # backward, then forward scan across quotes only
        for j in range(idx - 1, max(-1, idx - window), -1):
            if is_quote(j):
                s = spk(j)
                if s not in ("", "Unknown", "Narrator"):
                    return s
        for j in range(idx + 1, min(n, idx + window)):
            if is_quote(j):
                s = spk(j)
                if s not in ("", "Unknown", "Narrator"):
                    return s
        return ""

    # --- 1) Ping-pong patterns on Unknown quote rows ---
    for i_cur in range(n):
        if not is_quote(i_cur) or spk(i_cur) != "Unknown":
            continue

        # find nearest known quote speakers backward and forward (within 3 quotes)
        prev_k = next_k = ""
        # search backward
        steps = 0
        j = i_cur - 1
        while j >= 0 and steps < 6:
            if is_quote(j):
                s = spk(j)
                if s not in ("", "Unknown", "Narrator"):
                    prev_k = s
                    break
                steps += 1
            j -= 1
        # search forward
        steps = 0
        j = i_cur + 1
        while j < n and steps < 6:
            if is_quote(j):
                s = spk(j)
                if s not in ("", "Unknown", "Narrator"):
                    next_k = s
                    break
                steps += 1
            j += 1

        # A ? B  → ? = A
        if prev_k and next_k and prev_k != next_k:
            if not contains_name(i_cur, prev_k):
                if set_spk(i_cur, prev_k, "pingpong_A?B->A"):
                    continue

        # A ? A  → ? = B (if exactly one other participant is locally present)
        if prev_k and next_k and prev_k == next_k:
            # collect local known speakers nearby (±4 rows)
            neighborhood = set()
            for k in range(max(0, i_cur - 4), min(n, i_cur + 5)):
                if is_quote(k):
                    s = spk(k)
                    if s not in ("", "Unknown", "Narrator"):
                        neighborhood.add(s)
            # exclude A (prev_k)
            neighborhood.discard(prev_k)
            if len(neighborhood) == 1:
                other = list(neighborhood)[0]
                if not contains_name(i_cur, other):
                    if set_spk(i_cur, other, "pingpong_A?A->other"):
                        continue

    # --- 2) Carry monologue across short gaps (A ?? A → fill with A) ---
    for i_cur in range(n):
        if not is_quote(i_cur) or spk(i_cur) != "Unknown":
            continue

        back = nexts = ""
        # back known speaker within 3 quotes
        steps = 0
        j = i_cur - 1
        while j >= 0 and steps < 6:
            if is_quote(j):
                s = spk(j)
                if s not in ("", "Unknown", "Narrator"):
                    back = s
                    break
                steps += 1
            j -= 1

        # forward known speaker within 3 quotes
        steps = 0
        j = i_cur + 1
        while j < n and steps < 6:
            if is_quote(j):
                s = spk(j)
                if s not in ("", "Unknown", "Narrator"):
                    nexts = s
                    break
                steps += 1
            j += 1

        if back and not nexts:
            if not contains_name(i_cur, back):
                if set_spk(i_cur, back, "carry_back_monologue"):
                    continue
        elif nexts and not back:
            if not contains_name(i_cur, nexts):
                if set_spk(i_cur, nexts, "carry_fwd_monologue"):
                    continue
        elif back and nexts and back == nexts:
            if not contains_name(i_cur, back):
                if set_spk(i_cur, back, "carry_both_monologue"):
                    continue

    # --- 3) Fallback: nearest known quote speaker within window ---
    for i_cur in range(n):
        if not is_quote(i_cur) or spk(i_cur) != "Unknown":
            continue
        neigh = nearest_known_quote_speaker(i_cur)
        if neigh and not contains_name(i_cur, neigh):
            set_spk(i_cur, neigh, "fallback_nearest_known")

    return out


_ADDR_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "for",
    "nor",
    "in",
    "with",
    "of",
    "to",
    "at",
    "by",
    "on",
    "from",
    "as",
    "than",
    "into",
    "onto",
    "upon",
    "over",
    "under",
    "after",
    "before",
    "around",
    "through",
    "between",
    "without",
    "within",
}


def _content_set(text: str):
    toks = [
        w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", normalize_name(text))
    ]
    return {w for w in toks if len(w) > 2 and w not in _ADDR_STOP}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / float(len(a | b))


def _nearest_other_speaker(results, idx, avoid, window=ADDRESS_WINDOW):
    """Find nearest quoted speaker != avoid within window before/after idx."""
    # look backward
    for j in range(idx - 1, max(-1, idx - window) - 1, -1):
        r = results[j]
        if looks_like_direct_speech(r["text"]):
            sp = r["speaker"]
            if sp not in ("Narrator", "Unknown") and sp != avoid:
                return sp
    # forward
    for j in range(idx + 1, min(len(results), idx + window + 1)):
        r = results[j]
        if looks_like_direct_speech(r["text"]):
            sp = r["speaker"]
            if sp not in ("Narrator", "Unknown") and sp != avoid:
                return sp
    return None


def _analyze_dialogue_pair(prev_txt: str, cur_txt: str) -> bool:
    """
    Decide if prev and cur quotes are very likely from different speakers.
    """
    if not prev_txt or not cur_txt:
        return False
    pt, ct = prev_txt.strip(), cur_txt.strip()
    pt_low, ct_low = pt.lower(), ct.lower()

    # Question → anything
    if pt.endswith("?"):
        return True
    # Statement → affirmation
    if ct_low in {
        "yes",
        "yeah",
        "yep",
        "right",
        "exactly",
        "of course",
        "sure",
        "indeed",
    }:
        return True
    # Two declaratives
    if not pt.endswith("?") and not ct.endswith("?"):
        return True
    # Two questions
    if pt.endswith("?") and ct.endswith("?"):
        return True
    # Short after long
    if len(pt.split()) > 10 and len(ct.split()) <= 4:
        return True
    return False


def _carry_burst_attribution(rows, max_gap=3):
    """
    Within a contiguous run of quotes (no narrator attribution lines),
    carry forward the last confident speaker across short Unknown quotes.

    - A 'confident' speaker != Unknown/Narrator
    - Only patches quotes with <=2 tokens (micro) or <=12 chars (ultra short)
    - Resets when we see an explicit attribution narrator fragment
    """

    def tok_count(s):
        return len(re.findall(r"[A-Za-z0-9']+", s or ""))

    def is_ultra_short(s):
        s = (s or "").strip()
        return tok_count(s) <= 2 or len(re.sub(r"\s+", "", s)) <= 12

    out = rows
    last_conf = None
    gap = 0
    for i, r in enumerate(out):
        txt = (r.get("text") or "").strip()

        # narrator attribution resets the carry
        if (not r.get("is_quote")) and _ATTRIB_LINE_RX.match(txt or ""):
            last_conf = None
            gap = 0
            continue

        if r.get("is_quote"):
            sp = (r.get("speaker") or "Unknown").strip()
            if sp not in ("Unknown", "Narrator"):
                last_conf = sp
                gap = 0
                continue

            # Unknown micro-quote → inherit if we have a recent confident speaker
            if last_conf and gap <= max_gap and is_ultra_short(txt):
                out[i]["speaker"] = last_conf
                log(f"[burst-carry] '{last_conf}' -> {txt[:40]}…")
                gap += 1
            else:
                gap += 1
        else:
            # other narrator row breaks the carry
            last_conf = None
            gap = 0
    return out


def _qa_turn_taking(rows):
    """
    Conservative Q→A / short-reply turn-taking:
      - If a KNOWN quote ends with '?' and the immediately following quote is Unknown,
        assign that next quote to the nearest OTHER speaker if available.
      - If a long declarative is followed by a very short Unknown reply (<=4 words),
        try the same nearest-other assignment.
    Never overwrites locks or non-Unknown speakers.
    """
    if not rows:
        return rows

    out = [dict(r) for r in rows]
    n = len(out)

    def nearest_other(idx, avoid):
        # prefer forward (we're moving right), then backward
        for j in range(idx + 1, min(n, idx + 1 + ADDRESS_WINDOW)):
            r = out[j]
            if looks_like_direct_speech(r.get("text", "")):
                sp = r.get("speaker")
                if sp not in ("Narrator", "Unknown") and sp != avoid:
                    return sp
        for j in range(idx - 1, max(-1, idx - 1 - ADDRESS_WINDOW), -1):
            r = out[j]
            if looks_like_direct_speech(r.get("text", "")):
                sp = r.get("speaker")
                if sp not in ("Narrator", "Unknown") and sp != avoid:
                    return sp
        return None

    def word_count(s):
        return len(re.findall(r"[A-Za-z0-9']+", s or ""))

    for i in range(n - 1):
        a, b = out[i], out[i + 1]
        if not (
            looks_like_direct_speech(a.get("text", ""))
            and looks_like_direct_speech(b.get("text", ""))
        ):
            continue
        if b.get("_lock_speaker"):
            continue
        if (b.get("speaker") or "Unknown") != "Unknown":
            continue

        a_txt = (a.get("text") or "").strip()
        a_sp = a.get("speaker")
        b_txt = (b.get("text") or "").strip()

        # Only proceed if A has a known speaker
        if a_sp in ("Narrator", "Unknown", None, ""):
            continue

        # Case 1: A ends with '?' → b likely a reply by NOT A
        if a_txt.endswith("?"):
            other = nearest_other(i, avoid=a_sp) or None
            # if we don't see a different known speaker nearby, we stay conservative
            if other and not _contains_name(b_txt, other):
                b["speaker"] = other
                b["_lock_reason"] = "qa-next"
                out[i + 1] = b
                log(f"[qa] A? → next='{other}' | {b_txt[:60]}…")
                continue

        # Case 2: A is long, B is a very short non-question → likely a reply by NOT A
        if (
            (not a_txt.endswith("?"))
            and (word_count(a_txt) >= 12)
            and (word_count(b_txt) <= 4)
            and (not b_txt.endswith("?"))
        ):
            other = nearest_other(i, avoid=a_sp) or None
            if other and not _contains_name(b_txt, other):
                b["speaker"] = other
                b["_lock_reason"] = "qa-short-reply"
                out[i + 1] = b
                log(f"[qa] long→short → next='{other}' | {b_txt[:60]}…")

    return out


# --- Stitch rows by quote-balance, independent of is_quote (AGGRESSIVE, pre-attribution) ---
def _stitch_rows_by_quote_balance(results, *args, **kwargs):
    """
    Soft-wrap stitch: glue narration continuations to an open quote.
    Safer variant:
      - ignores apostrophes/single quotes
      - won't stitch if next line starts with an opener (“ " «)
      - won't stitch if next line is an attribution-looking fragment (e.g., ", said X." / "X said.")
    """
    import re

    if not results:
        return results

    def _dq_open(s: str) -> bool:
        t = _norm_unicode_quotes(s or "")
        # strip apostrophes
        t = t.replace("’", "").replace("'", "")
        # count curly pairs
        opens = t.count("“")
        closes = t.count("”")
        if opens > closes:
            return True
        # fall back to straight quotes parity
        dq = t.count('"')
        if dq % 2 == 1:
            return True
        # final heuristic: last seen dbl-quote glyph is an opener
        for ch in reversed(t):
            if ch in ("“", "”", '"'):
                return ch == "“"
        return False

    def _starts_with_opener(s: str) -> bool:
        t = _norm_unicode_quotes(s or "").lstrip()
        return t.startswith("“") or t.startswith('"') or t.startswith("«")

    def _looks_like_attrib_line(s: str) -> bool:
        s = (s or "").strip()
        try:
            if "_ATTRIB_LINE_RX" in globals() and _ATTRIB_LINE_RX.match(s):
                return True
        except Exception:
            pass
        # light fallback
        return bool(
            re.search(
                r"\b(said|asked|replied|demanded|continued|went on|added)\b", s, re.I
            )
        )

    out = []
    i = 0
    try:
        DBG["stitch_runs"] = DBG.get("stitch_runs", 0) + 1
    except Exception:
        pass

    while i < len(results):
        cur = dict(results[i])
        if i + 1 < len(results):
            nxt = results[i + 1]
        else:
            nxt = None

        if (
            nxt is not None
            and cur.get("is_quote") is True
            and (nxt.get("is_quote") is False)
            and _dq_open(cur.get("text") or "")
            and not _starts_with_opener(nxt.get("text") or "")
            and not _looks_like_attrib_line(nxt.get("text") or "")
        ):
            # glue
            t1 = cur.get("text") or ""
            t2 = nxt.get("text") or ""
            glue = (
                " "
                if (
                    t1
                    and not t1.endswith((" ", "—", "–", "-", ","))
                    and t2
                    and not t2.startswith((" ", ","))
                )
                else ""
            )
            cur["text"] = _norm_unicode_quotes(t1 + glue + t2)
            # keep quote flag; don't inherit speaker from narration
            try:
                DBG["stitch_rows_glued"] = DBG.get("stitch_rows_glued", 0) + 1
                DBG["stitch_chars_joined"] = DBG.get("stitch_chars_joined", 0) + len(t2)
            except Exception:
                pass
            i += 2
            out.append(cur)
            continue

        out.append(cur)
        i += 1

    return out


def _split_midquote_attrib_clauses_early(rows, *_args):
    """
    If a single quote row contains:  …" {attrib tail} "…   OR   …" {attrib tail}
      where {attrib tail} looks like:
        [,—–-]?  (Name verb …)   or   (verb Name …)   or   (pronoun verb …)
      e.g., '," said Zack.' / ' explained Smith.' / ' he went on.'
    Split into [quote][narration tail][quote?] without creating a quote row for the tail.
    """
    import re

    if not rows:
        return rows

    # full quoted spans (straight or curly)
    RX_SPAN = re.compile(r'([“"][^“”"]*[”"])')

    # Proper-name (up to First Last Last)
    proper = r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}"
    pron = r"(?:he|she|they)"

    # Build a robust verb set
    base_verbs = {
        "said",
        "say",
        "says",
        "ask",
        "asks",
        "asked",
        "reply",
        "replies",
        "replied",
        "answer",
        "answers",
        "answered",
        "remarked",
        "observed",
        "noted",
        "explained",
        "declared",
        "announced",
        "stated",
        "whispered",
        "murmured",
        "muttered",
        "hissed",
        "sobbed",
        "cried",
        "called",
        "yelled",
        "shouted",
        "laughed",
        "snapped",
        "retorted",
        "interjected",
        "interrupted",
        "insisted",
        "agreed",
        "warned",
        "offered",
        "begged",
        "demanded",
        "protested",
        "continued",
        "added",
        "queried",
        "rejoined",
        "pleaded",
        "blurted",
        "persisted",
        "reminded",
        "confirmed",
        "responded",
        "admitted",
        "conceded",
        "objected",
        "countered",
        "exclaimed",
        "went on",
    }
    # Allow project-level verb lists to augment
    try:
        base_verbs |= set(globals().get("_ATTRIB_VERBS", []))
    except Exception:
        pass
    try:
        base_verbs |= set(globals().get("_ATTRIB_VERBS_LOOSE", []))
    except Exception:
        pass

    # sort longest-first to keep multiword verbs like "went on" intact
    vpat = r"(?:%s)" % "|".join(
        sorted(map(re.escape, base_verbs), key=len, reverse=True)
    )

    # Tail starts with optional punctuation, then one of:
    #   Name-first:  Smith said ...
    #   Verb-first:  said Smith ...
    #   Pronoun-first: he went on / she continued / they asked ...
    # NEW: allow a glued closer/punct after the Name/verb chunk:  … queried Smith." …
    RX_TAIL = re.compile(
        rf"^\s*(?:,|—|–|-)?\s*(?:"
        rf"(?:(?P<n1>{proper})\s+{vpat})|"  # Name-first
        rf"(?:{vpat}\s+(?P<n2>{proper}))|"  # Verb-first
        rf"(?:(?P<pr>{pron})\s+{vpat})"  # Pronoun-first
        rf')\b(?:\s*[.”"])?',  # ← tolerate glued closing quote/punct
        re.I,
    )

    out = []
    for idx, row in enumerate(rows):
        if not row.get("is_quote"):
            out.append(row)
            continue

        raw = row.get("text") or ""
        t = _norm_unicode_quotes(raw)

        # only split when the row's quotes are balanced
        try:
            if not _balanced_quote_count(t):
                out.append(row)
                continue
        except Exception:
            out.append(row)
            continue

        parts = [p for p in RX_SPAN.split(t) if p and p.strip()]

        # SPECIAL CASE: If the text ends with: quote_text" attribution_text
        # e.g., 'Why? " he went on in a monotone.' or 'Help me!" she cried.'
        # Split into [quote][narration]
        # Look for LAST closing quote followed by non-quote text matching attribution patterns
        if len(parts) == 1 and not RX_SPAN.fullmatch(parts[0]):
            # Find the last closing quote character
            last_quote_pos = max(
                t.rfind('"'),
                t.rfind('"'),
                t.rfind('"')
            )
            
            if last_quote_pos > 0 and last_quote_pos < len(t) - 2:
                # Check if text after the quote matches attribution
                after_quote = t[last_quote_pos + 1:].strip()
                m = RX_TAIL.match(after_quote)
                if m:
                    # Split: everything up to and including the quote = quote
                    quote_part = t[:last_quote_pos + 1].strip()
                    
                    # Remove trailing quote from quote_part for clean output
                    if quote_part and quote_part[-1:] in ('"', '"', '"'):
                        quote_part = quote_part[:-1].rstrip()
                    
                    if quote_part:
                        q = dict(row)
                        q["text"] = quote_part
                        q["is_quote"] = True
                        out.append(q)
                        
                        # The attribution = narration
                        narr = dict(row)
                        narr["text"] = after_quote
                        narr["is_quote"] = False
                        narr["speaker"] = "Narrator"
                        narr["_keep_attrib_text"] = True
                        for zz in ("_lock_speaker", "_locked_to", "_lock_reason"):
                            narr.pop(zz, None)
                        out.append(narr)
                        
                        try:
                            record_attrib_op_row(
                                "split_midquote_attrib",
                                "split",
                                row,
                                row.get("speaker"),
                                row.get("speaker"),
                                "early_quote_ending_split",
                            )
                        except Exception:
                            pass
                        continue

        if len(parts) < 2:
            out.append(row)
            continue

        changed = False
        tmp = []
        k = 0
        while k < len(parts):
            part = parts[k]

            if RX_SPAN.fullmatch(part):
                qtxt = part.strip()

                # If the following chunk is a narration tail (attribution), emit [quote][narr]
                if k + 1 < len(parts) and not RX_SPAN.fullmatch(parts[k + 1]):
                    nxt = parts[k + 1]
                    m = RX_TAIL.match(nxt or "")
                    if m:
                        # 1) emit the quote
                        q = dict(row)
                        q["text"] = qtxt
                        q["is_quote"] = True
                        tmp.append(q)

                        # 2) emit the narration tail (NOT a quote)
                        tail = (nxt or "").strip()

                        # If the tail we captured ends with a stray closing quote/punct, trim one
                        if tail and tail[-1:] in ('"', "”"):
                            tail = tail[:-1].rstrip()

                        if tail:
                            narr = dict(row)
                            narr["text"] = tail
                            narr["is_quote"] = False
                            narr["speaker"] = "Narrator"
                            # hint for harvester to lock neighbor speaker
                            narr["_keep_attrib_text"] = True
                            for zz in ("_lock_speaker", "_locked_to", "_lock_reason"):
                                narr.pop(zz, None)
                            tmp.append(narr)

                        changed = True
                        k += 2
                        continue

                # Otherwise just pass the quoted span through
                q = dict(row)
                q["text"] = qtxt
                q["is_quote"] = True
                tmp.append(q)
                k += 1
                continue

            # Non-quote chunk: keep as Narrator (rare when source row had multiple spans)
            narr = dict(row)
            narr["text"] = part.strip()
            narr["is_quote"] = False
            narr["speaker"] = "Narrator"
            for zz in ("_lock_speaker", "_locked_to", "_lock_reason"):
                narr.pop(zz, None)
            tmp.append(narr)
            k += 1

        if changed:
            try:
                record_attrib_op_row(
                    "split_midquote_attrib",
                    "split",
                    row,
                    row.get("speaker"),
                    row.get("speaker"),
                    "early_midquote_split",
                    idx,
                )
            except Exception:
                pass
            out.extend(tmp)
        else:
            out.append(row)

    return out


def _glue_buffer(buf: list[dict], max_chars: int) -> dict:
    """Helper: glue buffered rows into a single quote row; keep earliest metadata; merge side meta."""
    head = dict(buf[0])
    glued_text_parts = []
    acc_len = 0
    for j, rr in enumerate(buf):
        frag = (rr.get("text") or "").strip()
        if not frag:
            continue
        # join with single spaces; preserve inline punctuation
        if glued_text_parts:
            glued_text_parts.append(" ")
        glued_text_parts.append(frag)
        acc_len += len(frag)
        try:
            DBG["stitch_rows_glued"] += 1 if j > 0 else 0
            DBG["stitch_chars_joined"] += len(frag) if j > 0 else 0
        except Exception:
            pass
        # merge stronger meta into head
        head = _merge_meta_keep_best(head, rr)

    head["text"] = re.sub(r"\s+\n\s+|\s{2,}", " ", "".join(glued_text_parts)).strip()
    head["is_quote"] = True  # force: everything we glued is inside a quote
    # do NOT invent a speaker here; attribution fills it later
    return head


def _final_quote_sanity_pass(rows):
    """
    Demote rows that are flagged as quotes but contain no quote glyphs and do not
    look like dash-led dialogue. Never touches locked rows.
    """
    if not rows:
        return rows
    out = []
    for r in rows:
        rr = dict(r)
        if rr.get("is_quote") and not rr.get("_lock_speaker"):
            txt = rr.get("text") or ""
            has_quote = bool(re.search(r'["“”«»]', txt))
            dash_dialogue = bool(re.match(r"^\s*[—–-]\s*[A-Z]", txt))
            if not has_quote and not dash_dialogue:
                # Demote to narration; keep text verbatim
                rr["is_quote"] = False
                # Only reset speaker if it was a real person (avoid erasing real Narrator)
                if rr.get("speaker") not in (None, "", "Narrator", "Unknown"):
                    prev = rr.get("speaker") or ""
                    rr["speaker"] = "Narrator"
                    try:
                        record_attrib_op_row(
                            "final_sanity",
                            "demote_false_quote",
                            rr,
                            prev,
                            "Narrator",
                            "no-glyphs-non-dash",
                            None,
                        )
                    except Exception:
                        pass
        out.append(rr)
    return out


# --- Final peel: if a quote row has a post-quote narrator tail, split it off (late safety) ---
_POST_Q_SENT = re.compile(r'(["”])\s*([.!?])\s+([A-Z])')


def _final_peel_narration_from_quotes(rows: list[dict]) -> list[dict]:
    """
    If a quote row still contains narrator text before the first quote or after the last,
    split those head/tail narrator bits into separate Narrator rows. Never touch the quote span itself.
    """
    # If quotes are atomic, do nothing here.
    if globals().get("QUOTES_ARE_ATOMIC"):
        return rows
    if not rows:
        return rows

    out: list[dict] = []

    for r in rows:
        rr = dict(r)

        # Only operate on quote rows
        if not rr.get("is_quote"):
            out.append(rr)
            continue

        txt = _norm_unicode_quotes(rr.get("text") or "")

        # --- NEW: skip peel when quotes are unbalanced (open monologue line) ---
        try:
            if not _balanced_quote_count(txt):
                out.append(rr)
                continue
        except Exception:
            out.append(rr)
            continue
        # ----------------------------------------------------------------------

        # Always define spans (defensive)
        try:
            spans = _quote_spans(txt)
        except Exception:
            spans = []

        if not spans:
            out.append(rr)
            continue

        a0, b_last = spans[0][0], spans[-1][1]
        head = (txt[:a0]).strip()
        core = (txt[a0:b_last]).strip()
        tail = (txt[b_last:]).strip()

        def _has_quote(s: str) -> bool:
            s = s or ""
            return any(ch in s for ch in ['"', "“", "”", "«", "»", "‘", "’"])

        emitted = False

        # Head narration (no visible quote glyphs)
        if head and not _has_quote(head):
            out.append({"text": head, "speaker": "Narrator", "is_quote": False})
            emitted = True

        # Quote core (kept as quote)
        if core:
            qrow = dict(rr)
            qrow["text"] = core
            qrow["is_quote"] = True
            out.append(qrow)
            emitted = True

        # Tail narration (no visible quote glyphs)
        if tail and not _has_quote(tail):
            narr = tail.lstrip(" \t.,;:—–-")
            if narr:
                out.append({"text": narr, "speaker": "Narrator", "is_quote": False})
                emitted = True

        # If nothing special happened, passthrough
        if not emitted:
            out.append(rr)

    return out


def _merge_broken_quote_fragments(rows: list[dict]) -> list[dict]:
    """
    EARLY cleanup: merge consecutive same-speaker rows that are fragments of a single quote.
    
    Problem: BookNLP sometimes splits a single quote across multiple sentences.
    Example:
        [Liddy] " Why, Zack? [/]
        [Liddy] I just do n't understand it. [/]  <- Missing quotes!
        [Liddy] Why? " [/]
    
    This creates fragments where the middle sentence looks like narration.
    We merge consecutive same-speaker quote-like rows back together.
    
    Only merge if:
    - Both have same speaker (not Narrator)
    - At least one has is_quote=True
    - Combined text doesn't exceed 500 chars
    """
    if not rows:
        return rows
    
    out = []
    i = 0
    merged = 0
    
    while i < len(rows):
        cur = dict(rows[i])
        
        # Try to extend with next same-speaker rows
        run = [cur]
        j = i + 1
        
        speaker = cur.get("speaker", "")
        if speaker and speaker != "Narrator":
            # Collect consecutive same-speaker rows
            while j < len(rows):
                nxt = rows[j]
                if nxt.get("speaker") != speaker:
                    break
                # Stop if we hit a narrator row
                if nxt.get("speaker") == "Narrator":
                    break
                # Check combined length
                total_len = sum(len(r.get("text", "")) for r in run) + len(nxt.get("text", ""))
                if total_len > 500:
                    break
                run.append(dict(nxt))
                j += 1
        
        # If we collected multiple rows, merge them
        if len(run) > 1:
            # Check if at least one has is_quote=True
            has_quote = any(r.get("is_quote") for r in run)
            if has_quote:
                # Merge all texts
                merged_text = " ".join(r.get("text", "").strip() for r in run if r.get("text", "").strip())
                merged_row = {
                    "speaker": speaker,
                    "text": merged_text,
                    "is_quote": True,  # Mark as quote since we're merging quote fragments
                    "_merged_fragments": len(run)
                }
                out.append(merged_row)
                merged += len(run) - 1
                i = j
                continue
        
        # No merge, just append
        out.append(cur)
        i += 1
    
    if merged:
        DBG.setdefault("notes", []).append(f"merged_broken_quotes={merged}")
        log(f"[merge_broken_quotes] Merged {merged} broken quote fragments")
    return out


def _merge_short_narration_tails_into_prev_quote(rows: list[dict]) -> list[dict]:
    """
    DISABLED FOR AUDIOBOOK CREATION: We need to preserve ALL text from the book.
    
    Previously this function deleted attribution narration like "said Charlie" 
    to avoid duplication. But for audiobook creation, we need every word present
    so users can assign voices to all text in the GUI.
    
    Now this function just passes through all rows unchanged.
    """
    # Simply return all rows unchanged - keep all book text
    return rows


def _inherit_speaker_for_sandwiched_unknowns(rows: list[dict]) -> list[dict]:
    """
    Final pass: assign speakers to Unknown quotes in two ways:
    
    1) For quotes sandwiched between same named speaker (continuation dialogue)
    2) For attribution fragments like "said John Smith" - extract the name
    
    Example sandwiched:
        Zack: "First quote."
        Unknown: "Second quote."  <-- Gets Zack
        Zack: "Third quote."
    
    Example attribution fragment:
        Unknown: "said John Smith."  <-- Gets John Smith
    """
    if not rows:
        return rows
    
    import re
    
    # Declare global at the start of the function
    global DBG
    
    # Pattern to extract speaker from attribution fragments
    # Matches: "said NAME", "asked NAME", "NAME said", "NAME told him", etc.
    ATTRIB_WITH_NAME = re.compile(
        r"\b(?:said|asked|told|explained|replied|whispered|snapped|moaned|laughed|reminded|suggested|exclaimed|responded|muttered|sighed)\s+([A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+)?)",
        re.I
    )
    NAME_WITH_VERB = re.compile(
        r"^([A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+)?)\s+(?:said|asked|told|explained|moaned|went\s+on)",
        re.I
    )
    
    out = []
    inherited = 0
    extracted = 0
    
    for i, cur in enumerate(rows):
        rr = dict(cur)
        
        # Check if current is an Unknown quote
        if rr.get("is_quote") and rr.get("speaker") == "Unknown":
            text = rr.get("text", "").strip()
            resolved = False
            
            # STRATEGY 1: Extract speaker from attribution fragment
            if len(text) < 150:  # Only check short texts (likely attribution)
                # Try verb-first pattern: "said John Smith"
                match = ATTRIB_WITH_NAME.search(text)
                if match:
                    name = match.group(1).strip()
                    if name and name not in ["him", "her", "them", "it"]:
                        rr["speaker"] = name
                        rr["_extracted_from_attrib"] = True
                        extracted += 1
                        resolved = True
                        DBG["extracted_from_attrib"] = DBG.get("extracted_from_attrib", 0) + 1
                
                # Try name-first pattern: "Smith told them"
                if not resolved:
                    match = NAME_WITH_VERB.match(text)
                    if match:
                        name = match.group(1).strip()
                        if name and name not in ["him", "her", "them", "it"]:
                            rr["speaker"] = name
                            rr["_extracted_from_attrib"] = True
                            extracted += 1
                            resolved = True
                            DBG["extracted_from_attrib"] = DBG.get("extracted_from_attrib", 0) + 1
            
            # STRATEGY 2: Sandwiched between same speaker
            if not resolved:
                prev_speaker = None
                next_speaker = None
                
                # Look back for previous quote (skip narration)
                for j in range(i-1, max(-1, i-5), -1):
                    if rows[j].get("is_quote"):
                        prev_speaker = rows[j].get("speaker")
                        break
                
                # Look ahead for next quote (skip narration)
                for j in range(i+1, min(len(rows), i+5)):
                    if rows[j].get("is_quote"):
                        next_speaker = rows[j].get("speaker")
                        break
                
                # If sandwiched between same named speaker, inherit it
                if (prev_speaker and next_speaker and 
                    prev_speaker == next_speaker and 
                    prev_speaker not in ["Unknown", "Narrator", ""]):
                    rr["speaker"] = prev_speaker
                    rr["_inherited_sandwich"] = True
                    inherited += 1
                    resolved = True
                    DBG["inherited_sandwich_speakers"] = DBG.get("inherited_sandwich_speakers", 0) + 1
        
        out.append(rr)
    
    if inherited or extracted:
        # Defensive: ensure DBG is a dict before trying to append
        if not isinstance(DBG, dict):
            DBG = {}
        DBG.setdefault("notes", []).append(f"inherited_sandwich={inherited}, extracted_attrib={extracted}")
    
    return out


def _peel_seam_tails_from_quote_rows(rows, *_args):
    """
    Late cleanup: split any quote row that still ends with ” followed immediately
    by lowercase/dash+lowercase. If the peeled tail looks like an attribution/action
    fragment (e.g., '— he said', '— Judy replied softly'), emit it as Narrator
    (tagged so the harvester can lock the neighbor), not as a quote. This avoids
    later re-merge of quote+tail.
    """
    import re

    if not rows:
        return rows

    # Detect a closing quote followed (optionally) by dash/en dash/em dash and a lowercase starter.
    SEAM_LOW = re.compile(r'([”"])\s*(?:[—–-]\s*)?([a-z])', re.U)
    # NEW: capital-starter seam (e.g., …”He …) — fire only when right side does NOT look like a new quote opening
    SEAM_CAP = re.compile(r'([”"])\s*([A-Z])', re.U)

    def _tail_has_quote_glyph(s: str) -> bool:
        s = s or ""
        for ch in ('"', "“", "”", "«", "»", "‘", "’"):
            if ch in s:
                return True
        return False

    def _looks_like_opening_quote_start(s: str) -> bool:
        s = (s or "").lstrip()
        return bool(s and s[0] in ('"', "“", "«", "‘"))

    out = []
    for i, r in enumerate(rows):
        if not r.get("is_quote"):
            out.append(r)
            continue

        t = r.get("text") or ""

        # never peel from rows with unbalanced quotes
        try:
            if not _balanced_quote_count(_norm_unicode_quotes(t)):
                out.append(r)
                continue
        except Exception:
            out.append(r)
            continue

        # Try lowercase seam first; if none, try capital seam with a guard
        m = SEAM_LOW.search(t)
        if not m:
            m2 = SEAM_CAP.search(t)
            if m2:
                # Right chunk begins at the CAP; only accept when it's not a fresh quoted segment
                right_probe = t[m2.start(2) :]
                if not _looks_like_opening_quote_start(right_probe):
                    m = m2

        if not m:
            out.append(r)
            continue

        # Split: left = ...closing-quote ; right = tail beginning at (-)? letter
        cut = m.start(1) + 1  # position just after the detected closing quote glyph
        left, right = t[:cut], t[cut:]

        # Left side: keep as quote with same speaker
        q = dict(r)
        q["text"] = left.strip()
        out.append(q)

        tail = (right or "").strip()
        if not tail:
            try:
                record_attrib_op_row(
                    "seam_peel_late",
                    "split_empty_tail",
                    q,
                    r.get("speaker"),
                    q.get("speaker"),
                    "late_seam",
                    i,
                )
            except Exception:
                pass
            continue

        # Only treat as attribution if the tail itself has no new quote glyphs
        if not _tail_has_quote_glyph(tail):
            try:
                looks_attrib = _looks_like_attribution_fragment(tail)
            except Exception:
                looks_attrib = False

            # Emit tail as Narration (never as Quote)
            narr = dict(r)
            narr["is_quote"] = False
            narr["speaker"] = "Narrator"
            narr["text"] = tail
            if looks_attrib:
                narr["_keep_attrib_text"] = True
                narr["_midquote_tail_attrib"] = True
            else:
                narr["_midquote_tail"] = True
            narr.pop("_lock_speaker", None)
            narr.pop("_locked_to", None)
            narr.pop("_lock_reason", None)
            out.append(narr)
            try:
                record_attrib_op_row(
                    "seam_peel_late",
                    "emit_tail_narr" if looks_attrib else "split",
                    q,
                    r.get("speaker"),
                    "Narrator",
                    "attrib_tail" if looks_attrib else "late_seam",
                    i,
                )
            except Exception:
                pass
            continue

        # Conservative fallback: if the tail includes any quote glyph, don’t alter the row at all
        out[-1] = dict(r)  # restore original row if we changed it
        out[-1]["text"] = t

    return out


def _promote_inbetween_attrib_triplets(rows, *_args):
    """
    Promote a short non-quote row BETWEEN two quotes when it looks like a pure beat.

    Rules:
      • If both neighbors are quotes and share the same concrete speaker → inherit it.
      • Else if one neighbor is a quote with a concrete speaker and the other quote is Unknown/empty → inherit the concrete one.
      • Middle row may already have a speaker; we still convert to quote and overwrite (no lock).
    """
    if not rows:
        return rows

    out = list(rows)
    n = len(out)

    def _is_lock(r):
        return bool(r.get("_lock_speaker"))

    for i in range(1, n - 1):
        cur = out[i]
        if cur.get("is_quote"):
            continue
        txt = (cur.get("text") or "").strip()
        if not txt:
            continue
        prev = out[i - 1]
        nxt = out[i + 1]
        if not (prev.get("is_quote") and nxt.get("is_quote")):
            continue
        if _is_lock(cur):
            continue

        if not _is_attrib_fragment_local(txt, max_words=24):
            continue

        prev_sp = (prev.get("speaker") or "").strip()
        nxt_sp = (nxt.get("speaker") or "").strip()

        # refuse only when both neighbors are locked to conflicting concrete speakers
        if (
            _is_lock(prev)
            and _is_lock(nxt)
            and prev_sp
            and nxt_sp
            and prev_sp != nxt_sp
        ):
            continue

        inherit_sp = None
        if prev_sp and nxt_sp and prev_sp == nxt_sp:
            inherit_sp = prev_sp
        elif prev_sp and not nxt_sp:
            inherit_sp = prev_sp
        elif nxt_sp and not prev_sp:
            inherit_sp = nxt_sp
        else:
            # both unknown/empty or conflicting non-locked — stay conservative
            continue

        new_cur = dict(cur)
        new_cur["is_quote"] = True
        new_cur["speaker"] = inherit_sp
        new_cur["_attrib_triplet_promoted"] = True
        new_cur["_promoted_quote"] = True
        out[i] = new_cur
        # --- surname override for mid-beat "… King …" between quotes ---
        try:
            _ensure_surname_map(out)
            sname = _extract_surname_candidate(txt)
            if sname:
                resolved = _resolve_surname_by_context(sname, out, i, window=12)
                if resolved and resolved != new_cur["speaker"]:
                    new_cur["speaker"] = resolved
                    new_cur["_surname_resolved"] = sname
        except Exception:
            pass

        try:
            record_attrib_op_row(
                "attrib_triplet",
                "promote",
                new_cur,
                cur.get("speaker"),
                inherit_sp,
                "triplet",
                i,
            )
        except Exception:
            pass

    return out


def _promote_pre_quote_attrib(rows, *_args):
    """
    If a non-quote beat immediately PRECEDES a quote and looks attribution-like,
    promote it to is_quote=True and inherit the NEXT quote's speaker.
    """
    if not rows:
        return rows
    out = list(rows)
    for i in range(1, len(out)):
        prev = out[i - 1]
        cur = out[i]
        if not cur.get("is_quote"):
            continue
        # candidate beat is the row immediately BEFORE a quote
        beat = prev
        if beat.get("is_quote"):
            continue
        txt = (beat.get("text") or "").strip()
        if not txt:
            continue
        if not _is_attrib_fragment_local(txt, max_words=24):
            continue
        sp = (cur.get("speaker") or "").strip()
        if not sp:
            continue
        newb = dict(beat)
        newb["is_quote"] = True
        newb["speaker"] = sp
        newb["_pre_quote_promoted"] = True
        newb["_promoted_quote"] = True
        out[i - 1] = newb
        # --- surname override for beats like "… said King." before a quote ---
        try:
            _ensure_surname_map(out)
            sname = _extract_surname_candidate(txt)
            if sname:
                resolved = _resolve_surname_by_context(
                    sname, out, i, window=12
                )  # context: the quote idx
                if resolved and resolved != newb["speaker"]:
                    newb["speaker"] = resolved
                    newb["_surname_resolved"] = sname
        except Exception:
            pass

        try:
            record_attrib_op_row(
                "pre_quote_attrib",
                "promote",
                newb,
                beat.get("speaker"),
                sp,
                "pre",
                i - 1,
            )
        except Exception:
            pass
    return out


def _debug_assert_noquote_text_marked_quote(rows):
    for i, r in enumerate(rows):
        t = r.get("text") or ""
        if r.get("is_quote") and not _has_any_quote_char(t):
            log(
                f"[debug-noquote-marked-quote] idx={i} speaker={r.get('speaker')} >>> {t[:90]}..."
            )
    return rows


def _reassert_quote_flags_strict(results):
    """
    Strictly recompute is_quote from glyph spans, BUT preserve only very specific
    promotions that are intended to be “dialogue with no visible glyphs”.
    Never preserve the generic _promoted_quote flag, and NEVER leave Narrator as quote.
    """
    if not results:
        return results

    def _has_quote_span(txt: str) -> bool:
        try:
            return bool(_quote_spans(_norm_unicode_quotes(txt or "")))
        except Exception:
            return False

    # Only these promotions deserve preservation as dialogue-without-glyphs
    # (they come from deliberate pre/post/triplet promotions):
    PRESERVE_KEYS = (
        "_post_quote_promoted",
        "_pre_quote_promoted",
        "_attrib_triplet_promoted",
        "_midquote_tail_promoted",  # keep only if you truly want tails as dialogue
    )

    out = []
    for r in results:
        rr = dict(r)
        txt = rr.get("text") or ""

        has_spans = _has_quote_span(txt)
        preserve = any(rr.get(k) for k in PRESERVE_KEYS)

        if has_spans:
            rr["is_quote"] = True
            # quotes can’t be Narrator unless explicitly locked on purpose
            if rr.get("speaker") == "Narrator" and not rr.get("_lock_speaker"):
                rr["speaker"] = "Unknown"
        elif preserve:
            # preserved promotions ≠ Narrator
            rr["is_quote"] = True
            if rr.get("speaker") == "Narrator" and not rr.get("_lock_speaker"):
                rr["speaker"] = "Unknown"
        else:
            # no glyphs and no special promotion → narration
            rr["is_quote"] = False
            if rr.get("speaker") not in (
                None,
                "",
                "Unknown",
                "Narrator",
            ) and not rr.get("_lock_speaker"):
                rr["speaker"] = "Narrator"

        out.append(rr)
    return out


def _looks_like_direct_speech_strict(text: str) -> bool:
    """
    Very strict: return True only if there is an actual quoted span,
    or a Name: style head (e.g. 'Zack:'), not attribution fragments.
    """
    t = _norm_unicode_quotes(text or "").strip()
    try:
        if _quote_spans(t):
            return True
    except Exception:
        pass

    # 'Name:' style turns are allowed to count as speech
    import re

    name_colon = re.compile(
        r"^\s*[A-Z][A-Za-z\'’\-]+(?:\s+[A-Z][A-Za-z\'’\-]+){0,2}\s*:\s*\S"
    )
    if name_colon.match(t):
        return True

    return False


def _is_quote_row_strict(row: dict) -> bool:
    return _looks_like_direct_speech_strict((row or {}).get("text") or "")


def _hard_separate_quotes_and_narration_strict(results, *_args):
    """
    Final safety net: any row that does NOT have a quoted span and is not a
    Name:-turn is Narrator (is_quote=False). Do not override explicit locks.
    """
    if not results:
        return results

    out = []
    for r in results:
        rr = dict(r)
        txt = rr.get("text") or ""
        is_q = _looks_like_direct_speech_strict(txt)

        if is_q:
            rr["is_quote"] = True
            if rr.get("speaker") == "Narrator" and not rr.get("_lock_speaker"):
                rr["speaker"] = "Unknown"
        else:
            rr["is_quote"] = False
            if rr.get("speaker") not in (
                None,
                "",
                "Unknown",
                "Narrator",
            ) and not rr.get("_lock_speaker"):
                rr["speaker"] = "Narrator"

        out.append(rr)
    return out


def _strip_stray_edge_quotes(rows):
    """
    For narration rows with NO balanced quote spans but with leading/trailing
    quote glyphs, strip those edge glyphs. Never touches real quoted spans.
    """
    if not rows:
        return rows

    out, n_stripped = [], 0
    for r in rows:
        rr = dict(r)
        txt = rr.get("text") or ""
        tcur = _norm_unicode_quotes(txt, keep_curly=True)

        # Only consider narration rows
        if not rr.get("is_quote"):
            spans = _quote_spans(tcur)
            if not spans and any(ch in tcur for ch in ('"', "“", "”", "«", "»")):
                # Strip leading/trailing single quote glyphs
                t2 = re.sub(r'^\s*[“"«]\s*', "", tcur)
                t2 = re.sub(r'\s*[”"»]\s*$', "", t2)
                if t2 != tcur:
                    rr["text"] = t2
                    n_stripped += 1
        out.append(rr)

    try:
        DBG["stray_edge_quotes_stripped"] = (
            DBG.get("stray_edge_quotes_stripped", 0) + n_stripped
        )
    except Exception:
        pass

    return out


def _apply_dialogue_pair_hints(rows, alias_inv=None):
    """
    Use _analyze_dialogue_pair(prev_txt, cur_txt) to resolve very likely
    two-party turns when the current quote is Unknown.

    - If prev is KNOWN and cur is Unknown:
        * If pair looks like different speakers (Q→A, affirmation, long→short, etc.),
          assign cur to the nearest OTHER known speaker.
        * Else (looks like same-speaker continuation) and cur is very short,
          carry prev speaker into cur.

    Never overwrites locked speakers. Skips if the chosen speaker's name appears in the line.
    """
    if not rows:
        return rows

    out = [dict(r) for r in rows]
    n = len(out)

    def wc(s):
        return len(re.findall(r"[A-Za-z0-9']+", s or ""))

    for i in range(1, n):
        prev, cur = out[i - 1], out[i]

        # both must be quotes
        if not (
            looks_like_direct_speech(prev.get("text", ""))
            and looks_like_direct_speech(cur.get("text", ""))
        ):
            continue

        # current must be Unknown and not locked; previous must be known
        if cur.get("_lock_speaker"):
            continue
        if (cur.get("speaker") or "Unknown") != "Unknown":
            continue
        prev_sp = prev.get("speaker") or "Unknown"
        if prev_sp in ("Unknown", "Narrator", None, ""):
            continue

        pt = (prev.get("text") or "").strip()
        ct = (cur.get("text") or "").strip()

        different = _analyze_dialogue_pair(pt, ct)

        if different:
            # assign to the nearest OTHER known speaker
            other = _nearest_other_speaker(out, i, avoid=prev_sp, window=ADDRESS_WINDOW)
            if other and not _contains_name(ct, other):
                cur["speaker"] = other
                cur["_lock_reason"] = "pair-hint-other"
                log(f"[pair-hint] prev='{prev_sp}' -> cur='{other}' | {ct[:60]}…")
                out[i] = cur
        else:
            # looks like continuation; only carry if the current line is very short (safe)
            if wc(ct) <= 4 and not _contains_name(ct, prev_sp):
                cur["speaker"] = prev_sp
                cur["_lock_reason"] = "pair-hint-carry"
                log(f"[pair-hint] carry '{prev_sp}' | {ct[:60]}…")
                out[i] = cur

    return out


def _apply_conversational_reasoning(rows):
    """
    Unified conversational attribution (conservative):
      - Bracketed Unknown (A, Unknown, B):
          * if A != B → assign Unknown to B (next anchor)
          * if A == B → assign Unknown to A (continuation)
      - Cluster alternation (>=2) when bracketed by DISTINCT known speakers
      - Double-Unknown ping-pong: if exactly 2 consecutive Unknown quotes,
        assume different speakers and alternate them.
      - Always skip if would-be speaker's name appears in the quote text.
      - Never overwrite locks or non-Unknown speakers.
    """
    if not rows:
        return rows

    out = rows
    n = len(out)

    # --- Pass 1: bracketed single Unknowns
    for i, r in enumerate(out):
        if not r.get("is_quote"):
            continue
        if (r.get("speaker") or "Unknown") != "Unknown":
            continue
        if r.get("_lock_speaker"):
            continue

        prev_spk = prev_txt = None
        for j in range(i - 1, -1, -1):
            if out[j].get("is_quote"):
                prev_txt = out[j].get("text", "")
                ps = out[j].get("speaker")
                if ps not in (None, "", "Unknown", "Narrator"):
                    prev_spk = ps
                break

        next_spk = next_txt = None
        for j in range(i + 1, n):
            if out[j].get("is_quote"):
                next_txt = out[j].get("text", "")
                ns = out[j].get("speaker")
                if ns not in (None, "", "Unknown", "Narrator"):
                    next_spk = ns
                break

        txt = r.get("text") or ""

        if prev_spk and next_spk:
            if prev_spk != next_spk:
                if not _contains_name(txt, next_spk):
                    r["speaker"] = next_spk
                    r["_lock_reason"] = "bracket-next"
                    log(f"[conv-reason] bracket-next '{next_spk}' | {txt[:60]}…")
            else:
                if not _contains_name(txt, prev_spk):
                    r["speaker"] = prev_spk
                    r["_lock_reason"] = "bracket-same"
                    log(f"[conv-reason] bracket-same '{prev_spk}' | {txt[:60]}…")

    # --- Pass 2: cluster alternation (>=2) with distinct anchors
    i = 0
    while i < n:
        if (
            out[i].get("is_quote")
            and (out[i].get("speaker") in (None, "", "Unknown"))
            and not out[i].get("_lock_speaker")
        ):
            start = i
            while (
                i < n
                and out[i].get("is_quote")
                and (out[i].get("speaker") in (None, "", "Unknown"))
                and not out[i].get("_lock_speaker")
            ):
                i += 1
            end = i
            cluster_len = end - start
            if cluster_len >= 2:
                left_spk = right_spk = None
                if start > 0 and out[start - 1].get("is_quote"):
                    ls = out[start - 1].get("speaker")
                    if ls not in (None, "", "Unknown", "Narrator"):
                        left_spk = ls
                if end < n and out[end].get("is_quote"):
                    rs = out[end].get("speaker")
                    if rs not in (None, "", "Unknown", "Narrator"):
                        right_spk = rs

                if left_spk and right_spk and left_spk != right_spk:
                    has_q = any(
                        "?" in (out[k].get("text") or "") for k in range(start, end)
                    )
                    has_stmt = any(
                        not ((out[k].get("text") or "").strip().endswith("?"))
                        for k in range(start, end)
                    )
                    if has_q or has_stmt:
                        pair = [right_spk, left_spk]
                        for k in range(cluster_len):
                            choice = pair[k % 2]
                            if _contains_name(out[start + k].get("text", ""), choice):
                                continue
                            out[start + k]["speaker"] = choice
                            out[start + k]["_lock_reason"] = "cluster-alt"
                            frag = (out[start + k].get("text", "")[:60]).replace(
                                "\n", " "
                            )
                            log(f"[conv-reason] cluster-alt '{choice}' | {frag}…")
        else:
            i += 1

    # --- Pass 3: special handling for EXACTLY two Unknowns in a row
    for i in range(n - 1):
        r1, r2 = out[i], out[i + 1]
        if (
            r1.get("is_quote")
            and r2.get("is_quote")
            and (r1.get("speaker") in (None, "", "Unknown"))
            and (r2.get("speaker") in (None, "", "Unknown"))
            and not r1.get("_lock_speaker")
            and not r2.get("_lock_speaker")
        ):
            # Assign different pseudo-speakers
            r1["speaker"] = "UnknownA"
            r1["_lock_reason"] = "pair-alt"
            r2["speaker"] = "UnknownB"
            r2["_lock_reason"] = "pair-alt"
            log(
                f"[conv-reason] pair-alt UnknownA|UnknownB | {r1.get('text','')[:40]} / {r2.get('text','')[:40]}"
            )

    return out


def attach_inline_attrib_to_adjacent_unknown(results, *args, **kwargs):
    """
    Harvest nearby narration (±window) for attribution fragments to resolve Unknown quotes.
      • Verb-first:  ', said Smith.' / '— asked Judy King.'   (but NOT 'said to Zack')
      • Name-first:  'Smith said.' / 'Judy King asked softly.'
      • Name-colon:  'Smith:' (applies to the right quote)
    Keeps narration lines as Narrator; only sets/locks the target quote's speaker.

    Supports BOTH call styles:
      (results, alias_inv, window=2)
      (results, output_dir, prefix, alias_inv, window=2)
    """
    import re

    # ---- signature shim -------------------------------------------------------
    alias_inv = None
    window = 2
    # kwargs override if provided
    if "alias_inv" in kwargs:
        alias_inv = kwargs["alias_inv"]
    if "window" in kwargs:
        window = kwargs["window"]

    # positional interpretation
    if alias_inv is None:
        if len(args) >= 3:
            # (output_dir, prefix, alias_inv [, window])
            alias_inv = args[2]
            if len(args) >= 4 and isinstance(args[3], int):
                window = args[3]
        elif len(args) >= 1:
            # (alias_inv [, window])
            alias_inv = args[0]
            if len(args) >= 2 and isinstance(args[1], int):
                window = args[1]
    # --------------------------------------------------------------------------

    if not results:
        return results

    try:
        _ensure_attrib_fragment_regexes()
    except Exception:
        pass

    MAX_LEN, MAX_WORDS = 90, 15
    proper = r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}"
    _RX_NAME_COLON = globals().get("_NAME_COLON_RX") or re.compile(
        rf"^\s*(?P<name>{proper})\s*:\s*$"
    )

    _verbs_fallback = {
        "said",
        "says",
        "say",
        "ask",
        "asks",
        "asked",
        "reply",
        "replies",
        "replied",
        "answer",
        "answers",
        "answered",
        "tell",
        "tells",
        "told",
        "called",
        "yelled",
        "shouted",
        "cried",
        "whispered",
        "murmured",
        "muttered",
        "snapped",
        "retorted",
        "laughed",
        "sobbed",
        "hissed",
        "noted",
        "observed",
        "remarked",
        "insisted",
        "countered",
        "agreed",
        "warned",
        "offered",
        "begged",
        "demanded",
        "protested",
        "announced",
        "explained",
        "declared",
        "argued",
        "suggested",
        "continued",
        "interjected",
        "interrupted",
        "conceded",
        "promised",
        "pleaded",
        "rejoined",
        "stated",
        "blurted",
        "went on",
    }
    verbs = (
        set(globals().get("_ATTRIB_VERBS_LOOSE", []))
        or set(globals().get("_ATTRIB_VERBS", []))
        or _verbs_fallback
    )
    vpat = r"\b(?:%s)\b" % "|".join(
        sorted(map(re.escape, verbs), key=len, reverse=True)
    )

    # permissive filler: up to 3 small words (pronouns/preps/adverbs), and an optional 'in a/the …' adjunct
    FILLER = (
        r"(?:\s+(?:\w+|to|at|with|of|about|for|on|in|into|onto|toward|towards)){0,3}"
        r"(?:\s+in\s+(?:a|an|the)\s+[a-z]{2,20}(?:\s+[a-z]{2,20}){0,2})?"
    )

    RX_VFIRST = re.compile(
        rf"(?:^|[,;:—–-]\s*){vpat}(?!\s+(?:to|at|with|toward|towards|into|onto|upon|of|about)\b){FILLER}\s+(?P<who>{proper})(?=[\s,.;:!?—–-]*$)",
        re.I,
    )
    RX_NFIRST = re.compile(
        rf"(?P<who>{proper})\s+{vpat}{FILLER}(?=[\s,.;:!?—–-]*$)", re.I
    )

    out = list(results)
    n = len(out)

    def narr_text(i):
        return _norm_unicode_quotes(out[i].get("text") or "")

    def is_quote(i):
        return 0 <= i < n and looks_like_direct_speech(out[i].get("text") or "")

    def has_inline_quote_glyphs(s: str) -> bool:
        return any(ch in s for ch in ['"', "“", "”", "«", "»"])

    def dbg_inc_safe(key):
        try:
            DBG[key] = DBG.get(key, 0) + 1
        except Exception:
            pass

    def record_op_safe(kind, action, row, old, new, reason, idx):
        try:
            record_attrib_op_row(kind, action, row, old, new, reason, idx)
        except Exception:
            pass

    _CAP_STOP = {
        "Apartment",
        "County",
        "Justice",
        "Center",
        "Oregon",
        "Toyota",
        "Seaside",
        "Astoria",
        "Gearhart",
        "Bay",
        "River",
        "Street",
        "Store",
        "Jail",
        "High",
        "University",
    }
    # Sanitizer is used correctly inside use_speaker; removed misplaced call here.

    def use_speaker(idx_quote, raw_name, reason):
        who_raw = _sanitize_person_name(raw_name or "")
        who = _canonicalize_who_ctx(who_raw, alias_inv, out, idx_quote) or ""
        if not who:
            return False

        if " " not in who:
            try:
                resolved = _resolve_surname_by_context(
                    who.lower(), out, idx_quote, window=8
                )
                if resolved:
                    who = resolved
            except Exception:
                pass

        prev = (out[idx_quote].get("speaker") or "").strip()
        locked = bool(out[idx_quote].get("_lock_speaker"))

        if prev in ("", "Unknown", "Narrator") or prev == who:
            ok = apply_speaker(
                out[idx_quote],
                who,
                reason=reason,
                stage="attrib_harvest",
                idx=idx_quote,
            )
            if ok:
                dbg_inc_safe("attrib_harvest_hits")
            return ok

        if not locked and reason and reason.startswith("harvest_"):
            old = prev
            out[idx_quote]["speaker"] = who
            out[idx_quote]["_lock_speaker"] = True
            out[idx_quote]["_locked_to"] = who
            out[idx_quote]["_lock_reason"] = reason
            record_op_safe(
                "attrib_harvest",
                "override",
                out[idx_quote],
                old,
                who,
                reason,
                idx_quote,
            )
            dbg_inc_safe("attrib_harvest_overrides")
            return True

        record_op_safe(
            "attrib_harvest",
            "skip_conflict_locked",
            out[idx_quote],
            prev,
            who,
            reason,
            idx_quote,
        )
        dbg_inc_safe("attrib_harvest_skips")
        return False

    for i in range(n):
        if not is_quote(i):
            continue
        if (out[i].get("speaker") or "Unknown") != "Unknown":
            continue

        best = None
        for d in range(1, window + 1):
            for j in (i - d, i + d):
                if j < 0 or j >= n or is_quote(j):
                    continue

                txt = narr_text(j).strip()
                if not txt or has_inline_quote_glyphs(txt):
                    continue
                if len(txt) > MAX_LEN or len(txt.split()) > MAX_WORDS:
                    continue

                who, tag = None, None

                try:
                    is_frag = _looks_like_attribution_fragment(txt)
                except Exception:
                    is_frag = False

                if is_frag:
                    if "_speaker_verb_from_attrib_fragment" in globals():
                        try:
                            who2, _verb = _speaker_verb_from_attrib_fragment(
                                txt, alias_inv
                            )
                            if who2:
                                who, tag = who2, "frag"
                        except Exception:
                            pass
                    if not who and "_speaker_from_attrib_fragment" in globals():
                        try:
                            res = _speaker_from_attrib_fragment(txt)
                            who2 = res[0] if isinstance(res, tuple) else res
                            if who2:
                                who, tag = who2, "frag_who"
                        except Exception:
                            pass

                if not who:
                    m = RX_VFIRST.search(txt)
                    if m:
                        who, tag = m.group("who"), "verbfirst"
                    else:
                        m = RX_NFIRST.search(txt)
                        if m:
                            who, tag = m.group("who"), "namefirst"
                        else:
                            mc = _RX_NAME_COLON.match(txt)
                            if mc:
                                who, tag = mc.group("name"), "namecolon"

                if who:
                    cand = (d, j, who, tag)
                    if (best is None) or (d < best[0]):
                        best = cand

        if best:
            _d, j, raw, tag = best
            if tag == "namecolon":
                k = j + 1
                while k < n and not is_quote(k):
                    k += 1
                target = (
                    k
                    if (k < n and (out[k].get("speaker") in ("", None, "Unknown")))
                    else i
                )
                use_speaker(target, raw, f"harvest_{tag}@{j}")
            else:
                use_speaker(i, raw, f"harvest_{tag}@{j}")

    return out


def _speaker_name_sanity(results, alias_inv):
    """
    Collapse junky multi-token speakers (e.g., 'Zack S Cheap Furnished Apartment In Astoria Oregon')
    to a canonical alias when possible. Conservative: only rewrites when it finds a confident alias.
    """
    import re

    out = []
    for idx, r in enumerate(results):
        spk = (r.get("speaker") or "").strip()
        if not spk or spk in {"Unknown", "Narrator"} or not r.get("is_quote"):
            out.append(r)
            continue

        # Heuristic: too long or >2 capitalized tokens → suspect
        caps = re.findall(r"[A-Z][A-Za-z'’\-]+", spk)
        if len(caps) <= 2 and len(spk) <= 30:
            out.append(r)
            continue

        cand = None
        # try first-two tokens
        if len(caps) >= 2:
            try:
                tup = " ".join(caps[:2])
                cand = (
                    _alias_correct(tup, alias_inv)
                    if "_alias_correct" in globals()
                    else tup
                )
            except Exception:
                pass
        # try surname-only
        if not cand and len(caps) >= 1:
            try:
                sur = caps[-1]
                cand = _resolve_surname_by_context(sur.lower(), results, idx, window=8)
            except Exception:
                cand = None
        # try first name
        if not cand and len(caps) >= 1:
            try:
                first = caps[0]
                cand = (
                    _alias_correct(first, alias_inv)
                    if "_alias_correct" in globals()
                    else first
                )
            except Exception:
                pass

        if cand and cand not in {"Unknown", "Narrator"} and len(cand) <= 30:
            old = r.get("speaker")
            r = dict(r)
            r["speaker"] = cand
            r["_lock_speaker"] = True
            r["_locked_to"] = cand
            r["_lock_reason"] = "name_sanity"
            try:
                record_attrib_op_row(
                    "name_sanity", "rewrite", r, old, cand, "collapse_junky_name", idx
                )
            except Exception:
                pass
        out.append(r)
    return out


# --- Extract an inline mid-clause attribution embedded in narration ---
_MID_ATTRIB_RX = re.compile(
    rf"(?:^|[,\-—;:]\s*)"
    rf"(?P<who>{_NAME_RX})\s+(?P<verb>{_VERBS_RX})\b|"
    rf"(?P<verb2>{_VERBS_RX})\s+(?P<who2>{_NAME_RX})",
    re.IGNORECASE,
)


def _extract_mid_clause_attrib(text: str, alias_inv: dict) -> str | None:
    t = text or ""
    m = _MID_ATTRIB_RX.search(t)
    if not m:
        return None
    who_raw = m.group("who") or m.group("who2")
    who = _sanitize_person_name(who_raw) if who_raw else None
    if not who or _is_banned(who):
        return None
    try:
        who = _alias_correct(who, alias_inv or {})
    except Exception:
        pass
    return who


# ---fix rows that accidentally keep a lonely leading quote ---
_LONELY_QUOTE_RX = re.compile(r'^\s*"\s*')


def _fix_lonely_quote_rows(rows: list[dict]) -> list[dict]:
    """
    Sweep away rows that are just `""` (or equivalent after normalization),
    by fusing them into an adjacent speech row. Prevents quote-loss side effects
    where a spoken fragment is left bare and gets demoted to Narrator.

    Order of preference:
      - If previous is speech: drop the lonely row (quotes already balanced there).
      - Else if next is speech: drop the lonely row (quotes will be balanced there).
      - Else keep the row (rare; we'll let the auditor catch it).
    """
    out = []
    n = len(rows)
    i = 0
    while i < n:
        cur = dict(rows[i])
        t = _norm_unicode_quotes(cur.get("text") or "").strip()
        if t in ('""', "“”"):
            prev_is_speech = bool(out) and looks_like_direct_speech(
                out[-1].get("text") or ""
            )
            next_is_speech = (i + 1 < n) and looks_like_direct_speech(
                rows[i + 1].get("text") or ""
            )
            if prev_is_speech or next_is_speech:
                # Drop the lonely quote row entirely
                i += 1
                continue
        out.append(cur)
        i += 1
    return out


def continuity_fill_quotes(
    rows: list[dict], window_back: int = 4, window_fwd: int = 2
) -> list[dict]:
    """
    Fill easy 'Unknown' quotes by borrowing from nearest confident neighbors.
    - Never overwrites locked rows or known speakers.
    - Prefers nearest PREV known quote inside window_back; if none, tries next inside window_fwd.
    - Skips when the candidate speaker's name appears in the quote text.
    """
    if not rows:
        return rows

    def _conf(r: dict) -> float:
        # locks & cid/qscore still dominate
        if r.get("_lock_speaker"):
            return 10.0
        c = 0.0
        if r.get("_cid") is not None:
            c += 3.0
        c += float(r.get("_qscore") or 0.0)

        sp = r.get("speaker") or ""
        if sp and sp not in ("Unknown", "Narrator"):
            c += 0.5
            # gentle nudge based on quote-zone frequency for that canonical (if known)
            try:
                # map canonical back to a cluster if you have reverse map; otherwise use name->stats if you maintain it
                # here we look up by name in CLUSTER_STATS if present
                for cid, st in (CLUSTER_STATS or {}).items():
                    if CJ_MAP.get(cid) == sp:
                        qcnt = int(st.get("quote", 0))
                        # cap the bonus; log1p keeps it tame
                        c += min(1.0, math.log1p(qcnt) * 0.2)
                        break
            except Exception:
                pass
        return c

    out = [dict(r) for r in rows]
    n = len(out)

    for i, r in enumerate(out):
        if not looks_like_direct_speech(r.get("text", "")):
            continue
        if r.get("_lock_speaker"):
            continue
        if (r.get("speaker") or "Unknown") != "Unknown":
            continue

        # find nearest confident previous
        prev_idx = None
        prev_conf = -1.0
        for j in range(i - 1, max(-1, i - window_back) - 1, -1):
            if looks_like_direct_speech(out[j].get("text", "")):
                sp = out[j].get("speaker")
                if sp not in ("Unknown", "Narrator", None, ""):
                    sc = _conf(out[j])
                    prev_idx, prev_conf = j, sc
                    break

        # find nearest confident next
        next_idx = None
        next_conf = -1.0
        for j in range(i + 1, min(n, i + 1 + window_fwd)):
            if looks_like_direct_speech(out[j].get("text", "")):
                sp = out[j].get("speaker")
                if sp not in ("Unknown", "Narrator", None, ""):
                    sc = _conf(out[j])
                    next_idx, next_conf = j, sc
                    break

        cand = None
        if prev_idx is not None and (next_idx is None or prev_conf >= next_conf):
            cand = out[prev_idx].get("speaker")
        elif next_idx is not None:
            cand = out[next_idx].get("speaker")

        if not cand:
            continue

        # don't assign if the candidate name is mentioned in the line
        txt = r.get("text") or ""
        if _contains_name(txt, cand):
            continue

        out[i]["speaker"] = cand
        out[i]["_lock_reason"] = "continuity"
        log(f"[continuity] {i}: -> '{cand}' | {txt[:60]}…")

    return out


# --- Helpers for conservative conversational reasoning -----------------------

_AFFIRMATIONS = {
    "yes",
    "yeah",
    "yep",
    "right",
    "exactly",
    "of course",
    "sure",
    "indeed",
    "okay",
    "ok",
    "alright",
    "fine",
    "true",
}

# --- Canonical name detection in text ----------------------------------------
_NAME_TOKEN_RX = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _canon_names_in_text(text: str, alias_inv: dict | None = None) -> set[str]:
    """
    Return a set of *canonical* character names that appear in `text`, using:
      - alias_inv: token → canonical (e.g., 'king' → 'Steve King')
      - SURNAME_TO_CANON: surname → set of canonicals (e.g., 'king' → {'Steve King','Liddy King'})
    Notes:
      - We normalize the text (lowercase, strip punctuation-like noise)
      - We match by tokens, not substrings.
    """
    if not text:
        return set()

    # Normalize and tokenize
    norm = normalize_name(text)
    tok_low = {t.lower() for t in _NAME_TOKEN_RX.findall(norm)}

    # Ensure alias + surname maps are available
    if alias_inv is None:
        alias_inv = globals().get("ALIAS_INV_CACHE", {}) or {}
    _ensure_surname_map()

    canon_hits: set[str] = set()

    # alias_inv: token -> canonical
    for tok in tok_low:
        if tok in alias_inv:
            canon_hits.add(alias_inv[tok])

    # surname expansion: token is a surname mapped to possibly multiple canonicals
    for tok in tok_low:
        if SURNAME_TO_CANON.get(tok):
            canon_hits |= SURNAME_TO_CANON[tok]

    return canon_hits


# --- Canon-aware "contains name" check (replacement) -------------------------
def _contains_name(text: str, person: str, alias_inv: dict | None = None) -> bool:
    """
    Return True if `text` appears to contain a mention of `person` (canonical),
    using both direct full-name boundary matching and canonicalization via
    alias/surname maps.

    This is intentionally conservative: it's used to *avoid* assigning a line
    to a speaker when that speaker's name appears inside the line.
    """
    if not text or not person:
        return False

    # Normalize inputs
    person_norm = normalize_name(person)
    text_norm = normalize_name(text)

    # 1) Direct full-name boundary match (handles multi-word names)
    #    e.g., "\bSteve King\b"
    full_rx = rf"\b{re.escape(person_norm)}\b"
    if re.search(full_rx, text_norm, flags=re.IGNORECASE):
        return True

    # 2) Canonicalization via tokens in text (alias + surname expansion)
    #    If *any* canonical derived from tokens in text equals `person_norm`, we say it contains it.
    canon_in_text = _canon_names_in_text(text, alias_inv)
    if person_norm in canon_in_text:
        return True

    # 3) Fallback: surname-only presence mapped specifically to this person
    parts = person_norm.split()
    if parts:
        last = parts[-1].lower()
        _ensure_surname_map()
        if last in SURNAME_TO_CANON and person_norm in SURNAME_TO_CANON[last]:
            # avoid substring false positives by using token set
            tok_low = {t.lower() for t in _NAME_TOKEN_RX.findall(text_norm)}
            if last in tok_low:
                return True

    return False


def _call_speaker_from_attrib_fragment(text, alias_inv=None):
    """
    Compatibility shim: some trees define _speaker_from_attrib_fragment(text),
    others define _speaker_from_attrib_fragment(text, alias_inv=None).
    Returns whatever the underlying function returns (tuple or str).
    """
    try:
        return _speaker_from_attrib_fragment(text, alias_inv)  # 2-arg variant
    except TypeError:
        return _speaker_from_attrib_fragment(text)  # 1-arg variant


def _demote_quoted_action_sentences(results):
    """
    Demote rows marked as quotes when the whole content is a third-person
    Name + action sentence, e.g., "King waved his hand …".
    """
    import re

    if not results:
        return results

    ACTION_VERBS = {
        "nodded",
        "smiled",
        "grinned",
        "frowned",
        "sighed",
        "shrugged",
        "gestured",
        "pointed",
        "glanced",
        "stared",
        "gazed",
        "looked",
        "wagged",
        "waved",
        "motioned",
        "beckoned",
        "laughed",
        "chuckled",
        "snorted",
        "grimaced",
        "winced",
        "blinked",
        "peered",
        "stepped",
        "turned",
        "walked",
        "strode",
        "marched",
        "sat",
        "stood",
        "rose",
        "leaned",
        "reached",
        "folded",
        "unfolded",
        "adjusted",
        "removed",
        "took",
        "set",
        "placed",
        "grabbed",
        "held",
        "clutched",
        "patted",
        "tapped",
        "drummed",
        "rubbed",
        "scratched",
        "opened",
        "closed",
        "shut",
        "pulled",
        "pushed",
        "drew",
        "lit",
        "flicked",
        "smoked",
        "continued",
        "went",
        "paused",
        "hesitated",
        "wiped",
        "cleared",
        "coughed",
    }
    _VERB = r"(?:%s)" % "|".join(
        sorted(map(re.escape, ACTION_VERBS), key=len, reverse=True)
    )
    _NAME = r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}"
    RX = re.compile(rf'^\s*[“"]\s*(?:{_NAME})\s+{_VERB}\b[^“”"]*[.!?””"]\s*[”"]\s*$')

    # 🔒 Never touch any row we *promoted* into a quote (glyph-less dialogue beats)
    PRESERVE_KEYS = (
        "_promoted_quote",
        "_post_quote_promoted",
        "_pre_quote_promoted",
        "_attrib_triplet_promoted",
        "_midquote_tail_promoted",
    )

    for idx, row in enumerate(results):
        if not row.get("is_quote"):
            continue
        if any(row.get(k) for k in PRESERVE_KEYS):
            continue  # <-- critical: don’t undo our promotions

        t = _norm_unicode_quotes(row.get("text") or "")
        if RX.match(t):
            old = row.get("speaker")
            row["is_quote"] = False
            row["speaker"] = "Narrator"
            try:
                record_attrib_op_row(
                    "demote_quoted_action",
                    "demote",
                    row,
                    old,
                    "Narrator",
                    "quoted_third_person_action",
                    idx,
                )
            except Exception:
                pass
    return results


def _demote_vocative_address(rows, alias_inv):
    """
    If a quote starts with a known name + comma (vocative), avoid assigning that name
    as the speaker. If the current speaker equals that name, set to Unknown to allow
    other heuristics (.quotes, burst-carry) to pick the real speaker.
    """
    # build a quick lowercase name set from alias_inv values
    names = set(n.lower() for n in (alias_inv or {}).values() if n)

    for r in rows:
        if not r.get("is_quote"):
            continue
        t = (r.get("text") or "").strip()
        m = re.match(r"^\s*([A-Za-z][\w\'\-]+)(?:\s+[A-Za-z][\w\'\-]+){0,2}\s*,", t)
        if not m:
            continue
        voc = normalize_name(m.group(0).strip(" ,")).lower()
        sp = (r.get("speaker") or "").lower()
        # if text starts with a known name and we assigned that same name → demote
        if voc in names and sp == voc:
            r["speaker"] = "Unknown"
            log(f"[vocative] demote '{voc}' as speaker | {t[:60]}…")
    return rows


def _extract_vocative_name(text: str, alias_inv: dict | None) -> str | None:
    """
    Return a canonical name if the quote STARTS with a vocative:
      - [Interj], Name...   e.g., "Hey, Zack—", "Listen, Christina."
      - Name, ...           e.g., "Christina, don't."
      - Name—               e.g., "Zack—"
    Only accepts 1–2 Title-Cased tokens that alias/whitelist-resolve.
    """
    if not text:
        return None
    s = (text or "").strip()

    # Allow a short interjection first
    interj = r"(?:Hey|Listen|Look|Yo|Please)\s*,\s*"
    name = r"([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)?)"

    # Try: Interj + Name,  or  Name followed by comma/dash/punct
    m = re.match(rf"^\s*(?:{interj})?{name}\s*[,—\-:!]", s)
    if not m:
        return None

    raw = normalize_name(m.group(1)).title()
    # require whitelist/alias resolve
    clamped = _whitelist_clamp(raw)
    if clamped:
        return clamped
    if alias_inv:
        low = raw.split()[0].lower()
        if low in alias_inv:
            return alias_inv[low]
    return None


# --- pronoun-pattern helper used by _apply_addressing_echo_rules --------------
_FIRST_PERSON = {"i", "me", "my", "mine", "we", "us", "our", "ours"}
_SECOND_PERSON = {"you", "your", "yours", "yourself", "yourselves"}


def _has_you_after_i(prev_txt: str, cur_txt: str) -> bool:
    """
    Return True when the previous quote uses 1st-person ('I'/'we') and the current
    quote uses 2nd-person ('you'), which is a strong ping-pong signal.
    """
    if not prev_txt or not cur_txt:
        return False
    prev_tokens = {w.lower() for w in re.findall(r"[A-Za-z']+", prev_txt)}
    cur_tokens = {w.lower() for w in re.findall(r"[A-Za-z']+", cur_txt)}
    return bool(prev_tokens & _FIRST_PERSON) and bool(cur_tokens & _SECOND_PERSON)


def _apply_addressing_echo_rules(results, alias_inv):
    """
    For quoted lines:
      - VOCATIVE at the start (“Charlie, …”): prefer assigning the OTHER speaker.
      - Short-echo replies: if content echoes previous, flip to previous speaker.
    Only adjusts speakers when Unknown or clearly mispointing and not locked.
    """
    if not results:
        return results
    out = [dict(r) for r in results]

    for i, r in enumerate(out):
        txt = (r.get("text") or "").strip()
        if not _looks_like_direct_speech_strict(txt):
            continue
        sp = r.get("speaker") or "Narrator"

        # (A) VOCATIVE-only addressing: Name at the very start
        if ADDRESS_HEURISTIC:
            voc = _extract_vocative_name(txt, alias_inv)
            if voc:
                # Use a wider search window only for short quotes (reduces self-assignments)
                dyn_win = 10 if len(txt) <= SHORT_QUOTE_MAX_CHARS else ADDRESS_WINDOW
                if sp == "Unknown" or normalize_name(sp) == normalize_name(voc):
                    other = _nearest_other_speaker(out, i, avoid=voc, window=dyn_win)
                    if other:
                        if not out[i].get("_lock_speaker"):
                            out[i]["speaker"] = other
                        log(
                            f"[addr] vocative='{voc}' → speaker='{other}' | {txt[:60]}…"
                        )
                        continue

        # (B) Echo heuristic (unchanged)
        if (
            len(txt) <= SHORT_QUOTE_MAX_CHARS
            and i > 0
            and looks_like_direct_speech(out[i - 1]["text"])
        ):
            prev_txt = out[i - 1]["text"]
            prev_sp = out[i - 1]["speaker"]
            if prev_sp not in ("Unknown", "Narrator"):
                cur_set = _content_set(txt)
                prev_set = _content_set(prev_txt)
                if (len(cur_set) <= 4) and (
                    _jaccard(cur_set, prev_set) >= 0.5
                    or _has_you_after_i(prev_txt, txt)
                ):
                    if not out[i].get("_lock_speaker"):
                        out[i]["speaker"] = (
                            prev_sp if sp in ("Unknown", prev_sp) else prev_sp
                        )
                    log(f"[echo] reassigned to '{prev_sp}' | {txt[:60]}…")

    return out


def _carry_monologue_across_punct(rows):
    """
    If we see:  QUOTE(A) -> Narrator(punct-only) -> QUOTE(C)
    and A’s quote visually continues, carry A’s speaker into C.
    Never flip a row that’s been attribution-locked.
    Extra guards:
      - Do NOT carry across a turn boundary (…”  “…”).
      - Do NOT carry if C starts with an opener (likely a new turn).
      - Do NOT carry across a RID gap (>1) when both rows carry numeric _rid.
    """
    if not rows:
        return rows

    def _norm(s):
        try:
            return _norm_unicode_quotes(s or "")
        except Exception:
            return s or ""

    def _starts_with_opener(s):
        return bool(re.match(r'^\s*["“«]', _norm(s)))

    def _ends_with_closer(s):
        return bool(re.search(r'["”»]\s*$', _norm(s)))

    def _is_punct_only(s):
        t = (_norm(s) or "").strip()
        return (
            bool(t)
            and bool(re.match(r"^[\s,.;:—–\-–—…()]*$", t))
            and not re.search(r"[A-Za-z0-9]", t)
        )

    def _rid_num(r):
        rid = r.get("_rid")
        if rid is None:
            return None
        m = re.search(r"(\d+)", str(rid))
        return int(m.group(1)) if m else None

    def _rid_gap(a, c) -> bool:
        ra, rc = _rid_num(a), _rid_num(c)
        return ra is not None and rc is not None and abs(rc - ra) > 1

    out = list(rows)
    i = 0
    n = len(out)

    while i + 2 < n:
        a, b, c = out[i], out[i + 1], out[i + 2]
        if (
            looks_like_direct_speech(a.get("text") or "")
            and not looks_like_direct_speech(b.get("text") or "")
            and looks_like_direct_speech(c.get("text") or "")
            and (a.get("speaker") not in ("Narrator", "Unknown", None, ""))
            and not c.get("_lock_speaker")
            and _is_punct_only(b.get("text") or "")
        ):
            # hard guards: turn boundary, opener on C, RID gap
            if _ends_with_closer(a.get("text") or ""):
                i += 1
                continue
            if _starts_with_opener(c.get("text") or ""):
                i += 1
                continue
            if _rid_gap(a, c):
                i += 1
                continue

            # safe: apply via logger
            try:
                apply_speaker(
                    out[i + 2],
                    a.get("speaker"),
                    reason="carry_monologue",
                    stage="carry_monologue",
                    idx=i + 2,
                )
            except Exception:
                out[i + 2] = dict(out[i + 2], speaker=a.get("speaker"))
            try:
                log(
                    f"[mono-carry] '{a['speaker']}' → next quote | { (c.get('text') or '')[:60] }…"
                )
            except Exception:
                pass
        i += 1

    return out


def _demote_nonquote_character_rows(rows):
    """
    Demote any non-quote rows that still carry a person speaker back to Narrator.
    NEVER touches rows that contain a true quote span.
    Respects speaker locks.
    Keeps punctuation-only bridge rows (e.g., “— , …”) as-is.
    """
    out = []
    for r in rows or []:
        rr = dict(r)
        txt = rr.get("text") or ""

        # Authoritative span check (normalize first, then detect)
        has_span = bool(_quote_spans(_norm_unicode_quotes(txt)))

        if not has_span:
            sp = (rr.get("speaker") or "").strip()
            if sp not in (None, "", "Narrator", "Unknown") and not rr.get(
                "_lock_speaker"
            ):
                # Allow pure punctuation shims (don’t demote those)
                if not re.fullmatch(r"\s*[-—–,.:;…]*\s*", txt):
                    rr["speaker"] = "Narrator"

        out.append(rr)
    return out


def _carry_same_speaker_across_adjacent_quotes(rows):
    """
    Carry speaker forward to the next quote ONLY if the previous quote is confidently locked,
    and ONLY when it does not look like a new turn (…”  “…” or next starts with an opener).
    """
    out = []
    last_speaker = None
    last_conf = False
    last_text = ""
    last_rid = None

    def _norm(s):
        try:
            return _norm_unicode_quotes(s or "")
        except Exception:
            return s or ""

    def _starts_with_opener(s):
        return bool(re.match(r'^\s*["“«]', _norm(s)))

    def _ends_with_closer(s):
        return bool(re.search(r'["”»]\s*$', _norm(s)))

    def _rid_num(r):
        rid = r.get("_rid")
        if rid is None:
            return None
        m = re.search(r"(\d+)", str(rid))
        return int(m.group(1)) if m else None

    for r in rows or []:
        rr = dict(r)
        if rr.get("is_quote"):
            # candidate carry?
            if (
                (rr.get("speaker") in (None, "", "Unknown"))
                and last_conf
                and last_speaker not in ("Narrator", "Unknown", "", None)
            ):
                # guards: not a turn boundary, no RID gap
                if not _ends_with_closer(last_text) and not _starts_with_opener(
                    rr.get("text") or ""
                ):
                    this_rid = _rid_num(rr)
                    if not (
                        last_rid is not None
                        and this_rid is not None
                        and abs(this_rid - last_rid) > 1
                    ):
                        try:
                            apply_speaker(
                                rr,
                                last_speaker,
                                reason="carry_same_speaker",
                                stage="carry_same_speaker",
                            )
                        except Exception:
                            rr["speaker"] = last_speaker

            # update context
            sp = rr.get("speaker") or ""
            conf = bool(rr.get("_lock_speaker")) or rr.get("_lock_reason") in (
                "enlp_quote_match",
                "attrib_fragment",
                "tail_attrib_split",
            )
            last_speaker, last_conf = sp, conf
            last_text = rr.get("text") or ""
            last_rid = _rid_num(rr)
        else:
            last_speaker, last_conf = None, False
            last_text = ""
            last_rid = None
        out.append(rr)

    return out


def _final_resplit_multiquote_rows(rows):
    """
    Late safety: for any row that still contains >1 quote spans, split it again safely.
    Uses the robust splitter on a per-row basis.
    """
    if not rows:
        return rows
    out = []
    resplit = 0
    for r in rows:
        t = _norm_unicode_quotes(r.get("text") or "")
        spans = _quote_spans(t) if r.get("is_quote") else []
        if len(spans) > 1:
            splitted = _split_results_on_multiple_quote_spans([r])
            out.extend(splitted)
            resplit += 1
        else:
            out.append(dict(r))
    DBG["final_resplit_rows"] = DBG.get("final_resplit_rows", 0) + resplit
    return out


# --- Glue soft-wrapped paragraph quotes into one row (before attribution) ---
# RE-ENABLED FOR AUDIOBOOK: Keeps multi-sentence quotes as one atomic block.
# This merges quote rows that are part of the same paragraph quote (soft-wrapped).
# Essential for TTS to keep quote integrity - each quote = one row for voice assignment.
SOFTWRAP_GLUE = True


def _is_open_quote_row(txt: str) -> bool:
    s = _norm_unicode_quotes(txt or "").strip()
    # starts with an opening quote and has no closing quote after the last opening
    return s.startswith("“") and ("”" not in s or s.rfind("”") < s.find("“"))


def _has_closing_quote(txt: str) -> bool:
    s = _norm_unicode_quotes(txt or "")
    return "”" in s


def _join_hyphen_wrap(a: str, b: str) -> str:
    """
    Join two lines inside a quote, handling soft hyphenation & spacing:
    - '... pro-\n fag ...' -> '... pro-fag ...' (uses non-breaking hyphen)
    - otherwise join with a single space
    """
    a = a.rstrip()
    b = b.lstrip()
    if a.endswith("-"):
        # remove trailing '-' on a, and don't insert an extra space
        return a[:-1] + "-" + b  # NBSP hyphen for readability
    # ensure single space between fragments
    if a and b and not a.endswith((" ", "\n")):
        return a + " " + b
    return a + b


def _glue_softwrapped_quotes(rows: list[dict]) -> list[dict]:
    """
    Merge consecutive rows that belong to the *same paragraph quote*.

    We ONLY glue when:
      • the current row is a quote that starts with an opener AND
      • the current row has NO closing quote after that opener (true soft-wrap), and
      • subsequent glued rows are quote rows that do NOT start with an opener
        (continuation lines), optionally ending with a closer.

    We NEVER glue a next row that starts with an opener — that's almost surely
    a new speaker/turn and must remain separate.
    """
    if not rows or not SOFTWRAP_GLUE:
        return rows

    try:
        DBG.setdefault("softwrap_runs", 0)
        DBG.setdefault("softwrap_rows_glued", 0)
        DBG.setdefault("softwrap_chars_joined", 0)
    except Exception:
        pass

    def _starts_with_opener(s: str) -> bool:
        t = _norm_unicode_quotes(s or "")
        return bool(
            re.match(r'^\s*"', t)
        )  # after normalization, all openers look like "

    out, i, n = [], 0, len(rows)

    while i < n:
        r = rows[i]
        txt = r.get("text") or ""
        is_q = bool(r.get("is_quote"))

        # Only start when: quote row, begins with opener, and does NOT already close that opener
        if is_q and _starts_with_opener(txt) and not _has_close_after_first_open(txt):
            try:
                DBG["softwrap_runs"] += 1
            except Exception:
                pass

            merged = dict(r)
            i += 1

            # consume quote rows that do NOT start with an opener (continuations)
            while i < n:
                nxt = rows[i]
                n_txt = nxt.get("text") or ""

                # stop gluing if the next row is narration
                if not nxt.get("is_quote"):
                    break

                # hard stop: next row starts with an opener → a new turn
                if _starts_with_opener(n_txt):
                    break

                # continuation line: glue verbatim
                merged["text"] = _join_hyphen_wrap(merged.get("text") or "", n_txt)
                try:
                    DBG["softwrap_rows_glued"] += 1
                    DBG["softwrap_chars_joined"] += len(n_txt)
                except Exception:
                    pass
                i += 1

                # if the continuation itself now closes (e.g., ends with the closer), stop
                if _has_close_after_first_open(n_txt):
                    break

            merged["is_quote"] = True
            out.append(merged)
            continue

        # normal row
        out.append(r)
        i += 1

    return out


def _promote_softwrap_continuations(rows: list[dict]) -> list[dict]:
    """
    If a quote row ends with a dangling opener (odd double-quote glyph count),
    and the next row is Narrator with no quote glyphs and not an attribution fragment,
    promote the next row to a quote (and carry speaker when safe).
    We DO NOT glue text here; merging (same speaker) happens later in _merge_quote_runs_by_speaker.
    """
    if not rows:
        return rows

    def _dq_count(s: str) -> int:
        t = _norm_unicode_quotes(s or "", keep_curly=True)
        return t.count('"') + t.count("“") + t.count("”") + t.count("«") + t.count("»")

    def _has_dq(s: str) -> bool:
        return _dq_count(s) > 0

    def _likely_attrib_or_colon(s: str) -> bool:
        t = (s or "").strip()
        try:
            if _looks_like_attribution_fragment(t):
                return True
        except Exception:
            pass
        try:
            if "_NAME_COLON_RX" in globals() and _NAME_COLON_RX.match(t):
                return True
        except Exception:
            pass
        return False

    out = []
    n = len(rows)
    i = 0
    promos = 0

    while i < n:
        cur = dict(rows[i])
        out.append(cur)

        # lookahead
        if i + 1 < n:
            nxt = dict(rows[i + 1])

            # A) current is a quote and has an odd number of double-quote glyphs (likely dangling)
            cur_is_q = bool(cur.get("is_quote"))
            cur_odd = _dq_count(cur.get("text") or "") % 2 == 1

            # B) next has no quote glyphs and is currently Narrator (or Unknown)
            nxt_is_plain = not bool(nxt.get("is_quote"))
            nxt_has_no_glyphs = not _has_dq(nxt.get("text") or "")
            nxt_is_neutral = nxt.get("speaker") in (None, "", "Unknown", "Narrator")

            # C) next is not an explicit attribution fragment or name-colon head
            if (
                cur_is_q
                and cur_odd
                and nxt_is_plain
                and nxt_has_no_glyphs
                and nxt_is_neutral
                and not _likely_attrib_or_colon(nxt.get("text") or "")
            ):
                # Promote the next row to quote
                nxt["is_quote"] = True
                # carry speaker if the current is confidently assigned to a real speaker
                sp = (cur.get("speaker") or "").strip()
                if sp and sp not in ("Narrator", "Unknown"):
                    nxt["speaker"] = sp
                    # do NOT hard-lock; let later stages adjust if needed
                    nxt["_lock_reason"] = "softwrap_promote"
                out.append(nxt)
                promos += 1
                i += 2
                continue

        i += 1

    try:
        DBG["softwrap_promotions"] = DBG.get("softwrap_promotions", 0) + promos
    except Exception:
        pass

    return out


def _has_close_after_first_open(s: str) -> bool:
    t = _norm_unicode_quotes(s or "", keep_curly=True)
    first = None
    for i, ch in enumerate(t):
        if ch in {"“", '"', "‘"}:
            first = i
            break
    if first is None:
        return False
    closer = {"”": "“", '"': '"', "’": "‘"}  # reverse map
    want = closer.get(t[first], '"')
    return want in t[first + 1 :]


def _force_split_adjacent_quotes(results):
    """
    If a *quote row* contains multiple adjacent quoted chunks (e.g., “A.” “B?” “C.”),
    split it into multiple quote rows safely (verbatim children).
    """
    if not results:
        return results

    # Close-quote [” or "] then optional punctuation/dash/space, then open-quote [“ or "]
    GLUE_RX = re.compile(r'(["”])\s*[.,;:!?—–-]*\s*(["“])')

    out = []
    splits = 0

    for r in results:
        t = _norm_unicode_quotes(r.get("text") or "")
        if not r.get("is_quote") or not t:
            out.append(r)
            continue

        if not GLUE_RX.search(t):
            out.append(r)
            continue

        parts, last = [], 0
        for m in GLUE_RX.finditer(t):
            cut = m.start(2)  # split right before the second (opening) quote
            chunk = t[last:cut]
            chs = chunk.strip()
            # skip pure-empty quote fragments like '""' or '“”' — they'll be handled
            # by the empty-quote repair later if needed
            if chs and chs not in ('""', "“”"):
                parts.append(chunk)
            last = cut
        tail = t[last:]
        tail_s = tail.strip()
        if tail_s and tail_s not in ('""', "“”"):
            parts.append(tail)

        if len(parts) <= 1:
            out.append(r)
            continue

        first = True
        for p in parts:
            rr = dict(r)
            rr["text"] = p
            rr["is_quote"] = True
            if first:
                first = False
            else:
                rr.pop("_rid", None)
            out.append(rr)

        splits += len(parts) - 1

    try:
        DBG["adjacent_quote_splits"] = DBG.get("adjacent_quote_splits", 0) + splits
    except Exception:
        pass

    return out


def _repair_empty_quote_followed_by_speech(rows):
    """
    Fix the pattern: [Narrator connector], ['""' as a quote], [Narrator that is actually the speech].
    Promote the following narrator to a proper quoted row, move the RID forward, and drop the empty quote row.
    """
    if not rows:
        return rows

    out = []
    i = 0
    n = len(rows)
    repaired = 0

    while i < n:
        cur = dict(rows[i])
        tcur = _norm_unicode_quotes(cur.get("text") or "").strip()
        if cur.get("is_quote") and tcur in ('""', "“”"):
            # Prefer to promote the *next* row when it looks like speech content
            if i + 1 < n:
                nxt = dict(rows[i + 1])
                tnxt = _norm_unicode_quotes(nxt.get("text") or "").strip()
                if tnxt and nxt.get("speaker") == "Narrator":
                    # Promote next row to a quoted row
                    if not (tnxt.startswith('"') or tnxt.startswith("“")):
                        tnxt = '"' + tnxt
                    if not (tnxt.endswith('"') or tnxt.endswith("”")):
                        tnxt = tnxt + '"'
                    nxt["text"] = tnxt
                    nxt["is_quote"] = True
                    # Move RID forward so the auditor maps the same row
                    if cur.get("_rid") is not None:
                        nxt["_rid"] = cur["_rid"]
                    out.append(nxt)
                    repaired += 1
                    i += 2
                    continue
            # Otherwise just drop the empty quote row
            i += 1
            continue

        out.append(cur)
        i += 1

    DBG["empty_quote_repairs"] = DBG.get("empty_quote_repairs", 0) + repaired
    return out


def _rehydrate_quote_rows_without_spans(rows):
    """
    For any row flagged is_quote=True but lacking a true span, wrap in quotes.
    Prevents later demotion to Narrator.
    """
    out = []
    fixed = 0
    for r in rows or []:
        rr = dict(r)
        if rr.get("is_quote") and not _quote_spans(
            _norm_unicode_quotes(rr.get("text") or "", keep_curly=True)
        ):
            s = (rr.get("text") or "").strip()
            if s and s not in ('""', "“”"):
                rr["text"] = '"' + s.strip('"“”') + '"'
                fixed += 1
        out.append(rr)
    DBG["rehydrate_quote_rows"] = DBG.get("rehydrate_quote_rows", 0) + fixed
    return out


def _is_continuation_para(txt: str) -> bool:
    """
    Detect multi-paragraph quote continuation: paragraph starts with a quote
    but does not appear to end with a closing quote (or trails off).
    """
    s = (txt or "").strip()
    if not s:
        return False
    starts_q = s[0] in QUOTE_CHARS
    ends_q = s.endswith('"') or s.endswith("”")
    ends_open = s.endswith("—") or s.endswith("...") or s.endswith("…")
    # If it starts quoted and either clearly not closed yet, treat as continuation
    return starts_q and (not ends_q or ends_open)


def _propagate_quote_context(rows):
    """
    If a previous row opens a quote but doesn't clearly close it, mark *only
    punctuation-only* narrator shims as quoted. Do NOT convert attribution
    prose like 'said Ava' or 'Ava said' into dialogue.
    """
    if not rows:
        return rows

    def punct_only(s: str) -> bool:
        s = (s or "").strip()
        # allow only punctuation/quote glyphs; no letters/digits
        return bool(s) and not re.search(r"[A-Za-z0-9]", s)

    def _closes(s: str) -> bool:
        s = s or ""
        return s.rstrip().endswith(("”", '"'))

    out = []
    in_quote = False
    carry_speaker = None

    for r in rows:
        rr = dict(r)
        t = _norm_unicode_quotes(rr.get("text") or "")
        is_q = looks_like_direct_speech(t)

        if is_q:
            out.append(rr)
            sp = rr.get("speaker")
            if sp and sp not in ("Narrator", "Unknown"):
                carry_speaker = sp

            # --- CHANGED: use your continuation detector
            if _is_continuation_para(t):
                in_quote = True
            elif _closes(t):
                in_quote = False
            # --------------------------------------------
            continue

        # narrator row inside an open quote:
        if in_quote:
            # only upgrade *pure punctuation* bridges; never attribution prose
            if punct_only(t):
                rr["is_quote"] = True
                if (
                    rr.get("speaker") in (None, "", "Narrator", "Unknown")
                ) and carry_speaker:
                    rr["speaker"] = carry_speaker
                out.append(rr)
                if _closes(t):
                    in_quote = False
                continue
            # attribution fragments or real prose stay narrator
            if "_ATTRIB_LINE_RX" in globals() and _ATTRIB_LINE_RX.match(t):
                out.append(rr)
                continue

        out.append(rr)

    return out


def _apply_name_colon_rule(rows, alias_inv):
    """
    If a row looks like `Name: text`, treat it as a spoken line by Name.
    If `text` is empty, push Name to the next quoted row as its speaker.
    """
    out = []
    n = len(rows)
    for i, r in enumerate(rows):
        t = _norm_unicode_quotes(r.get("text") or "")
        m = _NAME_COLON_RX.match(t)
        if not m:
            out.append(r)
            continue

        raw_name = m.group("name")
        rest = (m.group("rest") or "").strip()

        sp = _sanitize_person_name(raw_name) or "Unknown"
        if sp not in {"Narrator", "Unknown"}:
            sp = _alias_correct(sp, alias_inv or {})

        if rest:
            out.append(
                {
                    "speaker": sp,
                    "text": rest,
                    "is_quote": looks_like_direct_speech(rest),
                }
            )
        else:
            pushed = False
            if i + 1 < n:
                nx = dict(rows[i + 1])
                if looks_like_direct_speech(nx.get("text") or ""):
                    if nx.get("speaker") in (None, "", "Unknown", "Narrator"):
                        nx["speaker"] = sp
                    nx["is_quote"] = True
                    rows[i + 1] = nx
                    pushed = True
            if KEEP_ATTRIB_TEXT and not pushed:
                out.append({"speaker": "Narrator", "text": t, "is_quote": False})
    return out


# --- Safety splitter: separate narrator tails that were glued onto a quote (instrumented) ---
_POST_QUOTE_SENT_RX = re.compile(r'(["”])\s*([.!?])\s+([A-Z])')


def _separate_accidental_quote_narration_merges(rows: list[dict]) -> list[dict]:

    out = []
    for r in rows:
        rr = dict(r)
        txt = rr.get("text") or ""
        if not rr.get("is_quote"):
            out.append(rr)
            continue

        s = _norm_unicode_quotes(txt)
        spans = _quote_spans_balanced(s)
        if not spans:
            out.append(rr)
            continue

        last_close = spans[-1][1]
        tail = s[last_close:].strip()

        if '"' in tail or "“" in tail or "”" in tail:
            out.append(rr)
            continue

        m = _POST_QUOTE_SENT_RX.search(s)
        if tail and (m or re.match(r"^[A-Z]|^(?:The|A|An)\b", tail)):
            quote_text = s[:last_close].rstrip()
            narr_text = tail.lstrip(" .,!?:;—–-")

            if quote_text:
                out.append({**rr, "text": quote_text, "is_quote": True})
            if narr_text:
                out.append(
                    {"text": narr_text, "speaker": "Narrator", "is_quote": False}
                )

            try:
                DBG["narr_tail_splits"] += 1
            except Exception:
                pass
        else:
            out.append(rr)

    return out


# --- tiny trace helper (uses your existing log + stage_stats) ---
def trace_note(stage: str, msg: str) -> None:
    """
    Lightweight trace line. Writes to log and <prefix>.stage_stats.tsv if trace_init ran.
    """
    import csv
    import os

    # log
    try:
        log(f"[trace] {stage} | {msg}")
    except Exception:
        pass

    # append to stage_stats.tsv
    try:
        outdir = DBG.get("_trace_outdir")
        pref = DBG.get("_trace_prefix")
        if outdir and pref:
            p = os.path.join(outdir, f"{pref}.stage_stats.tsv")
            with open(p, "a", encoding="utf-8", newline="") as f:
                csv.writer(f, delimiter="\t").writerow([stage, "NOTE", msg])
    except Exception as e:
        try:
            log(f"[trace-note] write-failed: {e}")
        except Exception:
            pass


def _split_inline_tail_attrib_in_quotes(rows, *args):
    """
    Robust splitter for glue inside quote rows:
      1) ...?"demanded King..."        -> [quote]["demanded King..." as Narrator][rest...]
         ...”said Zack with a shrug.   -> [quote][tail narration][rest...]
         (Works even with no space/comma/dash after close quote.)
      2) ...” “I’ll... or ...”“I’ll... -> [quote][quote] (splits back-to-back quotes.)
    Keeps tail as Narrator; does not set a speaker. Records attrib_op row.
    """
    import re

    if not rows:
        return rows

    # Quote glyphs
    OPEN_Q = '“"«'
    CLOSE_Q = '”"»'
    RX_OPEN = re.compile(rf"[{OPEN_Q}]")
    RX_CLOSE = re.compile(rf"[{CLOSE_Q}]")

    # Build a loose verb set for narration tails (added multiword)
    _verbs_fallback = {
        "said",
        "says",
        "say",
        "ask",
        "asks",
        "asked",
        "reply",
        "replies",
        "replied",
        "answer",
        "answers",
        "answered",
        "tell",
        "tells",
        "told",
        "call",
        "called",
        "yell",
        "yelled",
        "shout",
        "shouted",
        "cry",
        "cried",
        "whisper",
        "whispered",
        "murmur",
        "murmured",
        "mutter",
        "muttered",
        "snap",
        "snapped",
        "retort",
        "retorted",
        "laugh",
        "laughed",
        "sob",
        "sobbed",
        "hiss",
        "hissed",
        "note",
        "noted",
        "observe",
        "observed",
        "remark",
        "remarked",
        "insist",
        "insisted",
        "counter",
        "countered",
        "agree",
        "agreed",
        "warn",
        "warned",
        "offer",
        "offered",
        "beg",
        "begged",
        "demand",
        "demanded",
        "protest",
        "protested",
        "announce",
        "announced",
        "explain",
        "explained",
        "declare",
        "declared",
        "argue",
        "argued",
        "suggest",
        "suggested",
        "continue",
        "continued",
        "interject",
        "interjected",
        "interrupt",
        "interrupted",
        "concede",
        "conceded",
        "promise",
        "promised",
        "plead",
        "pleaded",
        "rejoin",
        "rejoined",
        "state",
        "stated",
        "blurt",
        "blurted",
        "query",
        "queried",
        "go",
        "went",
        "add",
        "added",
        "went on",
        "carried on",
        "went on grimly",
        "said simply",
        "said softly",
    }
    verbs = (
        set(globals().get("_ATTRIB_VERBS_LOOSE", []))
        or set(globals().get("_ATTRIB_VERBS", []))
        or _verbs_fallback
    )
    vpat = r"(?:%s)" % "|".join(sorted(map(re.escape, verbs), key=len, reverse=True))

    # Proper names or pronouns (no change)
    proper = r"(?:[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}|he|she|they|we|i|him|her|them|He|She|They|We|I)"

    # Expanded filler: adverbs, 'in a X', 'with a X', up to 5 instances
    adverbs = (
        r"(?:\s+(?:\w+ly|then|again|softly|quietly|firmly|evenly|calmly|angrily|sharply|dryly|simply|wryly|grimly|sadly|leaden|curiously|in a monotone|with a shrug|with a sigh|in a low voice)){0,5}?"
        r"(?:\s+(?:in|with)\s+(?:a|an|the)\s+[a-z]{2,20}(?:\s+[a-z]{2,20}){0,2})?"
    )

    # Expanded: Allow glued attributions with no space after close quote
    RX_TAIL_AFTER_CLOSE = re.compile(
        rf"^[{CLOSE_Q}]\s*(?:[,—–-]?\s*)?"  # close quote, optional comma/dash
        rf"(?:(?:{proper})\s*)?"  # optional name/pronoun
        rf"(?:{vpat})\s*"  # verb
        rf"{adverbs}"
        rf"(?:\s*(?:{proper}|him|her|them))?"  # optional name/pronoun/object
        rf"\s*[\.,;!?—–]*$",
        re.I,
    )

    # We'll detect glued attributions procedurally: look at the raw text
    # immediately AFTER the close-quote and require the following token to
    # start with a lowercase letter and be either a pronoun or a verb from
    # our loose verb set. This avoids matching capitalized names (false positives).
    PRON_LIST = {"he", "she", "they", "we", "i", "you", "him", "her", "them"}
    # note: `verbs` is a set defined earlier in this function; we'll reuse it

    # Back-to-back quotes (with or without whitespace)
    RX_QQ = re.compile(rf"[{CLOSE_Q}]\s*[{OPEN_Q}]")

    out = []
    for idx, row in enumerate(rows):
        if not row.get("is_quote"):
            out.append(row)
            continue

        text = row.get("text") or ""
        if not text:
            out.append(row)
            continue

        t_norm = _norm_unicode_quotes(
            text
        )  # Assumes this calls _normalize_quote_spacing now

        pieces = []
        changed = False

        def emit_quote(s):
            if not s or not s.strip():
                return
            # don't emit bare quote glyphs (e.g., '"') — require inner content
            inner = re.sub(r"^[\s\"“”‘’«»]+|[\s\"“”‘’«»]+$", "", s)
            if not inner:
                return
            q = dict(row)
            q["text"] = s.strip()
            q["is_quote"] = True
            q.pop("_lock_speaker", None)
            q.pop("_locked_to", None)
            q.pop("_lock_reason", None)
            pieces.append(q)

        def emit_narr(s):
            if not s.strip():
                return
            n = dict(row)
            n["text"] = s.strip()
            n["is_quote"] = False
            n["speaker"] = "Narrator"
            n.pop("_lock_speaker", None)
            n.pop("_locked_to", None)
            n.pop("_lock_reason", None)
            pieces.append(n)

        s = t_norm

        # (A) Split back-to-back quotes
        while True:
            m = RX_QQ.search(s)
            if not m:
                break
            changed = True
            a, _ = m.span()
            left = s[: a + 1].strip()  # Up to close quote
            right = s[a + 1 :].lstrip()  # From next open quote
            emit_quote(left)
            s = right

        # (B) Split close-quote + narration tail(s)
        # Use the rightmost close-quote that has a preceding open-quote so we don't
        # accidentally treat an opening quote as a "close" (fixes cases like
        # He said, "Wait"and left.)
        while True:
            if not s:
                break
            # find the rightmost close-quote glyph
            tail_pos = max((s.rfind(ch) for ch in CLOSE_Q))
            if tail_pos == -1:
                break
            # find an open-quote before that close-quote
            open_before = max((s.rfind(ch, 0, tail_pos) for ch in OPEN_Q))
            if open_before == -1:
                # fallback to the original search if we couldn't find a paired open
                start_search_at = 1 if len(s) > 1 else 0
                mc = RX_CLOSE.search(s, start_search_at)
                if not mc:
                    break
                tail_start = mc.start()
            else:
                tail_start = tail_pos

            tail = s[tail_start:]
            # Try normal tail match
            if RX_TAIL_AFTER_CLOSE.match(tail):
                left = s[: tail_start + 1].strip()
                rest = s[tail_start + 1 :].lstrip()
                mnext = RX_OPEN.search(rest)
                if mnext:
                    narr_tail = rest[: mnext.start()].strip()
                    s = rest[mnext.start() :]
                else:
                    narr_tail = rest.strip()
                    s = ""
                emit_quote(left)
                emit_narr(narr_tail)
                changed = True
                continue

            # Try glued attribution fallback (procedural)
            rest_after_close = s[tail_start + 1 :]
            mword = re.match(r"\s*([a-z][\w\-']*)", rest_after_close)
            if mword:
                tok = mword.group(1)
                # accept only if tok is a pronoun or a known verb (lowercase)
                if tok.lower() in PRON_LIST or tok.lower() in set(
                    v.lower() for v in verbs
                ):
                    left = s[: tail_start + 1].strip()
                    rest = rest_after_close.lstrip()
                    mnext = RX_OPEN.search(rest)
                    if mnext:
                        narr_tail = rest[: mnext.start()].strip()
                        s = rest[mnext.start() :]
                    else:
                        narr_tail = rest.strip()
                        s = ""
                    emit_quote(left)
                    emit_narr(narr_tail)
                    changed = True
                    continue
                # Additional heuristic: accept short conjunction-starting tails like
                # 'and left' or 'but left' as narration tails (common in glue cases).
                # This lets strings like 'He said, "Wait"and left.' split sensibly.
                conj_match = re.match(
                    r"\s*(and|but|then)\s+([a-z][\w\-']*)", rest_after_close
                )
                if conj_match:
                    left = s[: tail_start + 1].strip()
                    rest = rest_after_close.lstrip()
                    mnext = RX_OPEN.search(rest)
                    if mnext:
                        narr_tail = rest[: mnext.start()].strip()
                        s = rest[mnext.start() :]
                    else:
                        narr_tail = rest.strip()
                        s = ""
                    emit_quote(left)
                    emit_narr(narr_tail)
                    changed = True
                    continue
            # If none of the heuristics matched, avoid infinite loops by removing
            # up to and including this quote and continuing.
            s = s[tail_start + 1 :]
            break  # avoid drift; let next iteration handle remaining text

        # Remaining text
        rem = s.strip()
        if rem:
            if rem and rem[0] in OPEN_Q:
                emit_quote(rem)
            else:
                emit_narr(rem)

        if changed:
            out.extend(pieces)
            try:
                record_attrib_op_row(
                    "split_inline_tail",
                    "split",
                    row,
                    row.get("speaker"),
                    "Narrator",
                    "closequote_tail_or_qq_split",
                    idx,
                )
            except Exception:
                pass
        else:
            out.append(row)

    return out


def _demote_misquoted_attrib_rows(results):
    """
    If a *quote row* is just a tiny quoted attribution fragment (e.g., "explained Smith."),
    convert it to Narrator (no quotes), and try to lock the speaker of the PREVIOUS quote.
    """
    if not results:
        return results

    proper = r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2}"
    verbs = globals().get("_ATTRIB_VERBS", set()) or {
        "said",
        "asked",
        "replied",
        "explained",
        "shouted",
        "cried",
        "murmured",
        "whispered",
        "noted",
        "observed",
        "remarked",
        "insisted",
        "continued",
        "added",
        "snapped",
        "retorted",
        "laughed",
        "sobbed",
        "hissed",
        "breathed",
        "muttered",
        "stated",
        "announced",
        "groaned",
    }
    vpat = r"(?:%s)" % "|".join(sorted(map(re.escape, verbs)))
    RX_QATTR = re.compile(
        rf'^\s*["“]\s*(?:{vpat})\s+{proper}\s*[.!?]?\s*["”]\s*$', re.IGNORECASE
    )
    RX_QATTR_NFIRST = re.compile(
        rf'^\s*["“]\s*{proper}\s+{vpat}\s*[.!?]?\s*["”]\s*$', re.IGNORECASE
    )

    out = []
    for i, r in enumerate(results):
        if not r.get("is_quote"):
            out.append(r)
            continue

        t = (r.get("text") or "").strip()
        if len(t) > 40:  # too long to be a glued attrib-only line
            out.append(r)
            continue

        if RX_QATTR.match(t) or RX_QATTR_NFIRST.match(t):
            # demote this line to narration
            narr = dict(r)
            narr["is_quote"] = False
            narr["speaker"] = "Narrator"
            narr["text"] = t.strip(' "“”')  # keep the words, drop the outer quotes
            out.append(narr)

            # try to lock the previous quote's speaker if this was clearly a tag
            j = len(out) - 2
            while j >= 0 and not looks_like_direct_speech(out[j].get("text") or ""):
                j -= 1
            if j >= 0 and out[j].get("is_quote"):
                # don't overwrite a firm lock
                if not out[j].get("_lock_speaker"):
                    sp = out[j].get("speaker") or "Unknown"
                    out[j]["speaker"] = sp
                    _lock_speaker(out[j], "dequote_glued_tail")

                try:
                    DBG["dequoted_attrib_rows"] = DBG.get("dequoted_attrib_rows", 0) + 1
                    # record a simple attributed op row for auditing
                    try:
                        record_attrib_op_row(
                            "dequote_glued_tail",
                            "dequote",
                            r,
                            r.get("speaker"),
                            "Narrator",
                            "dequote_glued_tail",
                        )
                    except Exception:
                        # fallback to generic recorder
                        try:
                            record_attrib_op(
                                "dequote_glued_tail",
                                op="dequote",
                                rid=r.get("_rid"),
                                prev=r.get("speaker"),
                                new="Narrator",
                                reason="dequote_glued_tail",
                            )
                        except Exception:
                            pass
                except Exception:
                    pass
        else:
            out.append(r)

    return out


def _debug_assert_quote_flag_consistency(rows):
    for i, r in enumerate(rows):
        t = r.get("text") or ""
        if any(q in t for q in ('"', "“", "”", "‘", "’")) and not r.get("is_quote"):
            log(
                f"[debug-quote-flag] idx={i} has quote char but is_quote=False | {t[:80]}…"
            )
    return rows


def _two_party_fill_unknowns(results):
    """If a quoted line is Unknown and flanked by two different speakers in quoted lines, fill with the next speaker."""
    if not results:
        return results
    out = [dict(r) for r in results]
    n = len(out)
    for i in range(1, n - 1):
        cur = out[i]
        if not looks_like_direct_speech(cur["text"]) or cur["speaker"] != "Unknown":
            continue
        prev, nxt = out[i - 1], out[i + 1]
        if all(looks_like_direct_speech(x["text"]) for x in (prev, nxt)):
            a, b = prev["speaker"], nxt["speaker"]
            if (
                a not in ("Narrator", "Unknown")
                and b not in ("Narrator", "Unknown")
                and a != b
            ):
                if not cur.get("_lock_speaker"):
                    cur["speaker"] = b
                log(f"[unknown-fix] two-party -> '{b}' | {cur['text'][:60]}…")
    return out


def _load_simple_whitelist(output_dir: str, prefix: str):
    """
    Populate:
      - CANON_WHITELIST: set of canonical display names
      - WH_ALIAS: token -> Canonical (first/last/unique variants)
      - CJ_MAP: optional char_id -> Canonical (if provided)

    Reads <prefix>.characters_simple.json (pref), falling back to book_input or bare name-only format.
    """
    global CANON_WHITELIST, WH_ALIAS, CJ_MAP
    CANON_WHITELIST = set()
    WH_ALIAS = {}
    CJ_MAP = {}

    path = os.path.join(output_dir, f"{prefix}.characters_simple.json")
    if not os.path.exists(path):
        for p in (
            os.path.join(output_dir, "book_input.characters_simple.json"),
            os.path.join(output_dir, "characters_simple.json"),
        ):
            if os.path.exists(p):
                path = p
                break

    if not os.path.exists(path):
        log("[whitelist] no characters_simple.json found")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        chars = data.get("characters", []) or []

        # First pass: collect canonicals; prefer multi-token by design (writer already did this)
        for c in chars:
            nm = (c.get("normalized_name") or c.get("name") or "").strip()
            if not nm:
                continue
            nm = normalize_name(nm).title()
            CANON_WHITELIST.add(nm)
            cid = c.get("char_id", None)
            if cid is not None:
                CJ_MAP[str(cid)] = nm

        # Second pass: add aliases if present; only map unique tokens to a canonical
        # Build token->set[canonical] bag to filter ambiguity.
        from collections import defaultdict

        bag = defaultdict(set)
        for c in chars:
            nm = normalize_name(
                (c.get("normalized_name") or c.get("name") or "")
            ).title()
            if not nm:
                continue
            toks = [t for t in re.split(r"\s+", normalize_name(nm)) if t]
            for t in toks:
                bag[t.lower()].add(nm)
            for a in c.get("aliases") or []:
                for t in re.split(r"\s+", normalize_name(a)):
                    if t:
                        bag[t.lower()].add(nm)

        for tok, cans in bag.items():
            if len(cans) == 1:
                WH_ALIAS[tok] = list(cans)[0]

        log(
            f"[whitelist] loaded {len(CANON_WHITELIST)} canonicals; {len(WH_ALIAS)} unique alias tokens; CJ_MAP={len(CJ_MAP)}"
        )
    except Exception as e:
        log(f"[whitelist] failed to read: {e}")


def _alias_correct(s: str, alias_inv: dict) -> str:
    """
    For single-token speakers, map to the canonical full name using alias_inv;
    then clamp the result to characters_simple.json if loaded.
    """
    if not s or s == "Narrator":
        return s

    parts = s.split()
    # If it's already multi-token (e.g., "Mike Jones"), just whitelist-clamp
    if len(parts) != 1:
        return _whitelist_clamp(s) or s

    tok = parts[0].lower()
    res = s

    if alias_inv:
        if tok in alias_inv:
            res = (alias_inv[tok] or s).title()
        else:
            # fuzzy fallback
            keys = list(alias_inv.keys())
            match = difflib.get_close_matches(tok, keys, n=1, cutoff=0.86)
            if match:
                res = (alias_inv[match[0]] or s).title()

    # finally, clamp to whitelist (characters_simple.json), if present
    clamped = _whitelist_clamp(res) if CANON_WHITELIST else res
    if CANON_WHITELIST:
        if clamped is None:
            # If single-token and not clamped, return the original single token title-cased
            # but let later stages drop it if it isn't a real character.
            return res.title()
        return clamped
    return res


# --- Attribution text visibility toggles ---
KEEP_ATTRIB_TEXT = True  # keep narrator fragments like "said Billy"
ATTACH_ATTRIB_TO_QUOTE = False  # do NOT glue attribution to quote text
COALESCE_ALLOW_QUOTE_TO_QUOTE = False  # keep separate quote lines separate

# --- Role canonicalization (keeps useful roles as stable speakers) ---
ROLE_CANON = {
    "guard": "Guard",
    "security guard": "Guard",
    "jail guard": "Guard",
    "the guard": "Guard",
    "prison guard": "Guard",
    "a guard": "Guard",
    "the security guard": "Guard",
    "the jail guard": "Guard",
    "the prison guard": "Guard",
    "night guard": "Guard",
    "gate guard": "Guard",
    "bodyguard": "Guard",
    "the bodyguard": "Guard",
    "watchman": "Guard",
    "the watchman": "Guard",
    "sentry": "Guard",
    "the sentry": "Guard",
    "warden": "Guard",
    "the warden": "Guard",
    "servant": "Servant",
    "the servant": "Servant",
    "maid": "Servant",
    "the maid": "Servant",
    "housekeeper": "Servant",
    "the housekeeper": "Servant",
    "butler": "Servant",
    "the butler": "Servant",
    "footman": "Servant",
    "the footman": "Servant",
    "valet": "Servant",
    "the valet": "Servant",
    "chambermaid": "Servant",
    "the chambermaid": "Servant",
    "manservant": "Servant",
    "the manservant": "Servant",
    "handmaiden": "Servant",
    "the handmaiden": "Servant",
    "attendant": "Servant",
    "the attendant": "Servant",
    "driver": "Driver",
    "the driver": "Driver",
    "chauffeur": "Driver",
    "the chauffeur": "Driver",
    "cab driver": "Driver",
    "the cab driver": "Driver",
    "taxi driver": "Driver",
    "the taxi driver": "Driver",
    "coachman": "Driver",
    "the coachman": "Driver",
    "carriage driver": "Driver",
    "the carriage driver": "Driver",
    "bus driver": "Driver",
    "the bus driver": "Driver",
    "truck driver": "Driver",
    "the truck driver": "Driver",
    "waiter": "Waiter",
    "the waiter": "Waiter",
    "waitress": "Waiter",
    "the waitress": "Waiter",
    "server": "Waiter",
    "the server": "Waiter",
    "bartender": "Waiter",
    "the bartender": "Waiter",
    "barman": "Waiter",
    "the barman": "Waiter",
    "barmaid": "Waiter",
    "the barmaid": "Waiter",
    "host": "Waiter",
    "the host": "Waiter",
    "hostess": "Waiter",
    "the hostess": "Waiter",
    "doctor": "Doctor",
    "the doctor": "Doctor",
    "physician": "Doctor",
    "the physician": "Doctor",
    "surgeon": "Doctor",
    "the surgeon": "Doctor",
    "healer": "Doctor",
    "the healer": "Doctor",
    "medic": "Doctor",
    "the medic": "Doctor",
    "nurse": "Nurse",
    "the nurse": "Nurse",
    "head nurse": "Nurse",
    "the head nurse": "Nurse",
    "policeman": "Policeman",
    "the policeman": "Policeman",
    "police officer": "Policeman",
    "the police officer": "Policeman",
    "cop": "Policeman",
    "the cop": "Policeman",
    "officer": "Policeman",
    "the officer": "Policeman",
    "detective": "Policeman",
    "the detective": "Policeman",
    "inspector": "Policeman",
    "the inspector": "Policeman",
    "constable": "Policeman",
    "the constable": "Policeman",
    "sheriff": "Policeman",
    "the sheriff": "Policeman",
    "shopkeeper": "Shopkeeper",
    "the shopkeeper": "Shopkeeper",
    "merchant": "Shopkeeper",
    "the merchant": "Shopkeeper",
    "clerk": "Shopkeeper",
    "the clerk": "Shopkeeper",
    "store owner": "Shopkeeper",
    "the store owner": "Shopkeeper",
    "vendor": "Shopkeeper",
    "the vendor": "Shopkeeper",
    "tradesman": "Shopkeeper",
    "the tradesman": "Shopkeeper",
    "innkeeper": "Shopkeeper",
    "the innkeeper": "Shopkeeper",
    "landlord": "Shopkeeper",
    "the landlord": "Shopkeeper",
    "barkeep": "Shopkeeper",
    "the barkeep": "Shopkeeper",
    "messenger": "Messenger",
    "the messenger": "Messenger",
    "courier": "Messenger",
    "the courier": "Messenger",
    "herald": "Messenger",
    "the herald": "Messenger",
    "runner": "Messenger",
    "the runner": "Messenger",
    "page": "Messenger",
    "the page": "Messenger",
    "delivery boy": "Messenger",
    "the delivery boy": "Messenger",
    "stranger": "Stranger",
    "the stranger": "Stranger",
    "passerby": "Stranger",
    "the passerby": "Stranger",
    "traveler": "Stranger",
    "the traveler": "Stranger",
    "wanderer": "Stranger",
    "the wanderer": "Stranger",
    "visitor": "Stranger",
    "the visitor": "Stranger",
    "guest": "Stranger",
    "the guest": "Stranger",
    "soldier": "Soldier",
    "the soldier": "Soldier",
    "warrior": "Soldier",
    "the warrior": "Soldier",
    "knight": "Soldier",
    "the knight": "Soldier",
    "swordsman": "Soldier",
    "the swordsman": "Soldier",
    "archer": "Soldier",
    "the archer": "Soldier",
    "captain": "Soldier",
    "the captain": "Soldier",
    "general": "Soldier",
    "the general": "Soldier",
    "peasant": "Peasant",
    "the peasant": "Peasant",
    "villager": "Peasant",
    "the villager": "Peasant",
    "farmer": "Peasant",
    "the farmer": "Peasant",
    "serf": "Peasant",
    "the serf": "Peasant",
    "commoner": "Peasant",
    "the commoner": "Peasant",
    "child": "Child",
    "the child": "Child",
    "boy": "Child",
    "the boy": "Child",
    "girl": "Child",
    "the girl": "Child",
    "lad": "Child",
    "the lad": "Child",
    "lass": "Child",
    "the lass": "Child",
    "urchin": "Child",
    "the urchin": "Child",
    "youth": "Child",
    "the youth": "Child",
    "beggar": "Beggar",
    "the beggar": "Beggar",
    "vagrant": "Beggar",
    "the vagrant": "Beggar",
    "homeless man": "Beggar",
    "the homeless man": "Beggar",
    "pauper": "Beggar",
    "the pauper": "Beggar",
    "thief": "Thief",
    "the thief": "Thief",
    "robber": "Thief",
    "the robber": "Thief",
    "burglar": "Thief",
    "the burglar": "Thief",
    "pickpocket": "Thief",
    "the pickpocket": "Thief",
    "priest": "Priest",
    "the priest": "Priest",
    "monk": "Priest",
    "the monk": "Priest",
    "cleric": "Priest",
    "the cleric": "Priest",
    "friar": "Priest",
    "the friar": "Priest",
    "nun": "Priest",
    "the nun": "Priest",
    "wizard": "Wizard",
    "the wizard": "Wizard",
    "mage": "Wizard",
    "the mage": "Wizard",
    "sorcerer": "Wizard",
    "the sorcerer": "Wizard",
    "witch": "Wizard",
    "the witch": "Wizard",
    "enchanter": "Wizard",
    "the enchanter": "Wizard",
    "elder": "Elder",
    "the elder": "Elder",
    "wise man": "Elder",
    "the wise man": "Elder",
    "sage": "Elder",
    "the sage": "Elder",
    "old timer": "Elder",
    "the old timer": "Elder",
    "guide": "Guide",
    "the guide": "Guide",
    "scout": "Guide",
    "the scout": "Guide",
    "tracker": "Guide",
    "the tracker": "Guide",
    "pathfinder": "Guide",
    "the pathfinder": "Guide",
    "assistant": "Assistant",
    "the assistant": "Assistant",
    "aide": "Assistant",
    "the aide": "Assistant",
    "helper": "Assistant",
    "the helper": "Assistant",
    "librarian": "Librarian",
    "the librarian": "Librarian",
    "archivist": "Librarian",
    "the archivist": "Librarian",
    "scribe": "Librarian",
    "the scribe": "Librarian",
    "blacksmith": "Blacksmith",
    "the blacksmith": "Blacksmith",
    "smith": "Blacksmith",
    "the smith": "Blacksmith",
    "armorer": "Blacksmith",
    "the armorer": "Blacksmith",
    "tailor": "Tailor",
    "the tailor": "Tailor",
    "seamstress": "Tailor",
    "the seamstress": "Tailor",
    "dressmaker": "Tailor",
    "the dressmaker": "Tailor",
    "cook": "Cook",
    "the cook": "Cook",
    "chef": "Cook",
    "the chef": "Cook",
    "baker": "Cook",
    "the baker": "Cook",
    "fisherman": "Fisherman",
    "the fisherman": "Fisherman",
    "angler": "Fisherman",
    "the angler": "Fisherman",
    "hunter": "Hunter",
    "the hunter": "Hunter",
    "trapper": "Hunter",
    "the trapper": "Hunter",
    "miner": "Miner",
    "the miner": "Miner",
    "digger": "Miner",
    "the digger": "Miner",
    "artist": "Artist",
    "the artist": "Artist",
    "painter": "Artist",
    "the painter": "Artist",
    "sculptor": "Artist",
    "the sculptor": "Artist",
    "musician": "Musician",
    "the musician": "Musician",
    "bard": "Musician",
    "the bard": "Musician",
    "minstrel": "Musician",
    "the minstrel": "Musician",
    "fool": "Fool",
    "the fool": "Fool",
    "jester": "Fool",
    "the jester": "Fool",
    "clown": "Fool",
    "the clown": "Fool",
    "oracle": "Oracle",
    "the oracle": "Oracle",
    "seer": "Oracle",
    "the seer": "Oracle",
    "prophet": "Oracle",
    "the prophet": "Oracle",
    "alchemist": "Alchemist",
    "the alchemist": "Alchemist",
    "apothecary": "Alchemist",
    "the apothecary": "Alchemist",
    "herbalist": "Herbalist",
    "the herbalist": "Herbalist",
    "druid": "Herbalist",
    "the druid": "Herbalist",
}


def _canonicalize_role(name: str) -> str | None:
    if not name:
        return None
    low = (name or "").strip().lower()
    # quick hits
    if low in ROLE_CANON:
        return ROLE_CANON[low]
    # contains-key match (e.g., "the guard behind him")
    for key, canon in ROLE_CANON.items():
        if key in low:
            return canon
    return None


# Obvious non-person tokens (nouns, places, objects, adjectives that leaked in)
BANNED_TERMS = {
    # vehicles / objects / places / rooms
    "lexus",
    "toyota",
    "ford",
    "chevy",
    "chevrolet",
    "honda",
    "bmw",
    "mercedes",
    "subaru",
    "truck",
    "car",
    "sedan",
    "rifle",
    "pistol",
    "gun",
    "apartment",
    "house",
    "room",
    "office",
    "street",
    "road",
    "highway",
    "alley",
    "door",
    "window",
    "phone",
    "radio",
    "wallet",
    "purse",
    "bag",
    "coat",
    "hat",
    "suburb",
    "county",
    "oregon",
    "seaside",
    # generic groups / crowd
    "men",
    "old men",
    "older man",
    "young man",
    "people",
    "crowd",
    "voice",
    # adverbial or leaked tokens masquerading as names
    "simply",
    "softly",
    "firmly",
    "curiously",
    "quietly",
    "dryly",
}


def _attrib_only(text: str) -> bool:
    """True if the fragment is just an attribution like 'said Bob' / 'Bob said.' with no quoted content."""
    t = text.strip()
    if not t:
        return True
    if _ATTRIB_TAIL.match(t):
        return True
    if _ATTRIB_HEAD.match(t) and (
        '"' not in t and "“" not in t and "”" not in t and "’" not in t and "‘" not in t
    ):
        return True
    if len(t.split()) == 1 and ('"' not in t and "“" not in t):
        return True
    return False


def looks_like_direct_speech(txt: str) -> bool:
    """
    Strict dialogue detector:
      • must contain at least one balanced opener→closer span
      • ignore leading/trailing narrator junk when counting
    """
    if not txt:
        return False
    s = _norm_unicode_quotes(txt, keep_curly=True)

    # Fast guard: balanced glyph count only
    if not _balanced_quote_count(s):
        return False

    spans = _quote_spans_balanced(s)
    if not spans:
        return False

    # At least one span must start with an opener and end with a closer
    for a, b in spans:
        seg = s[a:b].strip()
        if not seg:
            continue
        if seg[0] in ('"', "“") and seg[-1] in ('"', "”"):
            return True
    return False


def normalize_name(n: str) -> str:
    # Keep letters, spaces, apostrophes, and hyphens; collapse whitespace.
    cleaned = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z\s'-]", "", (n or "").strip())).strip()
    
    if not cleaned:
        return "Unknown"
    
    lowered = cleaned.lower()
    
    # Don't modify Narrator or Unknown
    if lowered in {"narrator", "the narrator"}:
        return "Narrator"
    if lowered in {"unknown", "unk"}:
        return "Unknown"
    
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
    
    return cleaned


# Map smart quotes / guillemets → ASCII quotes
_SMART_QUOTE_MAP = {
    0x201C: ord('"'),
    0x201D: ord('"'),
    0x201E: ord('"'),
    0x201F: ord('"'),
    0x00AB: ord('"'),
    0x00BB: ord('"'),
    0x2018: ord("'"),
    0x2019: ord("'"),
    0x201A: ord("'"),
    0x201B: ord("'"),
}


def _normalize_quote_spacing(text: str) -> str:
    """
    Trim spaces immediately after opening quotes and before closing quotes.
    E.g., '" I' → '"I', 'Right! "' → 'Right!"'.
    Preserves other whitespace.
    """
    if not text:
        return text
    # Patterns for opening: " / “ / « followed by space(s)
    text = re.sub(r'(["“«])\s+', r"\1", text)
    # Patterns for closing: space(s) followed by " / ” / »
    text = re.sub(r'\s+([”"»])', r"\1", text)
    return text


def _norm_unicode_quotes(s: str, keep_curly: bool = False) -> str:
    r"""
    1) Decode \u201c / \u201d / \x.. escapes if present.
    2) Unescape HTML entities (&ldquo; &rdquo; &quot; &#x201c; etc.).
    3) Optionally normalize smart quotes/guillemets to ASCII " and '.
       If keep_curly=True, we preserve “ ” ‘ ’ so _quote_spans can use orientation.
    """
    if not s:
        return s

    # 1) decode escapes
    if "\\u" in s or "\\x" in s:
        try:
            s = codecs.decode(s, "unicode_escape")
        except Exception:
            pass

    # 2) HTML entities
    if "&" in s:
        s = html.unescape(s)

    if not keep_curly:
        # map curly/guillemets → ASCII
        s = s.translate(_SMART_QUOTE_MAP)

    # tighten tokenization gaps so quote glyphs don't get separated
    s = _fix_tokenization_gaps(s)

    # NEW: Normalize quote spacing (trim spaces after open/before close)
    return _normalize_quote_spacing(s)


# --- UI-only cleanup: undo spacey contractions like "are n’t" / "are n't" -> "aren’t/aren't" ---
_CONTRACTIONS_FIX = [
    # Generic n't with either ASCII or curly apostrophe
    (
        re.compile(
            r"\b(do|does|did|is|are|was|were|has|have|had|should|would|could|might|must)\s+n['’]t\b",
            re.IGNORECASE,
        ),
        r"\1n't",
    ),
    (re.compile(r"\b(wo)\s+n['’]t\b", re.IGNORECASE), r"won't"),  # special case
    (re.compile(r"\b(ca)\s+n['’]t\b", re.IGNORECASE), r"can't"),  # special case
    # I'm / you're / we're / they're / he's / she's
    (re.compile(r"\b(I)\s+['’]m\b"), r"\1'm"),
    (re.compile(r"\b([Yy]ou|[Ww]e|[Tt]hey|[Hh]e|[Ss]he)\s+['’]re\b"), r"\1're"),
    (re.compile(r"\b([Hh]e|[Ss]he|[Ii]t|[Tt]here|[Ww]ho)\s+['’]s\b"), r"\1's"),
    # "' s" -> "’s" (possessive fix)
    (re.compile(r"(?:’|')\s*s\b"), r"'s"),
]


def _fix_tokenization_artifacts(s: str) -> str:
    """
    UI-only cleanup for contractions. Safe:
      - No backslashes / backrefs that could leak into text
      - Handles curly/ASCII apostrophes and spaced tokens (e.g., n ’ t)
      - Normalizes to ASCII apostrophe for consistency
    """
    t = s or ""

    # 0) Normalize curly apostrophes to ASCII once, so rules below are simpler
    t = t.replace("’", "'")

    # 1) Fix spaced contractions like "I 'm", "you 're", "he 's", "we 'll", "they 'd", "we 've"
    t = re.sub(r"\b(I)\s+'m\b", r"\1'm", t)
    t = re.sub(
        r"\b(you|You|we|We|they|They|he|He|she|She|it|It|who|Who|there|There)\s+'re\b",
        r"\1're",
        t,
    )
    t = re.sub(r"\b(he|He|she|She|it|It|there|There|who|Who)\s+'s\b", r"\1's", t)
    t = re.sub(r"\b(I|you|we|they|he|she|it)\s+'ll\b", r"\1'll", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(I|you|we|they|he|she|it)\s+'d\b", r"\1'd", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(I|you|we|they|he|she|it)\s+'ve\b", r"\1've", t, flags=re.IGNORECASE)

    # 2) Collapse n ' t / n ’ t into n't (do this before attaching to the base word)
    t = re.sub(r"\bn\s*'\s*t\b", "n't", t, flags=re.IGNORECASE)

    # 3) Attach space+n't to the base verb: "do n't" → "don't", "are n't" → "aren't"
    t = re.sub(r"\b([A-Za-z]+)\s+n'?t\b", r"\1n't", t)

    # 4) Special cases: "wo n't" → "won't", "ca n't" → "can't"
    t = re.sub(r"\bwo\s+n'?t\b", "won't", t, flags=re.IGNORECASE)
    t = re.sub(r"\bca\s+n'?t\b", "can't", t, flags=re.IGNORECASE)

    # 5) Common misspelling: "hav n't" / "havn't" → "haven't"
    t = re.sub(r"\bhav\s*n'?t\b", "haven't", t, flags=re.IGNORECASE)

    # 6) Whitespace squeeze
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _precompute_norm_quotes(qmap):
    """Attach a cached normalized quote string to each .quotes row."""
    for row in qmap or []:
        raw = (row.get("quote") or row.get("text") or row.get("raw") or "").strip()
        row["_norm_quote"] = _norm_quote_text(_norm_unicode_quotes(raw))
    return qmap


def tokenize_name(n: str):
    return [tok for tok in re.split(r"[^\w']+", n) if tok]


def build_alias_map(canonicals):
    alias = {}
    for full in canonicals:
        full_n = normalize_name(full)
        if not full_n:
            continue
        parts = tokenize_name(full_n)
        if not parts:
            continue
        alias.setdefault(full_n, set()).add(full_n)
        if len(parts) >= 2:
            alias[full_n].add(parts[-1])  # last
            alias[full_n].add(parts[0])  # first
    inv = {}
    for root, names in alias.items():
        for n in names:
            inv[n.lower()] = root
    return inv


def _norm_quote_text(s: str) -> str:
    # normalize whitespace + curly quotes so quotes compare robustly
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", "", s)
    return s


# --- Tokenization gap fixes (add/keep needed spaces, tighten the rest) ---
_TOKEN_GAP_FIXES = [
    # ensure a space after a closing quote when followed by a letter
    (re.compile(r'([”"])([A-Za-z])'), r"\1 \2"),
    # ensure a space after sentence-final .?! when next token starts uppercase
    # (fixes: "...property.No" -> "...property. No")
    (re.compile(r"([.?!])([A-Z])"), r"\1 \2"),
    # glue curly apostrophes/contractions
    (re.compile(r"\s+’\s+"), "’"),
    (re.compile(r"\b([A-Za-z])\s+’\s+(t|s|d|ll|re|ve)\b", re.I), r"\1’\2"),
    # no space before punctuation / parens
    (re.compile(r"\s+([,.;:!?])"), r"\1"),
    (re.compile(r"([(\[\{])\s+"), r"\1"),
    (re.compile(r"\s+([)\]\}])"), r"\1"),
    # tighten stray spaces around quotes — but ONLY when the next char is punctuation
    # (this is the key change: it no longer kills the space we *just added* after closers)
    (re.compile(r'"\s+(?=[,.;:!?])'), '"'),
    (re.compile(r"”\s+(?=[,.;:!?])"), "”"),
    # space after an opening curly quote is never correct
    (re.compile(r"“\s+"), "“"),
    # kill space *before* any quote
    (re.compile(r'\s+"'), '"'),
]


def _fix_tokenization_gaps(t: str) -> str:
    s = t or ""
    for rx, rep in _TOKEN_GAP_FIXES:
        s = rx.sub(rep, s)
    return s


ADVERB_JUNK = {
    "softly",
    "simply",
    "firmly",
    "curiously",
    "quietly",
    "dryly",
    "gravely",
    "evenly",
    "slowly",
    "calmly",
    "sternly",
    "gently",
}

ADVERB_JUNK = {
    "softly",
    "simply",
    "firmly",
    "curiously",
    "quietly",
    "dryly",
    "gravely",
    "evenly",
    "slowly",
    "calmly",
    "sternly",
    "gently",
}


def _explicit_name_from_text(text: str, require_caps: bool = True, **_kw) -> str | None:
    """
    Mine a quoted string for an inline attribution like:
      "…," said Zack.   "Zack said …"   "…," murmured Mr. Chips.
      "…," said the guard.  -> Guard

    Args:
      text: quote text (may include trailing punctuation)
      require_caps: if True, only accept capitalized Name tokens (e.g., "John Smith").
                    If False, also allow role phrases like "the guard".
      **_kw: ignore any extra kwargs from older callers for compatibility.
    """
    t = (text or "").strip().strip('“”"').strip()
    if not t:
        return None

    # Use your global verb list pattern
    try:
        verbs_rx = _VERBS_RX
    except NameError:
        # fallback if symbol differs in this file
        try:
            verbs_rx = "(?:" + "|".join(_ATTRIB_VERBS) + ")"
        except Exception:
            verbs_rx = r"(?:said|asked|replied|whispered|shouted|cried|muttered|responded|told|answered|added|remarked|explained)"

    NAME_WORD_CAP = r"[A-Z][\w'\-]+"
    NAME_TAIL_CAP = rf"{NAME_WORD_CAP}(?:\s+{NAME_WORD_CAP}){{0,2}}"

    # When require_caps is False, allow lowercase role phrases like "the guard"
    # Also always try explicit guard patterns as a special-case.
    GUARD_TAIL = r"(?:the|a|an)\s+guard"

    # Patterns:
    tail_cap = re.search(
        rf"(?:[,–—\-]\s*)?(?P<verb>{verbs_rx})\s+(?P<who>{NAME_TAIL_CAP})\.?\s*$",
        t,
        flags=re.IGNORECASE,
    )
    head_cap = re.search(
        rf"^(?P<who>{NAME_TAIL_CAP})\s+(?P<verb>{verbs_rx})\b", t, flags=re.IGNORECASE
    )

    # Guard-specific (accept regardless of require_caps)
    tail_guard = re.search(
        rf"(?:[,–—\-]\s*)?(?P<verb>{verbs_rx})\s+(?P<who>{GUARD_TAIL})\b",
        t,
        flags=re.IGNORECASE,
    )
    head_guard = re.search(
        rf"^(?P<who>{GUARD_TAIL})\s+(?P<verb>{verbs_rx})\b", t, flags=re.IGNORECASE
    )

    m = tail_guard or head_guard
    if m:
        return "Guard"

    m = tail_cap or head_cap
    if not m and not require_caps:
        # A looser fallback when caps aren’t required: allow title-cased OR single lowercase role-ish token at head/tail
        NAME_WORD_LOOSE = r"[A-Za-z][\w'\-]+"
        NAME_TAIL_LOOSE = rf"{NAME_WORD_LOOSE}(?:\s+{NAME_WORD_LOOSE}){{0,2}}"
        m = re.search(
            rf"(?:[,–—\-]\s*)?(?P<verb>{verbs_rx})\s+(?P<who>{NAME_TAIL_LOOSE})\.?\s*$",
            t,
            flags=re.IGNORECASE,
        ) or re.search(
            rf"^(?P<who>{NAME_TAIL_LOOSE})\s+(?P<verb>{verbs_rx})\b",
            t,
            flags=re.IGNORECASE,
        )

    if not m:
        return None

    cand = m.group("who").strip()

    # Role canonicalization first (e.g., "the guard behind him" -> Guard)
    try:
        rc = _canonicalize_role(cand)
        if rc:
            return rc
    except NameError:
        pass

    # Sanitize & validate as a person name
    try:
        cand = _sanitize_person_name(cand) or None
    except NameError:
        # very conservative fallback: keep only capitalized tokens
        tokens = re.findall(r"[A-Z][A-Za-z'\-]+", cand)
        cand = " ".join(tokens) if tokens else None

    if not cand:
        return None

    # Final ban check
    try:
        if _is_banned(cand):
            return None
    except NameError:
        pass

    return cand


def _finalize_speakers(results):
    """
    Final pass over speakers for quoted lines:
      - Preserve 'UnknownA'/'UnknownB' placeholders (pair-alt).
      - Respect _lock_speaker (never overwrite).
      - Conservative self-mention guard: demote only if NOT vocative and NOT 1st-person.
      - Prefer exact full-name whitelist matches; otherwise clamp as before.
      - For ambiguous last-name matches (e.g., two Kings), leave as Unknown.
    """
    if not results:
        return results

    out = []
    alias_inv = globals().get("ALIAS_INV_CACHE", {}) or {}

    # index whitelist by first/last for quick hints
    first_idx = defaultdict(list)
    last_idx = defaultdict(list)
    for canon in CANON_WHITELIST or []:
        parts = normalize_name(canon).split()
        if parts:
            first_idx[parts[0].lower()].append(canon)
            last_idx[parts[-1].lower()].append(canon)

    def unique_from_whitelist(tok: str) -> str | None:
        cands = set(first_idx.get(tok, [])) | set(last_idx.get(tok, []))
        return next(iter(cands)) if len(cands) == 1 else None

    for r in results:
        txt = _norm_unicode_quotes(r.get("text") or "")
        
        # Apply normalize_name to detect descriptive speakers FIRST
        # This catches speakers like "A Police Dispatcher In...", but preserves "The Guard"
        sp = r.get("speaker", "Narrator")
        normalized_sp = normalize_name(sp)
        if normalized_sp == "Unknown" and sp not in ("Unknown", "UnknownA", "UnknownB"):
            sp = "Unknown"
            # Update the row dict so non-speech rows also get normalized
            r = dict(r)
            r["speaker"] = sp
        
        if not looks_like_direct_speech(txt):
            out.append(r)
            continue

        # Never override locked
        if r.get("_lock_speaker"):
            out.append({"speaker": sp, "text": txt})
            continue

        # Preserve placeholders
        if sp in ("UnknownA", "UnknownB"):
            out.append({"speaker": sp, "text": txt})
            continue

        # Self-mention guard
        if sp not in ("Unknown", "Narrator", None, ""):
            first_tok = sp.split()[0]
            if first_tok:
                name_rx = rf"\b{re.escape(first_tok)}\b"
                if re.search(name_rx, txt, flags=re.IGNORECASE):
                    is_vocative = (
                        re.search(rf"(^|\s)[“\"']?{name_rx},", txt, re.IGNORECASE)
                        or re.search(rf",\s{name_rx}[!?.,]", txt, re.IGNORECASE)
                        or re.search(rf"^\s*{name_rx}\s*[—-],", txt, re.IGNORECASE)
                    )
                    is_first_person = bool(re.search(r"\b(I|I'm|I’ve|I’d|I’ll)\b", txt))
                    if not is_vocative and not is_first_person:
                        log(f"[name-in-own-quote] drop '{sp}' | {txt[:60]}…")
                        sp = "Unknown"

        # Unknowns pass through
        if sp in ("Unknown", "Narrator", None, ""):
            out.append({"speaker": sp, "text": txt})
            continue

        # Prefer exact full-name whitelist match
        if CANON_WHITELIST and sp in CANON_WHITELIST:
            out.append({"speaker": sp, "text": txt})
            continue

        # Clamp or rescue
        clamped = _whitelist_clamp(sp) if CANON_WHITELIST else sp
        if CANON_WHITELIST and (clamped is None):
            meta_q = r.get("_qscore", None)
            meta_c = r.get("_cid", None)
            if (meta_q is not None and meta_q >= FINALIZE_TRUST_QSCORE) and (
                (meta_c in CJ_MAP)
                or (meta_c is not None and _cluster_is_named_enough(meta_c))
            ):
                out.append({"speaker": sp, "text": txt})
                continue

            toks = normalize_name(sp).split()
            if len(toks) == 1:
                low = toks[0].lower()
                if low in alias_inv:
                    out.append({"speaker": alias_inv[low], "text": txt})
                    continue
                uniq = unique_from_whitelist(low)
                if uniq:
                    out.append({"speaker": uniq, "text": txt})
                    continue
                # Ambiguous single-token → leave as Unknown instead of misassigning
                if len(set(first_idx.get(low, [])) | set(last_idx.get(low, []))) > 1:
                    log(f"[finalize-ambig] '{sp}' ambiguous ({txt[:60]}…) → Unknown")
                    out.append({"speaker": UNKNOWN_SPEAKER, "text": txt})
                    continue

            out.append({"speaker": UNKNOWN_SPEAKER, "text": txt})
        else:
            if CANON_WHITELIST and clamped != sp:
                log(f"[finalize-clamp] '{sp}' → '{clamped}' | {txt[:60]}…")
            out.append({"speaker": clamped or sp, "text": txt})

    return out


def _final_guard_no_narrator_quotes(rows):
    """
    If a row contains true quoted spans and is labeled Narrator (and not locked),
    split it into: Narrator(before) + Unknown(quote) + Narrator(after) ... for each span.
    Otherwise, keep the row as is.
    """
    if not rows:
        return rows

    out = []
    peeled_rows = 0

    for r in rows:
        rr = dict(r)
        txt = rr.get("text") or ""
        norm = _norm_unicode_quotes(txt)
        spans = _quote_spans(norm)

        # Only act when: has real spans, labeled Narrator, and not locked
        if spans and rr.get("speaker") == "Narrator" and not rr.get("_lock_speaker"):
            pos = 0
            for a, b in spans:
                # Narration before the quote
                if a > pos:
                    before = norm[pos:a].strip()
                    if before:
                        out.append(
                            {"speaker": "Narrator", "text": before, "is_quote": False}
                        )

                # The quote span itself
                qtxt = norm[a:b].strip()
                if qtxt:
                    out.append({"speaker": "Unknown", "text": qtxt, "is_quote": True})

                pos = b

            # Trailing narration after the last quote
            if pos < len(norm):
                after = norm[pos:].strip()
                if after:
                    out.append(
                        {"speaker": "Narrator", "text": after, "is_quote": False}
                    )

            peeled_rows += 1
            continue

        # Otherwise unchanged
        out.append(rr)

    try:
        DBG["final_guard_peeled_rows"] = (
            DBG.get("final_guard_peeled_rows", 0) + peeled_rows
        )
    except Exception:
        pass

    return out


def _assert_invariants(rows):
    bad_quote_narr = [
        i
        for i, r in enumerate(rows)
        if r.get("is_quote") and (r.get("speaker") == "Narrator")
    ]
    bad_flag = [
        i
        for i, r in enumerate(rows)
        if any(c in (r.get("text") or "") for c in ['"', "“", "”", "‘", "’"])
        and not r.get("is_quote")
    ]
    if bad_quote_narr:
        log(f"[invariant] quote rows labeled Narrator at idx={bad_quote_narr[:10]}…")
    if bad_flag:
        log(
            f"[invariant] rows contain quote chars but is_quote=False at idx={bad_flag[:10]}…"
        )
    return rows


# Globals to hold character json maps
CJ_MAP = {}  # id -> canonical/normalized name
CLUSTER_STATS = {}  # id -> {"count": int, "proper": int}


def _cluster_is_named_enough(cid, min_prop=0.50, min_mentions=3):
    """
    Decide if a character cluster looks 'named enough'.
    Robust to missing 'count'/'proper'/'quote'/'narr' keys.
    """
    s = CLUSTER_STATS.get(cid) or {}
    # coerce safely with defaults
    total = 0
    try:
        total = int(s.get("count", 0) or 0)
    except Exception:
        total = 0

    proper = 0
    try:
        proper = int(s.get("proper", 0) or 0)
    except Exception:
        proper = 0

    quote = 0
    try:
        quote = int(s.get("quote", 0) or 0)
    except Exception:
        quote = 0

    narr = 0
    try:
        narr = int(s.get("narr", 0) or 0)
    except Exception:
        narr = 0

    # if total is unknown, approximate from other signals
    if total <= 0:
        total = proper + quote + narr

    if total <= 0:
        return False

    prop = (proper / float(total)) if total else 0.0
    return (prop >= float(min_prop)) and (total >= int(min_mentions))


def _ensure_cluster_defaults():
    """
    Normalize CLUSTER_STATS so each cluster has all expected keys.
    Prevents KeyError: 'count' (and similar) later in the pipeline.
    """
    for cid, s in (CLUSTER_STATS or {}).items():
        if not isinstance(s, dict):
            CLUSTER_STATS[cid] = {"count": 0, "proper": 0, "quote": 0, "narr": 0}
            continue
        s.setdefault("count", 0)
        s.setdefault("proper", 0)
        s.setdefault("quote", 0)
        s.setdefault("narr", 0)


def _is_banned(name: str) -> bool:
    # canonicalized roles (e.g., Guard) are allowed
    if _canonicalize_role(name):
        return False
    n = normalize_name(name).lower()
    if n in BAN_SPEAKERS:
        return True
    n_compact = re.sub(r"[\s\-]+", "", n)
    # ban compacted "the..." role tokens too (e.g., "theguardbehindhim")
    if n.startswith("the "):
        return True
    if n.startswith("the") and " " not in (name or ""):
        return True
    return n_compact in BAN_SPEAKERS_NORM


def _is_pronounish(name: str) -> bool:
    return normalize_name(name).lower() in PRONOUN_BLACKLIST


def _is_subject_only_canonical(name: str) -> bool:
    """
    True if CLUSTER_STATS shows this canonical is 'subject-only': appears inside quotes
    (mentioned by others) but has ~no narration presence, so we should not use it as a speaker
    unless a prior step already locked it.
    """
    try:
        can = normalize_name(name).title()
        # Find cluster ids that map to this canonical
        cids = [cid for cid, nm in (CJ_MAP or {}).items() if nm == can]
        for cid in cids:
            st = (CLUSTER_STATS or {}).get(cid) or {}
            qm = int(st.get("quote", 0))
            nmv = int(st.get("narr", 0))
            if (qm >= 2) and (nmv <= 0):
                return True
    except Exception:
        pass
    return False


def _filter_subject_only_speakers(rows):
    """
    Demote subject-only canonicals from quote rows, unless they were explicitly locked
    (by head/tail/inline attribution). Prevents Liddy/Judy-like subjects from becoming speakers.
    """
    if not rows:
        return rows
    out = []
    for r in rows:
        rr = dict(r)
        t = rr.get("text") or ""
        is_q = looks_like_direct_speech(t)
        sp = rr.get("speaker")
        if (
            is_q
            and (not rr.get("_lock_speaker"))
            and sp
            and sp not in ("Unknown", "Narrator")
        ):
            if _is_subject_only_canonical(sp):
                rr["speaker"] = "Unknown"
        out.append(rr)
        log(
            f"[subject-only] demoted={sum(1 for r in out if r.get('_note')=='subject_only')}"
        )

    return out


def load_quotes_map(output_dir, prefix):
    import os

    # Prefer the raw BookNLP file (no extension), but allow common fallbacks
    candidates = [
        f"{prefix}.quotes",  # book_input.quotes  <-- primary
        f"{prefix}.quotes.txt",  # optional fallback
        f"{prefix}.quotes(edit).txt",  # optional fallback
        f"{prefix}.quotes(mod).txt",  # optional fallback (for sharing)
    ]
    qpath = None
    for name in candidates:
        p = os.path.join(output_dir, name)
        if os.path.exists(p):
            qpath = p
            break

    qmap = []
    if not qpath:
        try:
            log(
                f"[enlp-index] quotes file not found for prefix='{prefix}' in {output_dir}"
            )
        except Exception:
            pass
        return qmap

    try:
        log(f"[enlp-index] using quotes file: {os.path.basename(qpath)}")
    except Exception:
        pass

    with open(qpath, "r", encoding="utf-8", errors="replace") as f:
        header = f.readline()  # keep/discard; BookNLP writes a header line
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 7:
                # BookNLP columns: doc_id, sent_id, start, end, mention_phrase, char_id, quote, ...
                _, _, _, _, mention_phrase, char_id, quote = parts[:7]
                qmap.append(
                    {
                        "quote": (quote or "").strip(),
                        "char_id": (char_id or "").strip(),
                        "mention": (mention_phrase or "").strip(),
                    }
                )
    return qmap


# ---- ENLP bootstrap (reuse your existing load_quotes_map) --------------------
ENLP_CID2CANON = {}
ENLP_QUOTE_INDEX = (
    {}
)  # normed quote -> [ {"char_id": int|None, "mention_phrase": str, "quote": str} ]
ENLP_COREF_MAP = {}  # normalize_name(surface) -> cid (very conservative)


def _norm_quote_text(s: str) -> str:
    s = _norm_unicode_quotes(s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def _string_sim_score(a: str, b: str) -> float:
    try:
        import difflib

        return difflib.SequenceMatcher(None, a, b).ratio()
    except Exception:
        return 0.0


def _enlp_lookup_quote(text: str, min_ratio: float = 0.90):
    """
    Try exact normalization match; if none, fuzzy-match (ratio>=min_ratio).
    Returns (row, score) where row has at least {"char_id": ..., "quote": ..., "mention_phrase": ...}
    or (None, 0.0) if no candidate.
    """
    if not ENLP_QUOTE_INDEX:
        return (None, 0.0)
    key = _norm_quote_text(text)
    rows = ENLP_QUOTE_INDEX.get(key)
    if rows:
        # Prefer a row that actually has a char_id
        for r in rows:
            if r.get("char_id") is not None:
                return (r, 1.0)
        return (rows[0], 0.99)

    # fuzzy fallback
    best = None
    best_sc = 0.0
    for k, lst in ENLP_QUOTE_INDEX.items():
        sc = _string_sim_score(key, k)
        if sc >= min_ratio and sc > best_sc:
            # prefer row with a char_id
            cand = None
            for r in lst:
                if r.get("char_id") is not None:
                    cand = r
                    break
            best = cand or lst[0]
            best_sc = sc
    return (best, best_sc)


def bootstrap_enlp_caches(output_dir: str, prefix: str) -> None:
    """
    Populate ENLP_CID2CANON, ENLP_QUOTE_INDEX, ENLP_COREF_MAP from this run's outputs.
    Uses your existing load_quotes_map(), so it works whether the file is '.quotes' or '.quotes(edit).txt'.
    """
    global ENLP_CID2CANON, ENLP_QUOTE_INDEX, ENLP_COREF_MAP

    # 1) cid -> canonical (prefer characters_simple.json)
    ENLP_CID2CANON = {}
    for cand in (f"{prefix}.characters_simple.json", f"{prefix}.characters.json"):
        p = os.path.join(output_dir, cand)
        if os.path.exists(p):
            try:
                data = json.load(open(p, "r", encoding="utf-8"))
                for c in data.get("characters", []):
                    cid = c.get("char_id", c.get("id", c.get("cluster_id")))
                    try:
                        cid = int(cid)
                    except Exception:
                        cid = None
                    name = (
                        c.get("normalized_name")
                        or c.get("canonical_name")
                        or c.get("name")
                        or ""
                    ).strip()
                    if cid is not None and name:
                        ENLP_CID2CANON[cid] = name
            except Exception as e:
                log(f"[enlp/bootstrap] char load failed: {e}")
            break  # stop at first hit

    # 2) quote index + conservative coref map from mention phrases
    ENLP_QUOTE_INDEX = {}
    ENLP_COREF_MAP = {}
    qmap = load_quotes_map(output_dir, prefix) or []
    PRON_LIKE = {
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        "mine",
        "yours",
        "ours",
        "theirs",
    }
    for q in qmap:
        quote_txt = q.get("quote") or ""
        cid_str = q.get("char_id")
        try:
            cid = int(cid_str) if cid_str not in ("", None, "-1") else None
        except Exception:
            cid = None
        key = _norm_quote_text(quote_txt)
        ENLP_QUOTE_INDEX.setdefault(key, []).append(
            {
                "quote": quote_txt,
                "char_id": cid,
                "mention_phrase": q.get("mention") or "",
            }
        )
        # very conservative surface -> cid
        mention = (q.get("mention") or "").strip()
        if cid is not None and mention and mention.lower() not in PRON_LIKE:
            ENLP_COREF_MAP[normalize_name(mention)] = cid

    log(
        f"[enlp/bootstrap] quotes={sum(len(v) for v in ENLP_QUOTE_INDEX.values())} chars={len(ENLP_CID2CANON)} coref={len(ENLP_COREF_MAP)}"
    )


def _short(s: str | None, n: int = 60) -> str:
    """Log-safe snippet helper: strip newlines before f-strings."""
    return (s or "").replace("\n", " ").replace("\r", " ")[:n]


def _force_quotes_not_narrator(rows):
    """Normalize unicode quotes, and ensure quote rows never remain Narrator."""
    out = []
    for r in rows:
        t = _norm_unicode_quotes(r.get("text", "") or "")
        is_q = looks_like_direct_speech(t)

        rr = dict(r)
        rr["text"] = t
        # preserve existing True; otherwise adopt detected is_q
        prev_flag = rr.get("is_quote")
        rr["is_quote"] = (prev_flag if prev_flag is not None else is_q) or is_q

        if is_q and rr.get("speaker") == "Narrator":
            rr["speaker"] = "Unknown"
            snippet = _short(t, 60)
            log(f"[safety] quote-narrator→Unknown | {snippet}…")

        out.append(rr)
    return out


def _lock_when_explicit_agrees(rows):
    """If the text explicitly names the same speaker (e.g., '...,' said Morehouse),
    then lock that row's speaker to prevent later flips."""
    if not rows:
        return rows
    out = []
    for r in rows:
        rr = dict(r)
        sp = rr.get("speaker")
        txt = rr.get("text") or ""
        if (
            sp
            and sp not in ("Unknown", "Narrator")
            and _explicit_matches_speaker(txt, sp)
        ):
            rr["_lock_speaker"] = True
            rr["_locked_to"] = sp
            rr["_lock_reason"] = "explicit_name_agreement"
        out.append(rr)
    return out


# --- Fuzzy matching for quotes ---
def _norm_aggressive(s: str) -> str:
    # lowercase, normalize quotes/apostrophes, strip spaces & punctuation (keep letters/digits and apostrophes)
    s = s.lower()
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^a-z0-9']", "", s)
    return s


def _shingle_overlap(a: str, b: str, k: int = 12) -> float:
    # percent of b's k-length substrings found in a
    if not a or not b:
        return 0.0
    if len(b) <= k:
        return 1.0 if b in a else 0.0
    sb = {b[i : i + k] for i in range(0, len(b) - k + 1)}
    hit = sum(1 for sh in sb if sh in a)
    return hit / max(1, len(sb))


def _best_quote_for_text(text: str, qmap, k: int = 12, min_ratio: float = 0.70):
    """
    Pick the .quotes row whose text best matches this line (fuzzy).
    Returns (row, score) or (None, 0.0).
    """
    a = _norm_aggressive(_norm_unicode_quotes(text))
    best, best_score = None, 0.0
    for q in qmap or []:
        qtxt = q.get("_norm_quote") or _norm_unicode_quotes(q.get("quote", ""))
        if not qtxt:
            continue
        b = _norm_aggressive(qtxt)
        if not b:
            continue
        score = 1.0 if b in a else _shingle_overlap(a, b, k=k)
        if score > best_score:
            best_score, best = score, q
    return (best, best_score) if best and best_score >= min_ratio else (None, 0.0)


def _lock_speaker(row: dict, reason: str = "attrib") -> None:
    """
    Mark this row's speaker as immutable for downstream heuristics.
    We also store the exact target ('_locked_to') so we can restore it later
    even if a heuristic overwrote it.
    """
    if not row:
        return
    row["_lock_speaker"] = True
    row["_locked_to"] = row.get("speaker")
    row["_lock_reason"] = reason


def _is_locked(row: dict) -> bool:
    return bool(row.get("_lock_speaker"))


def reassign_from_quotes(text, qmap, alias_inv):
    """
    Use .quotes to infer a speaker for a quoted line.
    Returns canonical speaker string or None.
    """
    t = (text or "").strip()
    if not t or not qmap:
        return None

    # micro quotes get a lower threshold
    tok_count = len(re.findall(r"[A-Za-z0-9']+", t))
    thr = 0.35 if tok_count <= 3 else 0.70

    qrow, score = _best_quote_for_text(t, qmap, k=12, min_ratio=thr)
    if not qrow:
        # STRICT explicit fallback: must whitelist/alias-resolve
        explicit = _explicit_name_from_text(t, require_caps=True)
        if explicit and not _is_banned(explicit):
            clamped = _whitelist_clamp(explicit)
            if clamped and not _is_banned(clamped):
                log(f"[explicit.strict] '{explicit}' -> '{clamped}' | {t[:80]}…")
                return clamped
        return None

    # sanitize → alias-correct → canonicalize-role → whitelist; optionally *require* resolution
    def canon(label: str, *, require_resolve: bool = False) -> str | None:
        raw = _sanitize_person_name(label) or ""
        if not raw:
            return None
        aliased = _alias_correct(raw, alias_inv or {})
        role_or = _canonicalize_role(aliased or raw) or (aliased or raw)
        clamped = _whitelist_clamp(role_or)
        out = clamped or role_or
        if not out or _is_banned(out) or _is_pronounish(out):
            return None
        # if require_resolve, insist whitelist/alias actually validated it
        if (
            require_resolve
            and (clamped is None)
            and (aliased is None or aliased == raw)
        ):
            return None
        return out

    # 1) Prefer cluster canonical when char_id is numeric
    cid_raw = (
        qrow.get("char_id")
        or qrow.get("character_id")
        or qrow.get("charid")
        or qrow.get("cid")
        or ""
    ).strip()
    if cid_raw and re.fullmatch(r"-?\d+", cid_raw):
        icid = int(cid_raw)
        can = CJ_MAP.get(icid)
        if can and (_cluster_is_named_enough(icid) or _canonicalize_role(can)):
            label = canon(can)
            if label:
                log(
                    f"[quote-charid] id={cid_raw} ({score:.2f}) -> '{label}' | {t[:80]}…"
                )
                return label

    # 2) Canonical-ish fields
    for f in [
        "canonical_name",
        "char_name",
        "character",
        "character_name",
        "name",
        "speaker",
        "entity",
    ]:
        if f in qrow:
            raw = (qrow.get(f) or "").strip()
            if raw:
                label = canon(normalize_name(raw))
                if label:
                    log(f"[quote-{f}] {score:.2f} -> '{label}' | {t[:80]}…")
                    return label

    # 3) STRICT mention: accept only if alias/whitelist truly resolves it
    mention_raw = (qrow.get("mention") or "").strip()
    if mention_raw:
        mnorm = normalize_name(mention_raw).strip()
        if mnorm and not _is_pronounish(mnorm) and not _is_banned(mnorm):
            label = canon(mnorm, require_resolve=True)
            if label:
                log(f"[quote-mention] {score:.2f} -> '{label}' | {t[:80]}…")
                return label

    # 4) Very late: explicit inside the quote (strict)
    explicit = _explicit_name_from_text(t, require_caps=True)
    if explicit and not _is_banned(explicit):
        label = canon(explicit, require_resolve=True)
        if label:
            log(f"[explicit] '{explicit}' -> '{label}' | {t[:80]}…")
            return label

    return None


def is_junk_line(text: str) -> bool:
    """Heuristic to filter junk or non-dialogue fragments."""
    words = text.split()
    if len(words) == 0:
        return True
    if len(words) == 1 and text.lower() not in SHORT_DIALOGUE:
        return True
    if len(words) <= 2 and all(len(w) <= 2 for w in words):
        return True
    return False


def _rebalance_quote_bursts(results):
    """
    For runs of consecutive quoted segments, enforce two-party alternation only when SAFE.
    Never overwrite an attribution-LOCKED or high-confidence row.
    Guards:
      - Do not override at a visual turn boundary (…”  “…”).
      - Do not override across RID gaps (>1) when both rows carry numeric _rid.
    """
    if not results:
        return results

    def is_attrib_narr(r):
        try:
            return (r.get("speaker") == "Narrator") and _ATTRIB_LINE_RX.match(
                (r.get("text") or "").strip()
            )
        except Exception:
            return False

    def _norm(s):
        try:
            return _norm_unicode_quotes(s or "")
        except Exception:
            return s or ""

    def _starts_with_opener(s):
        return bool(re.match(r'^\s*["“«]', _norm(s)))

    def _ends_with_closer(s):
        return bool(re.search(r'["”»]\s*$', _norm(s)))

    def _rid_num(r):
        rid = r.get("_rid")
        if rid is None:
            return None
        m = re.search(r"(\d+)", str(rid))
        return int(m.group(1)) if m else None

    out = [dict(r) for r in results]
    n = len(out)
    i = 0
    while i < n:
        if not looks_like_direct_speech(out[i]["text"]):
            i += 1
            continue

        j = i
        while j + 1 < n and (
            looks_like_direct_speech(out[j + 1]["text"]) or is_attrib_narr(out[j + 1])
        ):
            j += 1

        qidx = [k for k in range(i, j + 1) if looks_like_direct_speech(out[k]["text"])]
        if len(qidx) >= 3:
            known = []
            for k in qidx:
                sp = out[k]["speaker"]
                if sp not in ("Narrator", "Unknown") and (not known or known[-1] != sp):
                    known.append(sp)

            anchors = []
            if len(known) >= 2:
                anchors = known[:2]
            else:
                prev_sp = next(
                    (
                        out[t]["speaker"]
                        for t in range(i - 1, -1, -1)
                        if looks_like_direct_speech(out[t]["text"])
                        and out[t]["speaker"] not in ("Narrator", "Unknown")
                    ),
                    None,
                )
                next_sp = next(
                    (
                        out[t]["speaker"]
                        for t in range(j + 1, n)
                        if looks_like_direct_speech(out[t]["text"])
                        and out[t]["speaker"] not in ("Narrator", "Unknown")
                    ),
                    None,
                )
                anchors = [
                    a
                    for a in (prev_sp, next_sp)
                    if a and a not in ("Narrator", "Unknown")
                ]
                anchors = anchors[:2]

            if len(anchors) == 2 and anchors[0] != anchors[1]:
                a, b = anchors
                for pos, k in enumerate(qidx):
                    expect = a if (pos % 2 == 0) else b
                    sp = out[k]["speaker"]

                    # strong guards
                    if out[k].get("_lock_speaker"):
                        continue
                    if (
                        out[k].get("_cid") is not None
                        or float(out[k].get("_qscore", 0.0) or 0.0) >= 0.80
                    ):
                        continue
                    # visual turn boundary with previous quote in this run
                    if pos > 0:
                        pk = qidx[pos - 1]
                        if _ends_with_closer(out[pk]["text"]) and _starts_with_opener(
                            out[k]["text"]
                        ):
                            continue
                        # RID gap with previous quote
                        rpk = _rid_num(out[pk])
                        rk = _rid_num(out[k])
                        if rpk is not None and rk is not None and abs(rk - rpk) > 1:
                            continue

                    if sp in ("Narrator", "Unknown") or sp not in (a, b):
                        out[k]["speaker"] = expect
                        try:
                            log(
                                f"[burst] set '{expect}' in quote-burst | {out[k]['text'][:60]}…"
                            )
                        except Exception:
                            pass

        i = j + 1

    return out


def _strip_internal_tags(rows):
    for r in rows:
        r.pop("_lock_speaker", None)
        r.pop("_lock_reason", None)
    return rows


def _drop_empty_quote_rows(rows):
    """
    Remove rows that are 'quotes' but contain no real content (e.g., just "" or punctuation).
    """
    out = []
    for r in rows:
        t = (r.get("text") or "").strip()
        if looks_like_direct_speech(t):
            core = t.strip(" \"'“”‘’").strip()
            # Allow “…” or “—” to pass (not empty), but drop empty shells
            if not core or not re.search(r"[A-Za-z0-9]", core):
                log(f"[clean] drop empty quote row | {t[:60]}…")
                continue
        out.append(r)
    return out


def _coref_pronoun_fill(results, enlp_coref_map):
    """
    For quoted rows with Narrator/Unknown, scan for any surface -> cid hits.
    Prefer unique hit within the row. Assign canonical speaker when unique.
    """
    if not enlp_coref_map:
        return results
    out = []
    for row in results:
        sp = row.get("speaker") or "Narrator"
        txt = row.get("text") or ""
        if row.get("is_quote") and sp in ("Narrator", "Unknown"):
            hits = [cid for surf, cid in enlp_coref_map.items() if surf in txt]
            uniq = list(set(hits))
            if len(uniq) == 1:
                cid = uniq[0]
                if ("ENLP_CID2CANON" in globals()) and (cid in ENLP_CID2CANON):
                    row["speaker"] = ENLP_CID2CANON[cid]
                    row["_cid"] = cid
                    row["_lock_speaker"] = True
                    row["_lock_reason"] = "coref_fill"
        out.append(row)
    return out


def _merge_speakers(results):
    """
    Post-pass to merge 'King' -> 'Steve King' and 'Charlie' -> 'Mike Jones' etc.,
    preferring the longest multi-token variant observed in the run.
    """
    counts = Counter(r["speaker"] for r in results)
    multi_by_last = defaultdict(Counter)  # last -> Counter(full)
    multi_by_first = defaultdict(Counter)  # first -> Counter(full)

    speakers = set(counts.keys())
    for s in speakers:
        parts = s.split()
        if len(parts) >= 2:
            first, last = parts[0], parts[-1]
            multi_by_last[last.lower()][s] += counts[s]
            multi_by_first[first.lower()][s] += counts[s]

    mapping = {}
    for s in speakers:
        parts = s.split()
        if len(parts) == 1:
            tok = parts[0].lower()
            if tok in multi_by_last and multi_by_last[tok]:
                target, _ = max(
                    multi_by_last[tok].items(), key=lambda kv: (kv[1], len(kv[0]))
                )
                mapping[s] = target
                continue
            if tok in multi_by_first and multi_by_first[tok]:
                target, _ = max(
                    multi_by_first[tok].items(), key=lambda kv: (kv[1], len(kv[0]))
                )
                mapping[s] = target

    if mapping:
        for k, v in mapping.items():
            if k != v:
                log(f"[merge] '{k}' → '{v}'")

    merged = []
    for r in results:
        sp = r["speaker"]
        sp2 = mapping.get(sp, sp)
        merged.append({"speaker": sp2, "text": r["text"]})
    return merged


def _explicit_matches_speaker(text, speaker):
    """Check if the explicit attribution regex pulls the same name as the assigned speaker."""
    ex = _explicit_name_from_text(text or "")
    if not ex or not speaker:
        return False
    # loose compare: either exact or shares first/last token
    sp = normalize_name(speaker).split()
    ex_p = normalize_name(ex).split()
    return (normalize_name(ex) == normalize_name(speaker)) or (
        sp and ex_p and (sp[0] == ex_p[0] or sp[-1] == ex_p[-1])
    )


def _speaker_from_attrib_fragment(text: str) -> str | None:
    """
    Extract a likely speaker name from an attribution/action fragment ONLY.
    Pure, no calls to _extract_attrib_head_tail to avoid recursion.
    """
    if not text:
        return None
    t = (text or "").strip()
    if len(t) < 3:
        return None
    # early junk guard (avoids logging 'And', 'Well', etc.)
    if re.match(r"^(and|but|so|then|well|yes|no)\b", t.strip(), flags=re.I):
        return None
    # Quick reject if it contains obvious quote characters – leave to quote parser
    if any(q in t for q in ('"', "\u201c", "\u201d", "\u2018", "\u2019")):
        return None

    name_rx = (
        _NAME_COLON_RX
        if "_NAME_COLON_RX" in globals()
        else r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}"
    )
    verbs = (
        _ATTRIB_VERBS
        if "_ATTRIB_VERBS" in globals()
        else r"(said|asked|replied|agreed|whispered|murmured|shouted|cried|yelled|called|continued|added)"
    )
    rx_tail_verb_name = re.compile(
        rf".*\b(?:{verbs})\s+({name_rx})\s*\.?\s*$", re.IGNORECASE
    )
    rx_tail_name_verb = re.compile(
        rf".*,\s*({name_rx})\s+(?:{verbs})\s*\.?\s*$", re.IGNORECASE
    )
    rx_head_verb_name = re.compile(
        rf"^\s*(?:{verbs})\s+({name_rx})\b.*$", re.IGNORECASE
    )

    m = (
        rx_tail_verb_name.match(t)
        or rx_tail_name_verb.match(t)
        or rx_head_verb_name.match(t)
    )
    if not m:
        return None

    who_raw = _collapse_to_name_tail(m.group(1)) or m.group(1)
    who = _sanitize_person_name(who_raw) or ""
    if not who:
        return None

    STOP = {
        "and",
        "but",
        "so",
        "then",
        "well",
        "yes",
        "no",
        "old",
        "young",
        "dear",
        "sir",
        "maam",
        "ma’am",
        "boy",
        "girl",
        "man",
        "woman",
        "kid",
        "guys",
        "boys",
        "girls",
        "folks",
        "we",
        "they",
        "you",
        "i",
    }
    tokens = who.split()
    if (
        (len(tokens) == 1 and tokens[0].lower() in STOP)
        or len(tokens) > 3
        or len(who) > 40
    ):
        return None
    if _is_banned(who):
        return None
    if len(tokens) == 1 and not tokens[0][0].isupper():
        return None

    return who


def _speaker_verb_from_attrib_fragment(text: str, alias_inv: dict | None = None):
    """
    Like _speaker_from_attrib_fragment, but stays robust even if that helper
    returns only a name (older impls). Always returns (who, verb) or (None, None).
    """
    _ensure_attrib_fragment_regexes()

    t = (text or "").strip()
    if not t:
        return (None, None)

    # Gate with your detector if present
    try:
        if "_looks_like_attribution_fragment" in globals():
            if not _looks_like_attribution_fragment(t):
                return (None, None)
    except Exception:
        pass

    # Prefer your existing helper first
    who_only, verb_only = None, None
    try:
        res = _speaker_from_attrib_fragment(t, alias_inv=alias_inv)
        if isinstance(res, tuple):
            who_only, verb_only = res
        else:
            who_only, verb_only = res, None
    except Exception:
        pass

    # Then parse with the shared AF regexes
    try:
        m = _AF_VERB_NAME_RX.match(t) or _AF_NAME_VERB_RX.match(t)
    except Exception:
        m = None

    if not m:
        return (who_only, verb_only) if who_only else (None, None)

    who = (m.group("who") or "").strip()
    verb = (m.group("verb") or "").strip().lower()

    if who_only:
        who = who_only

    # Normalize and alias-correct the name
    try:
        who = normalize_name(who).title()
    except Exception:
        who = who.title() if who else who

    if alias_inv and "_alias_correct" in globals():
        try:
            who = _alias_correct(who, alias_inv or {})
        except Exception:
            pass

    # Basic stopword / sanity checks for spurious "names"
    STOP = {
        "and",
        "but",
        "so",
        "then",
        "well",
        "yes",
        "no",
        "old",
        "young",
        "dear",
        "sir",
        "maam",
        "ma’am",
        "boy",
        "girl",
        "man",
        "woman",
        "kid",
        "guys",
        "boys",
        "girls",
        "folks",
        "we",
        "they",
        "you",
        "i",
    }
    toks = who.split() if who else []
    if (
        (not who)
        or (len(toks) == 1 and toks[0].lower() in STOP)
        or len(toks) > 3
        or len(who) > 40
    ):
        return (None, None)

    # Debug/logging (best-effort)
    try:
        DBG["attrib_frag_hits"] = DBG.get("attrib_frag_hits", 0) + 1
    except Exception:
        pass
    try:
        log(f"[attrib-frag] who='{who}' verb='{verb or ''}' | {t[:80]}…")
    except Exception:
        pass

    return (who, verb or None)


def _extract_attrib_head_tail(s: str):
    """
    Detect attribution HEAD/TAIL inside a narrator fragment without calling any other
    extraction functions (no recursion). Returns a tuple:
        (kind, who_raw, a_lo, a_hi)
    where kind ∈ {'head','tail_verb_name','tail_name_verb'} or None,
    who_raw is the raw name string (un-sanitized), and a_lo/a_hi are the span
    indices of the name match in the string.
    """
    if not s:
        return None, None, None, None

    txt = s.strip()
    if not txt:
        return None, None, None, None

    # Quick reject if it contains obvious quote characters – leave to quote parser
    if any(q in txt for q in ('"', "\u201c", "\u201d", "\u2018", "\u2019")):
        return None, None, None, None

    # Use your globals
    name_rx = (
        _NAME_COLON_RX
        if "_NAME_COLON_RX" in globals()
        else r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}"
    )
    verbs = (
        _ATTRIB_VERBS
        if "_ATTRIB_VERBS" in globals()
        else r"(said|asked|replied|agreed|whispered|murmured|shouted|cried|yelled|called|continued|added)"
    )

    # Patterns
    rx_head_verb_name = re.compile(
        rf"^\s*(?:{verbs})\s+({name_rx})\b.*$", re.IGNORECASE
    )
    rx_tail_verb_name = re.compile(
        rf".*\b(?:{verbs})\s+({name_rx})\s*\.?\s*$", re.IGNORECASE
    )
    rx_tail_name_verb = re.compile(
        rf".*,\s*({name_rx})\s+(?:{verbs})\s*\.?\s*$", re.IGNORECASE
    )

    m = rx_head_verb_name.match(txt)
    if m:
        who_raw = _collapse_to_name_tail(m.group(1)) or m.group(1)
        span = m.span(1)
        return "head", who_raw, span[0], span[1]

    m = rx_tail_verb_name.match(txt)
    if m:
        who_raw = _collapse_to_name_tail(m.group(1)) or m.group(1)
        span = m.span(1)
        return "tail_verb_name", who_raw, span[0], span[1]

    m = rx_tail_name_verb.match(txt)
    if m:
        who_raw = _collapse_to_name_tail(m.group(1)) or m.group(1)
        span = m.span(1)
        return "tail_name_verb", who_raw, span[0], span[1]

    return None, None, None, None


# Titles/honorifics that may prefix a name (optional)
_TITLES = r"(?:Mr\.|Mrs\.|Ms\.|Miss|Dr\.|Prof\.|Sir|Madam|Madame|Lady|Lord|Capt\.|Captain|Lt\.|Lieut\.|Sgt\.|Gen\.|Colonel|Col\.)"

# A proper-cased personal name, allowing 1–3 tokens, internal dots/hyphens allowed
_NAME_CORE = r"[A-Z][a-zA-Z'\.-]+(?:\s+[A-Z][a-zA-Z'\.-]+){0,2}"

# Name with optional title (e.g., "Mr. King", "Dr. Exstrom", "Captain John Smith")
_NAME_CAP = rf"(?:{_TITLES}\s+)?{_NAME_CORE}"

# Rich dialogue verb inventory (past/present commonly used in narration)
# (Keep set relatively tight to avoid false positives; expand cautiously.)
_SPEECH_VERBS_SET = {
    # core
    "say",
    "says",
    "said",
    "ask",
    "asks",
    "asked",
    "tell",
    "tells",
    "told",
    "reply",
    "replies",
    "replied",
    "answer",
    "answers",
    "answered",
    "respond",
    "responds",
    "responded",
    "continue",
    "continues",
    "continued",
    "add",
    "adds",
    "added",
    "state",
    "states",
    "stated",
    "note",
    "notes",
    "noted",
    "remark",
    "remarks",
    "remarked",
    "observe",
    "observes",
    "observed",
    "explain",
    "explains",
    "explained",
    "announce",
    "announces",
    "announced",
    # tone/color
    "gasp",
    "gasps",
    "gasped",
    "breathe",
    "breathes",
    "breathed",
    "hiss",
    "hisses",
    "hissed",
    "roar",
    "roars",
    "roared",
    "bark",
    "barks",
    "barked",
    "bellow",
    "bellows",
    "bellowed",
    "protest",
    "protests",
    "protested",
    "agree",
    "agrees",
    "agreed",
    "insist",
    "insists",
    "insisted",
    "concede",
    "concedes",
    "conceded",
    "counter",
    "counters",
    "countered",
    "retort",
    "retorts",
    "retorted",
    "interject",
    "interjects",
    "interjected",
    "murmur",
    "murmurs",
    "murmured",
    "mutter",
    "mutters",
    "muttered",
    "whisper",
    "whispers",
    "whispered",
    "shout",
    "shouts",
    "shouted",
    "yell",
    "yells",
    "yelled",
    "cry",
    "cries",
    "cried",
    "snap",
    "snaps",
    "snapped",
    "growl",
    "growls",
    "growled",
    "grunt",
    "grunts",
    "grunted",
    "sigh",
    "sighs",
    "sighed",
    "whine",
    "whines",
    "whined",
    "scoff",
    "scoffs",
    "scoffed",
    "sneer",
    "sneers",
    "sneered",
    "chuckle",
    "chuckles",
    "chuckled",
    "laugh",
    "laughs",
    "laughed",
    "muse",
    "muses",
    "mused",
    "intoned",
    "urge",
    "urges",
    "urged",
    "warn",
    "warns",
    "warned",
    "order",
    "orders",
    "ordered",
    "demand",
    "demands",
    "demanded",
    "plead",
    "pleads",
    "pleaded",
    "beg",
    "begs",
    "begged",
    "promise",
    "promises",
    "promised",
}

# Build the regex alternation once (sorted for deterministic pattern)
_INLINED_ATTRIB_VERBS = "|".join(sorted(_SPEECH_VERBS_SET))

# Optional adverb(s) we allow between verb/name to keep precision (<=2 “-ly” or whitelisted adverbs)
_ADVERB_GAP = r"(?:\s+(?:\w+ly|softly|quietly|calmly|firmly|gently|slowly|dryly|coldly|sharply|evenly|lightly|boldly)){0,2}"

# Pattern A: Verb + (adverbs) + Name   → "gasped King", "said softly Mr. King"
#   group(1) = verb, group(2) = name
_RX_INLINE_VN = re.compile(
    rf"\b((?:{_INLINED_ATTRIB_VERBS}))\b{_ADVERB_GAP}\s+({_NAME_CAP})\b", re.IGNORECASE
)

# Pattern B: Name + (adverbs) + Verb   → "King gasped", "Mr. King said softly"
#   group(1) = name, group(2) = verb
_RX_INLINE_NV = re.compile(
    rf"\b({_NAME_CAP})\b{_ADVERB_GAP}\s+((?:{_INLINED_ATTRIB_VERBS}))\b", re.IGNORECASE
)

# Direction hinting:
# Keep a small NEXT list for cases that genuinely lead into the following line.
# If unsure, default to PREV (most printed English uses “..., VERB Name” to refer to the quote that just ended).
_NEXT_VERBS = {
    "responded",
    "responds",
    "continue",
    "continues",
    "continued",
    "add",
    "adds",
    "added",
    # expand only if tests show genuine ‘lead-in to next quote’ behavior
}


def _maybe_disambiguate_surname(
    who: str, rows_for_context, context_idx: int, window: int = ADDRESS_WINDOW
) -> str:
    """
    If 'who' is a single-token surname, try to resolve to a canonical full name
    using recent dialog context. Else return 'who' unchanged.
    """
    if not who or " " in who:
        return who
    last_low = who.lower()
    resolved = _resolve_surname_by_context(
        last_low, rows_for_context, context_idx, window=window
    )
    return resolved or who


def _sanitize_candidate_name(who: str, alias_inv, rows, idx_for_context: int) -> str:
    """
    Clean/canonicalize a speaker name and resolve single-surname by nearby context.
    Returns "" if the candidate should be discarded.
    """
    import re

    if not who:
        return ""

    # 1) clean raw (use global sanitizer if available; else minimal fallback)
    try:
        func = globals().get("_sanitize_person_name")
        if callable(func):
            who = func(who) or ""
        else:
            # minimal fallback: strip possessive and keep up to First Last
            s = re.sub(r"\b['’]s\b", "", who).strip()
            toks = re.findall(r"[A-Z][A-Za-z'’\-]+", s)
            who = " ".join(toks[:2]) if toks else ""
    except Exception:
        # fallback if sanitizer explodes
        s = re.sub(r"\b['’]s\b", "", who).strip()
        toks = re.findall(r"[A-Z][A-Za-z'’\-]+", s)
        who = " ".join(toks[:2]) if toks else ""

    # 2) canonicalize via alias/context
    try:
        if "_canonicalize_who_ctx" in globals():
            who2 = _canonicalize_who_ctx(who, alias_inv, rows, idx_for_context) or who
            who = who2
        elif alias_inv:
            who = alias_inv.get(who.lower(), who)
    except Exception:
        pass

    # 3) disambiguate surnames by nearby speaking context
    try:
        if " " not in who and "_resolve_surname_by_context" in globals():
            who2 = _resolve_surname_by_context(
                who.lower(), rows, idx_for_context, window=8
            )
            if who2:
                who = who2
    except Exception:
        pass

    # 4) sanity
    if len(who) > 40 or len(who.split()) > 3:
        return ""
    return who


def attach_action_fragments(results, alias_inv):
    """
    Attach narrator attributions to the nearest quote and LOCK that quote's speaker.

    Supported:
      - Head attribution → *next* quote
      - Tail attribution → *previous* quote
      - In-line attribution anywhere in narrator text (e.g., "..., said Johnson." / "Johnson asked ...")
        → direction depends on verb; past-tense verbs default to *previous*.

    Never overwrite a strong existing speaker (only Unknown/Narrator, or matching).
    KEEP_ATTRIB_TEXT / ATTACH_ATTRIB_TO_QUOTE respected.

    Notes:
      - Applies a possessive-kinship guard and name cleaner so junk like "Zack’s Father"
        or environment names don’t get promoted to speakers.
    """
    if not results:
        return results

    out = []
    n = len(results)

    def nearest_quote_index_fwd(start_idx):
        for j in range(start_idx + 1, n):
            if _is_quote_row_strict(results[j]):
                return j
        return None

    def nearest_quote_index_back(start_idx):
        for j in range(start_idx - 1, -1, -1):
            if _is_quote_row_strict(results[j]):
                return j
        return None

    def _clean_name_safe(raw: str) -> str:
        """
        Use global _sanitize_person_name _is_possessive_kinship if available.
        Fallback: strip "'s" and keep up to First Last tokens only.
        """
        s = (raw or "").strip()
        try:
            if "_is_possessive_kinship" in globals() and _is_possessive_kinship(s):
                return ""
        except Exception:
            pass
        func = globals().get("_sanitize_person_name")
        if callable(func):
            try:
                return func(s) or ""
            except Exception:
                pass
        # fallback minimal cleaner
        import re

        s = re.sub(r"\b['’]s\b", "", s).strip()
        toks = __import__("re").findall(r"[A-Z][A-Za-z'’\-]+", s)
        return " ".join(toks[:2]) if toks else ""

    def _canon_alias_safe(name: str) -> str:
        if not name:
            return ""
        # Prefer project’s alias/canonicalization helpers if present
        try:
            if "_alias_correct" in globals():
                return _alias_correct(name, alias_inv or {}) or name
        except Exception:
            pass
        # light fallback: alias_inv direct hit on lowercase
        try:
            if alias_inv:
                return alias_inv.get(name.lower(), name)
        except Exception:
            pass
        return name

    def candidate_from_fragment(txt: str) -> str | None:
        """
        Pull a speaker candidate from an attribution fragment and sanitize it.
        """
        who = None
        # 1) Prefer robust (who, verb) helper if available
        if "_speaker_verb_from_attrib_fragment" in globals():
            try:
                w, _v = _speaker_verb_from_attrib_fragment(txt, alias_inv)
                who = w or None
            except Exception:
                who = None
        # 2) Fallback to basic helper
        if not who and "_speaker_from_attrib_fragment" in globals():
            try:
                res = _speaker_from_attrib_fragment(txt)
                who = res[0] if isinstance(res, tuple) else res
            except Exception:
                who = None
        if not who:
            return None

        # 3) Clean / guard (possessive-kinship, environment caps, clamp to First Last)
        who = _clean_name_safe(who)
        if not who:
            return None

        # 4) Canonicalize via alias mapping/context
        who = _canon_alias_safe(who)
        if not who:
            return None

        # 5) Final sanity: short and human-ish
        try:
            STOP = {
                "and",
                "but",
                "so",
                "then",
                "well",
                "yes",
                "no",
                "old",
                "young",
                "dear",
                "sir",
                "maam",
                "ma’am",
                "boy",
                "girl",
                "man",
                "woman",
                "kid",
                "guys",
                "boys",
                "girls",
                "folks",
                "we",
                "they",
                "you",
                "i",
            }
            toks = who.split()
            if (
                (len(toks) == 1 and toks[0].lower() in STOP)
                or len(toks) > 3
                or len(who) > 40
            ):
                return None
        except Exception:
            pass
        return who

    for i, r in enumerate(results):
        txt = (r.get("text") or "").strip()
        is_q = looks_like_direct_speech(txt)
        if is_q:
            out.append(dict(r))
            continue

        # only narrator lines can be pure attribution fragments
        sp = r.get("speaker") or "Narrator"
        if sp != "Narrator":
            out.append(dict(r))
            continue

        # detect attribution-looking fragments (short tails/heads like “— said Zack.”)
        if not _ATTRIB_LINE_RX.match(txt or ""):
            out.append(dict(r))
            continue

        who = candidate_from_fragment(txt)
        if not who:
            out.append(dict(r))
            continue

        # Decide direction: if it 'said/asked' after content, attach to previous quote,
        # if it's a head like "Smith said," attach to next quote.
        direction = "prev"
        if _ATTRIB_HEAD.match(txt or "") or _NAME_COLON_RX.match(txt or ""):
            direction = "next"

        j = (
            nearest_quote_index_back(i)
            if direction == "prev"
            else nearest_quote_index_fwd(i)
        )
        if j is None:
            out.append(dict(r))
            continue

        # sanitize/canonicalize candidate now that j (context index) is known
        try:
            who_clean = (
                _sanitize_person_name(who)
                if "_sanitize_person_name" in globals()
                else _clean_name_safe(who)
            )
        except Exception:
            who_clean = _clean_name_safe(who)

        try:
            if "_canonicalize_who_ctx" in globals():
                who_final = (
                    _canonicalize_who_ctx(who_clean, alias_inv, results, j) or who_clean
                )
            else:
                who_final = (
                    alias_inv.get(who_clean.lower(), who_clean)
                    if alias_inv
                    else who_clean
                )
        except Exception:
            who_final = who_clean

        if " " not in who_final and "_resolve_surname_by_context" in globals():
            try:
                who_ctx = _resolve_surname_by_context(
                    who_final.lower(), results, j, window=8
                )
                if who_ctx:
                    who_final = who_ctx
            except Exception:
                pass

        who = who_final
        if not who:
            out.append(dict(r))
            continue

        who = _sanitize_candidate_name(who, alias_inv, results, j)
        if not who:
            out.append(dict(r))
            continue

        target = dict(results[j])
        tgt_txt = target.get("text") or ""
        tgt_sp = (target.get("speaker") or "").strip()

        # Only set if target speaker is weak or matches the candidate
        if tgt_sp in ("", None, "Unknown", "Narrator") or tgt_sp == who:
            old = tgt_sp or "Unknown"
            target["speaker"] = who
            target["_lock_speaker"] = True
            target["_lock_reason"] = "attrib_fragment"
            try:
                record_attrib_op_row(
                    "attrib_harvest",
                    "set",
                    target,
                    old,
                    who,
                    f"attach_action_fragments:{direction}",
                    j,
                )
            except Exception:
                pass
            log(
                f"[attrib] {direction} attach -> set speaker '{who}' for quote @ {j}: {tgt_txt[:60]}…"
            )
        else:
            try:
                record_attrib_op_row(
                    "attrib_harvest",
                    "skip_conflict_locked",
                    target,
                    tgt_sp,
                    who,
                    f"attach_action_fragments:{direction}",
                    j,
                )
            except Exception:
                pass
            log(
                f"[attrib] {direction} attach -> kept existing '{tgt_sp}' for quote @ {j}"
            )

        # If we don't want to keep the standalone attribution line, demote and tag
        # --- keep or drop the standalone attribution fragment line ---
        # Keep if global KEEP_ATTRIB_TEXT is True OR if this row was explicitly marked
        # by a splitter as a mid-quote attribution we must preserve.
        keep_fragment = bool(globals().get("KEEP_ATTRIB_TEXT", False)) or bool(
            r.get("_keep_attrib_text")
        )

        if keep_fragment:
            # keep as narration
            rr = dict(r)
            rr["text"] = txt
            rr["is_quote"] = False
            rr["speaker"] = "Narrator"
            rr.pop("_qa_demoted_quote", None)
            if r.get("_rid") is not None:
                rr["_rid"] = r["_rid"]
            out.append(rr)

            # write back the updated target in place (preserve index)
            results[j] = target
        else:
            # drop the fragment line by not appending (keeps UI cleaner),
            # but still write back the updated/locked target quote.
            results[j] = target
            continue

    return out


def _prefer_enlp_when_matching_quote(rr, qmap=None):
    """
    If this quote's normalized text matches ENLP index, prefer that speaker
    unless the row is already locked. Returns a possibly-updated row copy.
    Robust to any ENLP_QUOTE_INDEX shape and to missing ENLP data.
    """
    if not rr or not rr.get("is_quote"):
        return rr

    # build index once
    _build_enlp_index_once()
    index = DBG.get("_enlp_index") or {}
    if not index:
        return rr

    if rr.get("_lock_speaker"):
        return rr

    tnorm = _norm_quote_text(rr.get("text") or "")
    if not tnorm:
        return rr

    hit = index.get(tnorm)
    if not hit:
        return rr

    canon = hit.get("canonical")
    # If we have a canonical name, apply and lock.
    if canon and canon not in ("Narrator", "Unknown"):
        rr = dict(rr)
        rr["speaker"] = canon
        rr["_lock_speaker"] = True
        rr["_lock_reason"] = "enlp_quote_match"
        return rr

    # Otherwise, try to map char_id via ENLP_CID2CANON (if present)
    cid2canon = globals().get("ENLP_CID2CANON", None)
    if cid2canon and hit.get("char_id"):
        rr = dict(rr)
        rr["speaker"] = cid2canon.get(hit["char_id"]) or rr.get("speaker") or "Unknown"
        rr["_lock_speaker"] = True
        rr["_lock_reason"] = "enlp_quote_match"
        return rr

    # No usable info → leave row unchanged
    return rr


# peel narration that is stuck to a single-quote-span row ---


def _peel_outside_text_from_quote(rows):
    """
    If a row contains exactly one quoted span, but also has non-quoted text
    before or after the span (e.g., …” queried Smith.), split into up to 3 rows:
      [pre-narration?, quoted, post-narration?].
    - Keep the quoted substring ONLY in the quote row.
    - Pre/Post become Narrator rows (is_quote=False).
    - Preserve all characters and order.
    """
    if not rows:
        return rows

    out = []
    for r in rows:
        rr = dict(r)
        t = rr.get("text") or ""
        try:
            spans = _quote_spans(t)  # your existing span finder
        except Exception:
            spans = []

        # Only act on exactly 1 span where outside text exists
        if spans and len(spans) == 1:
            lo, hi = spans[0]
            pre = t[:lo].strip()
            mid = t[lo:hi].strip()
            post = t[hi:].strip()

            if mid and (pre or post):
                if pre:
                    out.append({"speaker": "Narrator", "text": pre, "is_quote": False})
                qsp = rr.get("speaker") or ""
                if qsp in ("", "Narrator"):
                    qsp = "Unknown"
                out.append(
                    {
                        **{
                            k: v
                            for k, v in rr.items()
                            if k not in ("text", "speaker", "is_quote")
                        },
                        "speaker": qsp,
                        "text": mid,
                        "is_quote": True,
                    }
                )
                if post:
                    out.append({"speaker": "Narrator", "text": post, "is_quote": False})

                try:
                    DBG["peel_outside_quote_rows"] = (
                        DBG.get("peel_outside_quote_rows", 0) + 1
                    )
                except Exception:
                    pass
                continue

        out.append(rr)

    return out


# recover balanced-quote content from Narrator rows ---
def _recover_balanced_quotes_from_narration(rows):
    """
    If a Narrator row contains 1+ quoted spans, split it into narration + quoted + narration.
    Quoted spans become separate rows with speaker=Unknown (later passes can attribute).
    """
    if not rows:
        return rows

    out = []
    for r in rows:
        rr = dict(r)
        t = rr.get("text") or ""
        sp = (rr.get("speaker") or "").strip()
        if sp != "Narrator":
            out.append(rr)
            continue

        try:
            spans = _quote_spans(t)
        except Exception:
            spans = []

        if not spans:
            out.append(rr)
            continue

        last = 0
        for lo, hi in spans:
            if lo > last:
                pre = t[last:lo].strip()
                if pre:
                    out.append({"speaker": "Narrator", "text": pre, "is_quote": False})
            mid = t[lo:hi].strip()
            if mid:
                out.append({"speaker": "Unknown", "text": mid, "is_quote": True})
            last = hi

        if last < len(t):
            tail = t[last:].strip()
            if tail:
                out.append({"speaker": "Narrator", "text": tail, "is_quote": False})

        try:
            DBG["recovered_quotes_from_narration"] = (
                DBG.get("recovered_quotes_from_narration", 0) + 1
            )
        except Exception:
            pass

    return out


def _has_quote_span(txt: str) -> bool:
    try:
        return bool(_quote_spans(_norm_unicode_quotes(txt or "", keep_curly=True)))
    except Exception:
        return False


def _final_never_break_quotes(rows: list[dict]) -> list[dict]:
    """
    Last-chance guard: if a quote opens and doesn't close, slurp everything
    until the closer into one quoted row (keep the original speaker).
    Never pulls across a clear new turn (“…”  “…”).
    """
    if not rows:
        return rows
    if not globals().get("QUOTES_ARE_ATOMIC"):
        return rows

    def _norm(s):
        return _norm_unicode_quotes(s or "", keep_curly=True)

    def _starts_with_open(s):
        return bool(re.match(r'^\s*[“"]', _norm(s)))

    def _ends_with_close(s):
        return bool(re.search(r'[”"]\s*$', _norm(s)))

    def _has_span(s):
        return bool(_quote_spans(_norm(s)))

    out, buf = [], []
    in_run = False
    run_speaker = None
    run_meta = {}

    def flush():
        nonlocal buf, in_run, run_speaker, run_meta
        if not buf:
            return
        # merge text (preserve quotes exactly as they appeared)
        merged = dict(run_meta)
        merged["text"] = "".join([b["text"] for b in buf])
        merged["is_quote"] = True
        if run_speaker:
            merged["speaker"] = run_speaker
        out.append(merged)
        buf.clear()
        in_run = False
        run_speaker = None
        run_meta = {}

    i = 0
    n = len(rows)
    while i < n:
        r = dict(rows[i])
        s = r.get("text") or ""
        is_q = bool(r.get("is_quote"))

        if not in_run:
            # Start a run only if this row is quote-like and looks like an opener that doesn't close here
            if is_q and _starts_with_open(s) and not _ends_with_close(s):
                in_run = True
                run_speaker = r.get("speaker") or ""
                # seed meta from the first quoted row
                run_meta = {k: v for k, v in r.items() if k not in {"text"}}
                buf.append({"text": s})
            else:
                out.append(r)
        else:
            # Already in a quoted run: keep gluing *everything* until we see a closing quote.
            # If we encounter a clear new turn (“… ”  “ …”), flush before starting it.
            if _starts_with_open(s) and _ends_with_close(s):
                # A self-contained quote row: this is almost surely a new turn → flush and start fresh.
                flush()
                out.append(r)
            else:
                # append text regardless of current row labeling
                buf.append({"text": s})
                # end the run once we finally see a closer on *this* row
                if _ends_with_close(s):
                    flush()
        i += 1

    # Unclosed tail → flush anyway (very rare; safer to keep it quoted)
    if in_run:
        flush()

    return out


def _quote_spans(s: str):
    """
    Return [(start, end)] for each quoted span (end exclusive).
    Robust to mixed curly/ASCII quotes. Fallback-to-EOL is **conservative**:
    only when the opener is at the line start or right after a dash/comma.
    """
    s = s or ""
    min_len = globals().get("MIN_QUOTE_CHARS", 1)
    open_q = set(globals().get("OPEN_Q", {"“", '"', "‘"}))
    close_q = set(globals().get("CLOSE_Q", {"”", '"', "’"}))

    spans = []
    start = None
    active = None

    for i, ch in enumerate(s):
        if start is None:
            if ch in open_q:
                start = i
                active = ch
        else:
            if ch in close_q:
                if (
                    (active == '"' and ch == '"')
                    or (active == "“" and ch == "”")
                    or (active == "‘" and ch == "’")
                ):
                    if i - start + 1 >= min_len:
                        spans.append((start, i + 1))
                    start, active = None, None

    # Conservative fallback: opener with no closer → to EOL ONLY if opener looks like start/soft-wrap
    if start is not None:
        pre = s[:start]
        looks_like_head = (pre.strip() == "") or bool(
            re.search(r"[—–-]\s*$|[,;:]\s*$", pre)
        )
        if looks_like_head and (len(s) - start >= min_len):
            spans.append((start, len(s)))

    return spans


def _quote_spans_balanced(s: str):
    """
    Like _quote_spans but **no** dangling-opener fallback.
    Returns only true opener→closer spans.
    """
    s = s or ""
    min_len = globals().get("MIN_QUOTE_CHARS", 1)
    open_q = set(globals().get("OPEN_Q", {"“", '"', "‘"}))
    close_q = set(globals().get("CLOSE_Q", {"”", '"', "’"}))

    spans, start, active = [], None, None
    for i, ch in enumerate(s):
        if start is None:
            if ch in open_q:
                start, active = i, ch
        else:
            if ch in close_q:
                if (
                    (active == '"' and ch == '"')
                    or (active == "“" and ch == "”")
                    or (active == "‘" and ch == "’")
                ):
                    if i - start + 1 >= min_len:
                        spans.append((start, i + 1))
                    start, active = None, None
    return spans


def _rehydrate_monologue_gaps(rows: list[dict], window: int = 2) -> list[dict]:
    """
    If we see QUOTE(S) → Narrator(no quotes, sentence-like) → QUOTE(S) within ±window,
    flip the narrator middle back to quoted speech by S (unless it's attributiony/locked).
    """
    if not rows:
        return rows

    def _is_dialogue(r):
        return looks_like_direct_speech(r.get("text") or "")

    def _is_plain_sentence(s: str) -> bool:
        t = (s or "").strip()
        if not t or '"' in t or "“" in t or "”" in t:
            return False
        # starts with capital and ends in terminal punct
        return bool(re.match(r"^[A-Z0-9][\s\S]{2,}[.?!]$", t))

    def _is_attrib_like(s: str) -> bool:
        try:
            return _looks_like_attribution_fragment((s or "").strip())
        except Exception:
            return False

    out = [dict(r) for r in rows]
    n = len(out)

    for i in range(1, n - 1):
        left, mid, right = out[i - 1], out[i], out[i + 1]
        if _is_dialogue(left) and not _is_dialogue(mid) and _is_dialogue(right):
            S = (left.get("speaker") or "").strip()
            if S and S not in ("Narrator", "Unknown") and not mid.get("_lock_speaker"):
                tmid = _norm_unicode_quotes(mid.get("text") or "", keep_curly=True)
                if _is_plain_sentence(tmid) and not _is_attrib_like(tmid):
                    # wrap and flip to quote by S
                    q = tmid
                    if not (q.startswith('"') or q.startswith("“")):
                        q = '"' + q
                    if not (q.endswith('"') or q.endswith("”")):
                        q = q + '"'
                    mid["text"] = q
                    mid["is_quote"] = True
                    apply_speaker(
                        mid, S, reason="rehydrate_monologue_gap", stage="rehydrate"
                    )
    return out


def split_multiquote_segments(
    rows: list[dict], qmap=None, alias_inv=None
) -> list[dict]:
    """
    Split rows that contain multiple direct-speech spans into separate rows
    *without ever* producing an empty `""` segment, and while preserving
    quote spans on the speech fragments themselves.

    Key rules:
      - Speech fragments are ALWAYS emitted with their opening/closing `"` kept (or re-synthesized if needed).
      - Connector fragments (between quotes) are Narrator. If we had to strip quotes from a connector, we tag it
        as an intentional demotion for the auditor: _qa_demoted_quote=True.
      - Adjacent zero-length or pure `""` tokens are *never* emitted; we fuse them into the nearest speech fragment.
      - We preserve non-textual fields and pass through `_rid` only to the first emitted fragment to keep the auditor stable.
    """

    out = []

    for r in rows:
        txt = r.get("text") or ""
        base = dict(r)
        base_txt_norm = _norm_unicode_quotes(txt, keep_curly=True)
        spans = _quote_spans_balanced(base_txt_norm)

        # If 0 or 1 spans, passthrough
        if len(spans) <= 1:
            out.append(dict(r))
            continue

        # More than one span -> split into: [ pre, speech1, mid1, speech2, mid2, ... , post ]
        pieces = []
        last = 0
        for lo, hi in spans:
            # pre/mid connector
            if lo > last:
                connector = base_txt_norm[last:lo]
                if connector and connector.strip():
                    pieces.append(("connector", connector))
            # speech (ensure quotes kept)
            speech = base_txt_norm[lo:hi]
            pieces.append(("speech", speech))
            last = hi
        # trailing connector
        if last < len(base_txt_norm):
            tail = base_txt_norm[last:]
            if tail and tail.strip():
                pieces.append(("connector", tail))

        # Cleanup: drop empty pure-quote tokens like ""
        cleaned = []
        for kind, seg in pieces:
            s = seg.strip()
            if kind == "speech":
                # If the slice doesn't start/end with a quote (edge-case), synthesize.
                s_norm = s
                has_open = s_norm.startswith('"') or s_norm.startswith("“")
                has_close = s_norm.endswith('"') or s_norm.endswith("”")
                if not has_open:
                    s_norm = '"' + s_norm
                if not has_close:
                    s_norm = s_norm + '"'
                # Elide speech that is literally just ""
                if s_norm.strip() in ('""', "“”"):
                    continue
                cleaned.append(("speech", s_norm))
            else:
                # connector: NEVER emit empty/whitespace-only connectors
                if s and s not in ('""', "“”"):
                    cleaned.append(("connector", s))

        # If everything collapsed (e.g., weird quotes), just pass the original row through
        if not cleaned:
            out.append(dict(r))
            continue

        # Emit rows: speech rows keep/force is_quote=True; connectors -> Narrator (+tag demotion)
        first_emitted = True
        for kind, seg in cleaned:
            rr = dict(base)
            rr["text"] = seg

            if kind == "speech":
                rr["is_quote"] = True
                # Keep speaker as-is; later passes attach/lock if needed.
            else:
                # connector narration
                rr["is_quote"] = False
                rr["speaker"] = "Narrator"
                rr["_qa_demoted_quote"] = (
                    True  # tell the auditor this connector losing quotes is intentional
                )

            # Preserve the original _rid only on the first emitted child to keep auto-restore sane
            if first_emitted:
                first_emitted = False
            else:
                rr.pop("_rid", None)

            out.append(rr)

    return out


def _call_speaker_from_attrib_fragment(text, alias_inv=None):
    """
    Compatibility shim: some trees define _speaker_from_attrib_fragment(text),
    others define _speaker_from_attrib_fragment(text, alias_inv=None).
    Returns whatever the underlying function returns (tuple or str).
    """
    try:
        return _speaker_from_attrib_fragment(text, alias_inv)  # 2-arg variant
    except TypeError:
        return _speaker_from_attrib_fragment(text)  # 1-arg variant


def _demote_quoted_attrib_fragments(results, alias_inv):
    """
    Demote rows like `"said Zack"` *and* rows incorrectly marked as quote that
    contain NO quote glyphs but are pure beats (`said Zack.` / `laughed King.`).
    Strip outer quotes if present; attach the inferred speaker to the nearest
    Unknown quote (prefer NEXT, else PREV). Tag with _qa_demoted_quote.
    """
    import re

    if not results:
        return results

    out = []
    n = len(results)

    _STRICT = globals().get("_ATTRIB_VERBS_RX_STRICT")
    _LINE_RX = globals().get("_ATTRIB_LINE_RX")
    _VERBS_ANY = globals().get("_VERBS_RX")  # loose fallback

    def _has_q(s):
        return any(ch in (s or "") for ch in ('"', "“", "”", "«", "»", "‘", "’"))

    def _token_count(s: str) -> int:
        return len(re.findall(r"[A-Za-z0-9']+", s or ""))

    def _strip_outer_quotes_once(s: str) -> str:
        if not s:
            return s
        s2 = s.strip()
        if s2 and s2[0] in {'"', "“", "‘"} and s2[-1] in {'"', "”", "’"}:
            return s2[1:-1].strip()
        return s2.strip(' "\u201c\u201d\u2018\u2019')

    def _attach_to_next_unknown_quote(idx_from: int, who: str) -> bool:
        j = idx_from + 1
        while j < n and not _looks_like_direct_speech_strict(
            (results[j].get("text") or "")
        ):
            j += 1

        if j < n and _looks_like_direct_speech_strict((results[j].get("text") or "")):
            prev_sp = (results[j].get("speaker") or "").strip()
            if prev_sp in ("", "Unknown", "Narrator") or prev_sp == who:
                if "apply_speaker" in globals():
                    try:
                        apply_speaker(
                            results[j],
                            who,
                            reason="quoted_attrib_next",
                            stage="demote_quoted_attr",
                        )
                    except Exception:
                        results[j]["speaker"] = who
                        results[j]["_lock_speaker"] = True
                        results[j]["_locked_to"] = who
                        results[j]["_lock_reason"] = "quoted_attrib_next"
                else:
                    results[j]["speaker"] = who
                    results[j]["_lock_speaker"] = True
                    results[j]["_locked_to"] = who
                    results[j]["_lock_reason"] = "quoted_attrib_next"
                try:
                    if "record_attrib_op" in globals():
                        frag = (results[j].get("text", "")[:64]).replace("\n", " ")
                        record_attrib_op(
                            "demote_quoted_attrib",
                            idx=idx_from,
                            attach="next",
                            who=who,
                            excerpt=frag,
                        )
                except Exception:
                    pass
                return True
        return False

    def _attach_to_prev_unknown_quote_in_out(who: str) -> bool:
        j = len(out) - 1
        while j >= 0 and not _looks_like_direct_speech_strict(
            (out[j].get("text") or "")
        ):
            j -= 1
        if j >= 0:
            prev_sp = (out[j].get("speaker") or "").strip()
            if prev_sp in ("", "Unknown", "Narrator") or prev_sp == who:
                tgt = dict(out[j])
                if "apply_speaker" in globals():
                    try:
                        apply_speaker(
                            tgt,
                            who,
                            reason="quoted_attrib_prev",
                            stage="demote_quoted_attr",
                        )
                    except Exception:
                        tgt["speaker"] = who
                        tgt["_lock_speaker"] = True
                        tgt["_locked_to"] = who
                        tgt["_lock_reason"] = "quoted_attrib_prev"
                else:
                    tgt["speaker"] = who
                    tgt["_lock_speaker"] = True
                    tgt["_locked_to"] = who
                    tgt["_lock_reason"] = "quoted_attrib_prev"
                out[j] = tgt
                try:
                    if "record_attrib_op" in globals():
                        frag = (tgt.get("text", "")[:64]).replace("\n", " ")
                        record_attrib_op(
                            "demote_quoted_attrib",
                            idx=j,
                            attach="prev",
                            who=who,
                            excerpt=frag,
                        )
                except Exception:
                    pass
                return True
        return False

    for i, r in enumerate(results):
        if not r.get("is_quote"):
            out.append(r)
            continue

        # GUARD: If this row has a non-Narrator/non-Unknown speaker, it's a quote continuation
        # from BookNLP (no opening quote mark). Do NOT demote these to narration.
        current_speaker = (r.get("speaker") or "").strip()
        if current_speaker and current_speaker not in ("Narrator", "Unknown"):
            out.append(r)
            continue

        t = _norm_unicode_quotes(r.get("text") or "")
        has_q = _has_q(t)
        spans = _quote_spans(t) or []

        # Two gateways:
        #  A) exactly one quoted span (classic `"said Zack"` fragment)
        #  B) NO quote glyphs at all but row still flagged quote (e.g., `said Zack.`)
        if not (len(spans) == 1 or (not has_q)):
            out.append(r)
            continue

        # Extract the candidate fragment to analyze
        if len(spans) == 1:
            a, b = spans[0]
            qseg = t[a:b]
            frag = _strip_outer_quotes_once(qseg)
        else:
            frag = t  # no glyphs; analyze the whole line

        # Try to pull a concrete speaker from the fragment
        who_raw, verb_raw = None, None
        # Prefer strict line pattern when we have it
        if globals().get("_ATTRIB_LINE_RX") and globals()["_ATTRIB_LINE_RX"].match(
            frag
        ):
            tmp = _call_speaker_from_attrib_fragment(frag, alias_inv)
            if isinstance(tmp, tuple):
                who_raw, verb_raw = tmp
            else:
                who_raw = tmp
        # Fallback: short + contains a known attribution/action verb
        if not who_raw:
            if _token_count(frag) <= 10:
                verb_rx = _STRICT or _VERBS_ANY
                if verb_rx and re.search(verb_rx, frag, flags=re.I):
                    tmp = _call_speaker_from_attrib_fragment(frag, alias_inv)
                    if isinstance(tmp, tuple):
                        who_raw, verb_raw = tmp
                    else:
                        who_raw = tmp

        # If no usable 'who', keep as-is (prevents nuking true utterances)
        if not who_raw:
            out.append(r)
            continue

        who = _sanitize_person_name(who_raw) if who_raw else None
        if not who or who in {"Narrator", "Unknown"} or _is_banned(who):
            out.append(r)
            continue
        try:
            if "_alias_correct" in globals():
                who = _alias_correct(who, alias_inv or {})
        except Exception:
            pass

        # Build demoted narrator row (strip outer quotes if any)
        rr = dict(r)
        rr["text"] = frag
        rr["is_quote"] = False
        rr["speaker"] = "Narrator"
        rr["_qa_demoted_quote"] = True
        rr["_qa_demote_reason"] = "quoted_attrib_fragment"
        if r.get("_rid") is not None:
            rr["_rid"] = r["_rid"]

        # Prefer NEXT Unknown quote; else PREV in out
        attached = _attach_to_next_unknown_quote(
            i, who
        ) or _attach_to_prev_unknown_quote_in_out(who)
        try:
            DBG["demote_quoted_attrib_rows"] = (
                DBG.get("demote_quoted_attrib_rows", 0) + 1
            )
            if attached:
                DBG["demote_quoted_attrib_attached"] = (
                    DBG.get("demote_quoted_attrib_attached", 0) + 1
                )
        except Exception:
            pass

        out.append(rr)

    return out


def _balanced_quote_count(s: str) -> bool:
    s = s or ""
    # count only the visible quote glyphs we use
    q = sum(1 for ch in s if ch in ('"', "“", "”"))
    return (q % 2) == 0


def _force_nonquote_when_no_glyphs(rows):
    """
    Very late safety net: any row marked is_quote=True but containing NO visible
    quote glyphs becomes narration. Useful when earlier promotions accidentally
    minted quote rows out of naked beats like 'said Zack.'.
    """
    if not rows:
        return rows
    out = []
    GLYPHS = {'"', "“", "”", "«", "»", "‘", "’"}
    for i, r in enumerate(rows):
        if r.get("is_quote") and not any(ch in (r.get("text") or "") for ch in GLYPHS):
            rr = dict(r)
            rr["is_quote"] = False
            if not rr.get("speaker") or rr["speaker"] not in ("Narrator", "Unknown"):
                rr["speaker"] = "Narrator"
            rr["_qa_demoted_quote"] = True
            rr["_qa_demote_reason"] = "no_quote_glyphs"
            out.append(rr)
        else:
            out.append(r)
    return out


def smooth_dialogue_turns(results, window=6):
    """
    Light-weight ping-pong smoother for dialogue:
    - If we see S, S, S with all three lines as dialogue, and a consistent 'other' speaker
      appears adjacent in the window, flip the middle S to that 'other' IF neighbors are confident.
    - Also fixes rare 'Narrator' in-between actual quotes.
    Guards:
      - Never flip across a visual turn boundary (…”  “…”).
      - Never flip locked rows or when neighbors aren’t confident.
    """
    if not results:
        return results

    def _is_dialogue(r):
        return looks_like_direct_speech(r.get("text") or "")

    def _norm(s):
        try:
            return _norm_unicode_quotes(s or "")
        except Exception:
            return s or ""

    def _starts_with_opener(s):
        return bool(re.match(r'^\s*["“«]', _norm(s)))

    def _ends_with_closer(s):
        return bool(re.search(r'["”»]\s*$', _norm(s)))

    def nearest_other(i, S):
        for j in range(i - 1, max(-1, i - window), -1):
            if _is_dialogue(res[j]) and res[j]["speaker"] != S:
                return res[j]["speaker"]
        for j in range(i + 1, min(n, i - window * (-1))):
            if _is_dialogue(res[j]) and res[j]["speaker"] != S:
                return res[j]["speaker"]
        return None

    def confident(r):
        sp = r.get("speaker")
        if r.get("_lock_speaker"):
            return True
        if sp in ("Unknown", "Narrator", None, ""):
            return False
        try:
            if sp in (CANON_WHITELIST or {}):
                return True
        except Exception:
            pass
        try:
            return sp in (CJ_MAP or {}).values()
        except Exception:
            return False

    res = results
    n = len(res)

    # narrator-in-between fix (conservative)
    for i in range(1, n - 1):
        a, b, c = res[i - 1], res[i], res[i + 1]
        if not (_is_dialogue(a) and _is_dialogue(b) and _is_dialogue(c)):
            if (
                _is_dialogue(b)
                and (b.get("speaker") == "Narrator" or not b.get("speaker"))
                and not b.get("_lock_speaker")
            ):
                guess = a.get("speaker") if _is_dialogue(a) else c.get("speaker")
                if guess and guess not in ("Narrator", "Unknown", "", None):
                    # boundary guard
                    if not (
                        _ends_with_closer(a.get("text") or "")
                        and _starts_with_opener(b.get("text") or "")
                    ):
                        b["speaker"] = guess
                        try:
                            log(
                                f"[turn-fix] Narrator dialogue reassigned to '{guess}' for: {b['text'][:60]}…"
                            )
                        except Exception:
                            pass
            continue

    # collapse S,S,S only if both neighbors are confident and not a boundary
    for i in range(1, n - 1):
        a, b, c = res[i - 1], res[i], res[i + 1]
        if _is_dialogue(a) and _is_dialogue(b) and _is_dialogue(c):
            S = a.get("speaker")
            if (
                b.get("speaker") == S
                and c.get("speaker") == S
                and confident(a)
                and confident(c)
                and not b.get("_lock_speaker")
            ):
                # boundary guards
                if _ends_with_closer(a.get("text") or "") and _starts_with_opener(
                    b.get("text") or ""
                ):
                    continue
                if _ends_with_closer(b.get("text") or "") and _starts_with_opener(
                    c.get("text") or ""
                ):
                    continue
                other = nearest_other(i, S)
                if other and other not in ("Narrator", "Unknown", "", None):
                    b["speaker"] = other
                    try:
                        log(
                            f"[turn-fix] '{S}' triple collapsed; middle reassigned to '{other}' for: {b['text'][:60]}…"
                        )
                    except Exception:
                        pass

    return res


def _enforce_locked_speakers(rows: list[dict]) -> list[dict]:
    """
    Late pass: if any row is 'locked', ensure its speaker equals the locked target.
    If a heuristic flipped it, restore the original locked speaker.
    """
    if not rows:
        return rows

    out = []
    for r in rows:
        rr = dict(r)
        if rr.get("_lock_speaker"):
            target = rr.get("_locked_to")
            if target and rr.get("speaker") != target:
                # PRECOMPUTE the snippet to avoid backslashes inside f-string expr
                txt = rr.get("text") or ""
                snippet = txt.replace("\n", " ")[:60]
                log(
                    f"[lock] restoring '{target}' over '{rr.get('speaker')}' | {snippet}…"
                )
                rr["speaker"] = target
        out.append(rr)
    return out


# --- PURE reassert: recompute is_quote from spans; DO NOT touch speaker here ---
def _reassert_quote_flags(rows):
    out = []
    for r in rows:
        rr = dict(r)
        txt = _norm_unicode_quotes(rr.get("text") or "")
        spans = _quote_spans(txt)
        rr["is_quote"] = bool(spans and len(spans) > 0)
        out.append(rr)
    return out


def _hard_separate_quotes_and_narration(rows, qmap, alias_inv):
    """
    If a row contains both quoted and unquoted text, split it back into
    Narrator and per-quote segments using split_multiquote_segments.
    """
    if globals().get("QUOTES_ARE_ATOMIC"):
        return rows

    if not rows:
        return rows
    out = []
    for r in rows:
        t = _norm_unicode_quotes(r.get("text") or "")
        spans = _quote_spans(t)

        # keep as-is if no quotes, or exactly one span that covers all text
        if not spans or (len(spans) == 1 and spans[0] == (0, len(t))):
            rr = dict(r)
            rr["text"] = t
            out.append(rr)
            continue

        # mixed → resplit this single row
        parts = split_multiquote_segments(
            [{"speaker": r.get("speaker"), "text": t}], qmap, alias_inv
        )
        out.extend(parts)
    return out


def _audit_quotes(stage: str, rows: list[dict]):
    # Count rows that contain any visible quote char
    def qcount(t: str) -> int:
        t = t or ""
        return t.count('"') + t.count("“") + t.count("”")

    with_q = sum(1 for r in rows if qcount(r.get("text") or "") > 0)
    bad = sum(
        1
        for r in rows
        if qcount(r.get("text") or "") > 0
        and (r.get("is_quote") is False or r.get("speaker") == "Narrator")
    )
    log(f"[audit] {stage}: rows_with_quotes={with_q} misflagged={bad}")


def _assert_no_broken_quotes(rows):
    errs = 0
    open_run = False
    for i, r in enumerate(rows):
        s = _norm_unicode_quotes(r.get("text") or "", keep_curly=True)
        if re.match(r'^\s*[“"]', s) and not re.search(r'[”"]\s*$', s):
            open_run = True
        elif open_run and r.get("is_quote") and re.search(r'[”"]\s*$', s):
            open_run = False
        elif open_run and not r.get("is_quote"):
            log(f"[assert] Narrator inside open quote at row {i}")
            errs += 1
    DBG["broken_quote_runs"] = errs
    return rows


# Put near your other config toggles if you want it adjustable
COALESCE_ALLOW_QUOTE_TO_QUOTE = False  # keep quotes separate for clarity


def can_merge(a: dict, b: dict) -> bool:
    """
    Decide whether two adjacent rows should be merged.
    HARD GUARDS:
      - Never merge across quote↔narrator boundary.
      - Never merge if speakers differ.
      - Optionally avoid merging quote→quote to keep quotes crisp.
      - Avoid merging if either side looks like an attribution fragment
        (e.g., '… said Zack', 'asked Charlie softly') so we don't fuse tails/heads.
    """
    is_quote_a = bool(a.get("is_quote"))
    is_quote_b = bool(b.get("is_quote"))

    # 1) Never cross quote↔narrator boundary
    if is_quote_a != is_quote_b:
        return False

    # 2) Optional: keep quotes separate even when both are quotes
    if is_quote_a and is_quote_b and not COALESCE_ALLOW_QUOTE_TO_QUOTE:
        return False

    # 3) Speakers must match exactly
    if (a.get("speaker") or "") != (b.get("speaker") or ""):
        return False

    # 4) If either side is an attribution-like narrator fragment, don't merge
    ta = a.get("text", "") or ""
    tb = b.get("text", "") or ""
    if _looks_like_attribution_fragment(ta) or _looks_like_attribution_fragment(tb):
        return False

    # (Optional) You can add more heuristics here (length checks, punctuation) if desired.
    return True


# --- Safe coalescer: allow quote→quote merges for same speaker; never mix narr↔quote (instrumented) ---
COALESCE_ALLOW_QUOTE_TO_QUOTE = (
    False  # ✅ allow merging contiguous quotes from the same speaker
)


# --- Quote-aware coalescer: forbid swallowing narration tails into quotes (instrumented) ---
def _has_any_quote_char(t: str) -> bool:
    t = t or ""
    return (
        ('"' in t)
        or ("\u201c" in t)
        or ("\u201d" in t)
        or ("\u2018" in t)
        or ("\u2019" in t)
    )


def _ends_with_closing_quote(t: str) -> bool:
    """
    True if the last matched quote span ends at the end of the text (optionally with terminal punctuation/spaces).
    """
    s = _norm_unicode_quotes(t or "")
    spans = _quote_spans(s)
    if not spans:
        return False
    last_end = spans[-1][1]
    tail = s[last_end:]
    return bool(
        re.match(r"^\s*[.!?]*\s*$", tail)
    )  # nothing but terminal punctuation/space after the closer


# === Hard "line-for-line" mode (no merging of any kind) ===
# When True: every input row remains a row. Quotes never glue to quotes.
# Narration never glues to narration. Narration never glues to quotes.
STRICT_LINE_FOR_LINE = True


# --- Quote-aware coalescer: DISABLED under STRICT_LINE_FOR_LINE ---
def _has_any_quote_char(t: str) -> bool:
    t = t or ""
    return (
        ('"' in t)
        or ("\u201c" in t)
        or ("\u201d" in t)
        or ("\u2018" in t)
        or ("\u2019" in t)
    )


def _ends_with_closing_quote(t: str) -> bool:
    s = _norm_unicode_quotes(t or "")
    spans = _quote_spans(s)
    if not spans:
        return False
    last_end = spans[-1][1]
    tail = s[last_end:]
    return bool(re.match(r"^\s*[.!?]*\s*$", tail))


def _coalesce_paragraphs(results, max_gap_chars: int = 0):
    """
    DISABLED FOR AUDIOBOOK: We need to preserve ALL narration sentences separately.
    Previously merged 540 → 277 rows (49% reduction). For audiobook TTS, each sentence 
    needs to be separate for independent voice/pacing control.
    """
    # Return all rows unchanged - preserve every sentence for audiobook
    return results
    
    # ===== ORIGINAL DISABLED CODE BELOW =====
    if not results:
        return results

    def _has_quote_glyphs(s: str) -> bool:
        t = _norm_unicode_quotes(s or "")
        return any(ch in t for ch in ('"', "“", "”", "«", "»", "‘", "’"))

    def _looks_attrib(s: str) -> bool:
        s = (s or "").strip()
        try:
            if _ATTRIB_LINE_RX and _ATTRIB_LINE_RX.match(s):
                return True
        except Exception:
            pass
        try:
            return bool(_looks_like_attribution_fragment(s))
        except Exception:
            return False

    out = []
    cur = None
    merged = []
    buffer = None
    def has_balanced_quote(row):
        # Use _quote_spans to check for balanced quotes
        text = row.get("text", "")
        spans = _quote_spans(text)
        return bool(spans)

    for row in rows:
        # If this row contains a balanced quote, flush buffer and keep atomic
        if has_balanced_quote(row):
            if buffer is not None:
                merged.append(buffer)
                buffer = None
            merged.append(row)
            continue
        is_narr = (row.get("speaker", "").strip().lower() == "narrator") and not row.get("is_quote")
        if is_narr:
            if buffer is None:
                buffer = dict(row)
            else:
                # Merge text and other fields as needed
                buffer["text"] = (buffer.get("text", "") + " " + row.get("text", "")).strip()
                # Optionally merge other fields if needed
        else:
            if buffer is not None:
                merged.append(buffer)
                buffer = None
            merged.append(row)
    if buffer is not None:
        merged.append(buffer)




# --- Aggressive merge of consecutive quote rows into a single "character line" (instrumented) ---
def _merge_quote_runs_aggressive(rows: list[dict], max_chars: int = 4000) -> list[dict]:
    """
    Glue consecutive quote rows into one line, stopping when narration appears
    or when merging would likely cross a turn boundary.

    Rules:
      - Merge only lines with is_quote=True.
      - If all speakers are Unknown except one known, take that known.
      - If multiple known speakers appear in run, STOP before crossing to a new speaker.
      - Do not merge a row that looks like a pure attribution fragment (tail/head).
      - Length cap per merged line (max_chars) for safety.

    Speaker selection for the merged line:
      - Pick the row with highest _speaker_confidence (locks > char_id > qscore > named).
      - If all Unknown, keep "Unknown".
    """
    if not rows:
        return rows

    # dbg counters
    try:
        DBG.setdefault("merge_quote_runs_calls", 0)
        DBG.setdefault("merge_quote_runs_merges", 0)
        DBG["merge_quote_runs_calls"] += 1
    except Exception:
        pass

    def conf(r: dict) -> float:
        # reuse your existing notion if present
        try:
            return _speaker_confidence(r)
        except Exception:
            c = 0.0
            if r.get("_lock_speaker"):
                c += 10.0
            if r.get("_cid") is not None:
                c += 3.0
            c += float(r.get("_qscore") or 0.0)
            if r.get("speaker") not in ("Narrator", "Unknown", None, ""):
                c += 0.5
            return c

    out: list[dict] = []
    i = 0
    n = len(rows)

    while i < n:
        r = rows[i]
        if not r.get("is_quote"):
            out.append(r)
            i += 1
            continue

        # start a run with this quote
        run_rows = [dict(r)]
        i += 1

        # try to extend the run
        while i < n and rows[i].get("is_quote"):
            cand = rows[i]
            txt = cand.get("text") or ""

            # avoid gluing pure attribution fragments into dialogue
            if _looks_like_attribution_fragment(txt):
                break

            # If merging would clearly cross a new turn:
            # - different known speaker appears while current run already has a known speaker
            run_known_speakers = [
                x.get("speaker")
                for x in run_rows
                if x.get("speaker") not in (None, "", "Unknown", "Narrator")
            ]
            cand_sp = cand.get("speaker")
            if cand_sp not in (None, "", "Unknown", "Narrator") and run_known_speakers:
                # if the incoming known speaker differs from the one we already have, stop
                if all(cand_sp != s for s in run_known_speakers):
                    break

            # obey the length cap
            projected = (
                sum(len(x.get("text") or "") for x in run_rows)
                + len(txt)
                + len(run_rows)
            )  # +spaces
            if projected > max_chars:
                break

            run_rows.append(dict(cand))
            i += 1

        # merge the run rows' text
        merged_text = " ".join(
            (rr.get("text") or "").strip()
            for rr in run_rows
            if (rr.get("text") or "").strip()
        )
        merged_text = re.sub(r"\s+\n\s+|\s{2,}", " ", merged_text).strip()
        merged_text = _fix_tokenization_gaps(merged_text)

        # decide final speaker by highest confidence
        best = max(run_rows, key=conf)
        final_sp = best.get("speaker") or "Unknown"

        # build merged row
        merged = dict(run_rows[0])
        merged["text"] = merged_text
        merged["speaker"] = final_sp
        merged["is_quote"] = True  # keep as quote
        # keep strongest metadata
        for rr in run_rows[1:]:
            merged = _merge_meta_keep_best(merged, rr)

        out.append(merged)
        try:
            DBG["merge_quote_runs_merges"] += len(run_rows) - 1
        except Exception:
            pass

    return out


# --- Merge consecutive quote rows into one “character line” by speaker (conservative) ---
def _merge_quote_runs_by_speaker(rows: list[dict], max_chars: int = 4000) -> list[dict]:
    """
    Merge consecutive quote rows ONLY when they share the exact same known speaker.

    Guardrails:
      - Never merge Unknown/Narrator (unless MERGE_UNKNOWN_QUOTES=True in globals()).
      - Respect row-level opt-outs: _no_merge or _no_split flags.
      - Do not merge if locked-speaker conflicts across the run.
      - Do not merge across a visual turn boundary (…”  “…”).
      - Do not merge across a RID gap (> 1) when both rows carry numeric _rid.
      - Do not merge if it would reduce the total quote glyph budget.
      - Do not merge if either side contains a seam-like tail:  [”"] (—|–|-)? [a-z]
      - Do not merge if concatenation would CREATE a seam-like tail at the join.
      - Length cap per merged row (max_chars).

    Keeps strongest metadata; preserves locks when any part of the run is locked.
    """
    import re

    if not rows:
        return rows

    try:
        if STRICT_LINE_FOR_LINE:
            return rows
    except NameError:
        pass

    # --- config from globals (optional toggle) ---
    try:
        ALLOW_UNKNOWN = bool(globals().get("MERGE_UNKNOWN_QUOTES", False))
    except Exception:
        ALLOW_UNKNOWN = False

    # --- small local helpers (no external deps required) ---
    def is_quote(r):
        return bool(r.get("is_quote"))

    def speaker_of(r):
        return (r.get("speaker") or "").strip()

    def locked_to(r):
        return (r.get("_locked_to") or "").strip()

    def has_flag(r, k):
        return bool(r.get(k))

    def _norm(s: str) -> str:
        try:
            return _norm_unicode_quotes(s or "")
        except Exception:
            return s or ""

    def _starts_with_opener_text(s: str) -> bool:
        t = _norm(s)
        return bool(re.match(r'^\s*["“«]', t))

    def _ends_with_closer_text(s: str) -> bool:
        t = _norm(s)
        return bool(re.search(r'["”»]\s*$', t))

    def _rid_num(r) -> int | None:
        rid = r.get("_rid")
        if rid is None:
            return None
        m = re.search(r"(\d+)", str(rid))
        return int(m.group(1)) if m else None

    def _rid_gap(a, b) -> bool:
        ra, rb = _rid_num(a), _rid_num(b)
        return ra is not None and rb is not None and abs(rb - ra) > 1

    def qglyphs(s: str) -> int:
        if not s:
            return 0
        return sum(1 for ch in s if ch in ('"', "“", "”", "‘", "’", "«", "»"))

    def row_qglyphs(r: dict) -> int:
        return qglyphs(r.get("text") or "")

    # seam-like tail: closing quote followed by optional dash then lowercase
    SEAM_RX = re.compile(r'[”"]\s*(?:[—–-]\s*)?[a-z]')

    def _seam_like_text(s: str) -> bool:
        return bool(SEAM_RX.search(s or ""))

    def _should_merge_quote_rows(a: dict, b: dict) -> bool:
        """Basic gate before heavier checks."""
        if not (is_quote(a) and is_quote(b)):
            return False
        sa = speaker_of(a) or "Unknown"
        sb = speaker_of(b) or "Unknown"

        # do not merge unknown/narration unless explicitly allowed
        if not ALLOW_UNKNOWN and (
            sa in ("Unknown", "Narrator") or sb in ("Unknown", "Narrator")
        ):
            return False

        # speakers must match
        if sa != sb:
            return False

        ta = a.get("text") or ""
        tb = b.get("text") or ""

        # do not merge if either side already looks like it ends-with-quote→lowercase seam
        if _seam_like_text(ta) or _seam_like_text(tb):
            return False

        # and do not merge if the JOIN would create a seam
        if _seam_like_text((ta.rstrip() + " " + tb.lstrip())):
            return False

        return True

    # --- dbg counters ---
    try:
        DBG["merge_quote_runs_calls"] = DBG.get("merge_quote_runs_calls", 0) + 1
    except Exception:
        pass

    out: list[dict] = []
    i, n = 0, len(rows)
    merges = 0
    skips_conflict = 0
    skips_flags = 0
    skips_glyph = 0
    skips_len = 0
    skips_turn = 0
    skips_ridgap = 0
    skips_guard = 0  # new: seam/unknown guard

    while i < n:
        head = dict(rows[i])
        i += 1

        if not is_quote(head):
            out.append(head)
            continue

        spk = speaker_of(head)

        if spk in ("Unknown", "Narrator", "", None) and not ALLOW_UNKNOWN:
            out.append(head)
            continue

        if has_flag(head, "_no_merge") or has_flag(head, "_no_split"):
            out.append(head)
            continue

        run = [head]

        # try to extend the run with same-speaker quotes (subject to guards)
        while i < n:
            cand = rows[i]

            # fast guard: must be mergeable quotes (same speaker, no seams, unknown policy)
            if not _should_merge_quote_rows(run[-1], cand):
                skips_guard += 1
                break

            if has_flag(cand, "_no_merge") or has_flag(cand, "_no_split"):
                skips_flags += 1
                break

            # do not merge across lock conflicts
            lt_head = locked_to(run[-1]) or speaker_of(run[-1])
            lt_cand = locked_to(cand) or speaker_of(cand)
            if lt_head and lt_cand and lt_head != lt_cand:
                skips_conflict += 1
                break

            # visual turn boundary guard …”  “…
            if _ends_with_closer_text(
                run[-1].get("text") or ""
            ) and _starts_with_opener_text(cand.get("text") or ""):
                skips_turn += 1
                break

            # RID gap guard
            if _rid_gap(run[-1], cand):
                skips_ridgap += 1
                break

            # length budget
            projected = (
                sum(len((r.get("text") or "")) for r in run)
                + len(cand.get("text") or "")
                + len(run)
            )  # spaces
            if projected > max_chars:
                skips_len += 1
                break

            # passed all checks → take it
            run.append(dict(cand))
            i += 1

        if len(run) == 1:
            out.append(run[0])
            continue

        # --- safety: quote-glyph budget before merge ---
        before_glyphs = sum(row_qglyphs(r) for r in run)

        # Merge text (normalize whitespace only)
        merged_text = " ".join(
            (r.get("text") or "").strip() for r in run if (r.get("text") or "").strip()
        )
        merged_text = re.sub(r"\s+\n\s+|\s{2,}", " ", merged_text).strip()
        merged_text = _fix_tokenization_gaps(merged_text)

        # --- safety: quote-glyph budget after merge ---
        after_glyphs = qglyphs(merged_text)

        if after_glyphs < before_glyphs:
            skips_glyph += 1
            for r in run:
                out.append(r)
            continue

        merged = dict(run[0])
        merged["text"] = merged_text
        merged["is_quote"] = True
        merged["speaker"] = speaker_of(run[0]) or "Unknown"

        if any(r.get("_lock_speaker") for r in run):
            merged["_lock_speaker"] = True
            merged["_locked_to"] = locked_to(run[0]) or merged["speaker"]
            merged["_lock_reason"] = "merge_same_speaker"

        for rr in run[1:]:
            try:
                merged = _merge_meta_keep_best(merged, rr)
            except Exception:
                for k in ("_qscore", "_cid", "_enlp_conf", "_span_lo", "_span_hi"):
                    if rr.get(k) and not merged.get(k):
                        merged[k] = rr.get(k)

        out.append(merged)
        merges += len(run) - 1

        try:
            frag_l = (run[0].get("text", "")[:40]).replace("\n", " ")
            frag_r = (run[-1].get("text", "")[-40:]).replace("\n", " ")
            log(
                f"[merge-run] speaker='{merged['speaker']}' parts={len(run)} glyphs {before_glyphs}->{after_glyphs} | '{frag_l} … {frag_r}'"
            )
        except Exception:
            pass

    try:
        DBG["merge_quote_runs_merges"] = DBG.get("merge_quote_runs_merges", 0) + merges
        DBG["merge_quote_runs_skips_lock_conflict"] = (
            DBG.get("merge_quote_runs_skips_lock_conflict", 0) + skips_conflict
        )
        DBG["merge_quote_runs_skips_flags"] = (
            DBG.get("merge_quote_runs_skips_flags", 0) + skips_flags
        )
        DBG["merge_quote_runs_skips_glyph"] = (
            DBG.get("merge_quote_runs_skips_glyph", 0) + skips_glyph
        )
        DBG["merge_quote_runs_skips_length"] = (
            DBG.get("merge_quote_runs_skips_length", 0) + skips_len
        )
        DBG["merge_quote_runs_skips_turn_boundary"] = (
            DBG.get("merge_quote_runs_skips_turn_boundary", 0) + skips_turn
        )
        DBG["merge_quote_runs_skips_rid_gap"] = (
            DBG.get("merge_quote_runs_skips_rid_gap", 0) + skips_ridgap
        )
        DBG["merge_quote_runs_skips_guard"] = (
            DBG.get("merge_quote_runs_skips_guard", 0) + skips_guard
        )
    except Exception:
        pass

    return out


def _norm_inline(s: str) -> str:
    # normalize curly quotes and whitespace before comparing
    return re.sub(r"\s+", " ", _norm_unicode_quotes(s or "").strip())


def _speaker_confidence(r: dict) -> float:
    """
    Higher = more trustworthy speaker assignment.
    Locked attributions are strongest; next, rows with a .quotes char_id or high qscore.
    """
    if r.get("_lock_speaker"):
        return 10.0
    c = 0.0
    if r.get("_cid") is not None:
        c += 3.0
    c += float(r.get("_qscore", 0.0) or 0.0)
    if r.get("speaker") not in ("Narrator", "Unknown", None, ""):
        c += 0.5
    return c


def _merge_meta_keep_best(base: dict, other: dict) -> dict:
    """Merge metadata from two duplicate rows, keeping the stronger side-channel info."""
    r = dict(base)
    if float(other.get("_qscore", 0.0) or 0.0) > float(r.get("_qscore", 0.0) or 0.0):
        r["_qscore"] = other["_qscore"]
    if r.get("_cid") is None and other.get("_cid") is not None:
        r["_cid"] = other["_cid"]
    if r.get("_src") is None and other.get("_src") is not None:
        r["_src"] = other["_src"]
    return r


# --- Adjacent dedupe using normalized text + speaker confidence (instrumented) ---
def _dedupe_adjacent_quotes(rows: list[dict]) -> list[dict]:
    """
    Remove/merge adjacent duplicates or near-duplicates.
    Cases handled (in order):
      1) Exact same normalized text, same quote/narration kind:
         keep the one with higher _speaker_confidence, merge metadata.
      2) One text is a substring of the other (e.g., split artifact):
         keep the longer, merge metadata from the other.
      3) Same speaker & kind, tiny punctuation-only diffs:
         prefer the one with higher confidence.
    """
    if not rows:
        return rows

    try:
        DBG.setdefault("dedupe_pairs_evaluated", 0)
        DBG.setdefault("dedupe_pairs_merged", 0)
        DBG.setdefault("dedupe_confidence_wins", 0)
        DBG.setdefault("dedupe_length_wins", 0)
    except Exception:
        pass

    out: list[dict] = []
    i = 0
    n = len(rows)

    def _kind(r):  # quote vs narr
        return bool(r.get("is_quote"))

    while i < n:
        a = rows[i]
        if i == n - 1:
            out.append(a)
            break

        b = rows[i + 1]

        # only consider dedupe if same kind (quote vs narration)
        if _kind(a) != _kind(b):
            out.append(a)
            i += 1
            continue

        try:
            DBG["dedupe_pairs_evaluated"] += 1
        except Exception:
            pass

        # normalize text for comparison
        ta = _norm_inline(a.get("text") or "")
        tb = _norm_inline(b.get("text") or "")

        same_speaker = a.get("speaker") == b.get("speaker")

        merged = False

        # (1) exact text match
        if ta == tb and ta != "":
            sp_a = a.get("speaker") or ""
            sp_b = b.get("speaker") or ""
            same_speaker = sp_a == sp_b
            compat = (
                same_speaker
                or (
                    sp_a in ("Unknown", "Narrator", "")
                    and sp_b not in ("Unknown", "Narrator", "")
                )
                or (
                    sp_b in ("Unknown", "Narrator", "")
                    and sp_a not in ("Unknown", "Narrator", "")
                )
            )
            if compat:
                ca = _speaker_confidence(a)
                cb = _speaker_confidence(b)
                keep, drop = (a, b) if ca >= cb else (b, a)

                # prefer the one with a real, locked, or known speaker when confidence ties
                if ca == cb:
                    ka = sp_a not in ("Unknown", "Narrator", "")
                    kb = sp_b not in ("Unknown", "Narrator", "")
                    if ka != kb:
                        keep, drop = (a, b) if ka else (b, a)
                    elif bool(a.get("_lock_speaker")) != bool(b.get("_lock_speaker")):
                        keep, drop = (a, b) if a.get("_lock_speaker") else (b, a)

                keep = _merge_meta_keep_best(keep, drop)
                out.append(keep)
                i += 2
                merged = True

        # (2) substring near-dup (one contains the other)
        elif (ta and tb) and (ta in tb or tb in ta) and same_speaker:
            # keep the longer text; merge meta from the shorter
            if len(tb) > len(ta):
                keep, drop = (b, a)
            else:
                keep, drop = (a, b)
            try:
                DBG["dedupe_length_wins"] += 1
            except Exception:
                pass
            keep = _merge_meta_keep_best(keep, drop)
            out.append(keep)
            i += 2
            merged = True

        # (3) tiny punctuation-only diffs and same speaker
        elif same_speaker and (
            ta.replace(",", "").replace(".", "") == tb.replace(",", "").replace(".", "")
        ):
            ca = _speaker_confidence(a)
            cb = _speaker_confidence(b)
            keep, drop = (a, b) if ca >= cb else (b, a)
            if ca != cb:
                try:
                    DBG["dedupe_confidence_wins"] += 1
                except Exception:
                    pass
            keep = _merge_meta_keep_best(keep, drop)
            out.append(keep)
            i += 2
            merged = True

        if merged:
            try:
                DBG["dedupe_pairs_merged"] += 1
            except Exception:
                pass
            continue

        # no dedupe this pair; keep A and advance by 1
        out.append(a)
        i += 1

    return out


def _dedupe_narrator_quote_duplicates(rows: list[dict]) -> list[dict]:
    """
    If two adjacent rows contain the same text except for quote glyphs and
    one is Narrator (is_quote=False) while the other is a quote (is_quote=True),
    keep the quote and drop the narrator duplicate. Preserves metadata on the kept row.
    """
    if not rows:
        return rows

    def _core_text(s: str) -> str:
        # normalize quotes then strip leading/trailing quote glyphs and whitespace
        t = _norm_unicode_quotes(s or "")
        t = re.sub(r'^\s*[“"»]\s*', "", t)
        t = re.sub(r'\s*[”"«]\s*$', "", t)
        return t.strip()

    out = []
    i = 0
    n = len(rows)
    drops = 0

    while i < n:
        a = rows[i]
        if i + 1 < n:
            b = rows[i + 1]
            a_is_q = bool(a.get("is_quote"))
            b_is_q = bool(b.get("is_quote"))

            # Case 1: Narrator then Quote
            if (not a_is_q) and b_is_q:
                if _core_text(a.get("text")) and _core_text(
                    a.get("text")
                ) == _core_text(b.get("text")):
                    out.append(dict(b))  # keep the quoted version
                    i += 2
                    drops += 1
                    continue

            # Case 2: Quote then Narrator
            if a_is_q and (not b_is_q):
                if _core_text(a.get("text")) and _core_text(
                    a.get("text")
                ) == _core_text(b.get("text")):
                    out.append(dict(a))  # keep the quoted version
                    i += 2
                    drops += 1
                    continue

        out.append(dict(a))
        i += 1

    try:
        DBG["dedupe_narrator_quote_dups"] = (
            DBG.get("dedupe_narrator_quote_dups", 0) + drops
        )
    except Exception:
        pass

    return out


def _global_dedupe_by_text_and_speaker(rows: list[dict]) -> list[dict]:
    """
    Remove duplicate rows based on (normalized_text, speaker, is_quote) across the ENTIRE list,
    not just adjacent rows. This catches duplicates that are separated by narration or other content.
    
    For each unique (text, speaker, is_quote) tuple, keeps only the FIRST occurrence.
    Tracks removed duplicates in DBG stats.
    """
    if not rows:
        return rows
    
    seen = set()
    out = []
    removed_count = 0
    
    for row in rows:
        # Create a signature for this row
        text = _norm_inline(row.get("text", "")).strip()
        speaker = (row.get("speaker") or "").strip()
        is_quote = bool(row.get("is_quote"))
        
        # Skip empty text rows
        if not text:
            out.append(row)
            continue
        
        signature = (text, speaker, is_quote)
        
        if signature in seen:
            # This is a duplicate - skip it
            removed_count += 1
            continue
        
        # First occurrence - keep it
        seen.add(signature)
        out.append(row)
    
    try:
        DBG["global_dedupe_removed"] = removed_count
    except Exception:
        pass
    
    if removed_count > 0:
        log(f"[global_dedupe] removed {removed_count} duplicate rows")
    
    return out


# ---------- Alias + Canonical map (strict, multi-token-first) ----------


def _split_camel(s: str) -> str:
    # "LennartJohnson" -> "Lennart Johnson"
    return re.sub(r"(?<!^)([A-Z])", r" \1", s or "").strip()


def _best_canonical_name(entry: dict) -> str | None:
    """
    Choose the most descriptive canonical for an entry from characters.json:
    prefer multi-token 'canonical_name' or split CamelCase normalized_name.
    """
    can = (entry.get("canonical_name") or "").strip()
    norm = (entry.get("normalized_name") or "").strip()
    # try split CamelCase on normalized_name if it has no spaces
    if norm and " " not in norm:
        norm_spaced = _split_camel(norm)
    else:
        # normalized_name already spaced or empty
        norm_spaced = norm

    candidates = [
        c for c in [can, norm_spaced, norm, can.title() if can else None] if c
    ]
    # prefer the one with most tokens
    candidates.sort(key=lambda x: len(x.split()), reverse=True)
    if not candidates:
        return None
    return normalize_name(candidates[0]).title()


def _load_characters_full(output_dir: str, prefix: str) -> list[dict]:
    """
    Load <prefix>.characters.json if present (fallbacks included).
    Return the list under 'characters' (or []).
    """
    paths = [
        os.path.join(output_dir, f"{prefix}.characters.json"),
        os.path.join(output_dir, "book_input.characters.json"),
        os.path.join(output_dir, "characters.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                chars = data.get("characters", []) or []
                if chars:
                    log(f"[chars] loaded {len(chars)} from {os.path.basename(p)}")
                    return chars
            except Exception as e:
                log(f"[chars] failed to read {p}: {e}")
    log("[chars] no characters.json found")
    return []


def _load_alias_overrides(output_dir: str, prefix: str) -> dict[str, list[str]]:
    """
    Optional manual overrides: <prefix>.aliases.json
    {
      "aliases": {
        "Lennart Johnson": ["Len","Johnson","Lenny"],
        "Mike Jones": ["Charlie","Jones","Chuck"],
        "Steve King": ["Steve","King"]
      }
    }
    """
    paths = [
        os.path.join(output_dir, f"{prefix}.aliases.json"),
        os.path.join(output_dir, "book_input.aliases.json"),
        os.path.join(output_dir, "aliases.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                ali = data.get("aliases", {}) or {}
                if ali:
                    log(
                        f"[aliases] loaded {len(ali)} canonical entries from {os.path.basename(p)}"
                    )
                    # normalize keys/values for safety
                    out = {}
                    for k, arr in ali.items():
                        k2 = normalize_name(k).title()
                        vals = [normalize_name(x).title() for x in (arr or []) if x]
                        out[k2] = vals
                    return out
            except Exception as e:
                log(f"[aliases] failed to read {p}: {e}")
    return {}


def _prefer_multi_token_groups(
    canonicals: list[str],
) -> tuple[list[str], dict[str, str]]:
    """
    If we have 'Johnson' and 'Lennart Johnson', prefer the latter.
    Returns (preferred_list, demotions) where demotions maps
    single-token -> chosen multi-token canonical.
    """
    by_last = {}
    for c in canonicals:
        toks = c.split()
        last = toks[-1] if toks else c
        by_last.setdefault(last, set()).add(c)

    preferred = set()
    demotions = {}
    for last, group in by_last.items():
        # pick the canonical with the most tokens
        best = max(group, key=lambda x: len(x.split()))
        preferred.add(best)
        # demote others in the group to the multi-token 'best'
        for g in group:
            if g != best:
                demotions[g] = best
    return sorted(preferred), demotions


def _build_alias_map_strict(output_dir: str, prefix: str, qmap=None) -> dict:
    """
    Build a STRICT alias map token->canonical using what we already loaded via
    _load_simple_whitelist (CANON_WHITELIST, WH_ALIAS). Optionally merge a local
    overrides file if present, but keep ONLY unique tokens across canonicals.

    Accepts qmap (ignored here) so callers can pass it without error.
    """
    import json
    import os
    import re

    global CANON_WHITELIST, WH_ALIAS

    # Start from the unique alias tokens we loaded from characters_simple.json
    alias_inv = dict(WH_ALIAS or {})

    # Try to load optional overrides in the shape:
    # { "aliases": { "John Smith": ["Zack","Smith"], ... } }
    overrides = None
    try_paths = [
        os.path.join(output_dir, f"{prefix}.aliases.json"),
        os.path.join(output_dir, "book_input.aliases.json"),
        os.path.join(output_dir, "aliases.json"),
    ]
    for p in try_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                ov = data.get("aliases", data)
                if isinstance(ov, dict) and ov:
                    overrides = ov
                    log(f"[alias] loaded overrides from {os.path.basename(p)}")
                    break
            except Exception as e:
                log(f"[alias] failed to read {p}: {e}")

    # If there are overrides, rebuild the token->canonical map with uniqueness
    if overrides:
        from collections import defaultdict

        def _norm(s: str) -> str:
            return normalize_name(s or "").strip()

        bag = defaultdict(set)

        # Seed with existing unique tokens
        for tok, can in alias_inv.items():
            tl = _norm(tok).lower()
            if tl:
                bag[tl].add(_norm(can).title())

        # Add override tokens
        for can, arr in overrides.items():
            can_norm = _norm(can).title()
            if not can_norm:
                continue
            for a in arr or []:
                for tok in re.split(r"\s+", _norm(a)):
                    tl = tok.lower()
                    if tl:
                        bag[tl].add(can_norm)

        # Keep ONLY tokens that point to exactly one canonical
        alias_inv = {}
        for tok, cans in bag.items():
            if len(cans) == 1:
                alias_inv[tok] = list(cans)[0]

    log(
        f"[alias] strict map built: canonicals={len(CANON_WHITELIST)} tokens={len(alias_inv)}"
    )
    return alias_inv


# Ensure globals exist
if "CANON_WHITELIST" not in globals():
    CANON_WHITELIST = set()
if "WH_ALIAS" not in globals():
    WH_ALIAS = {}


def _whitelist_clamp(name: str) -> str | None:
    """
    Snap an arbitrary name/mention to a canonical full name using:
      1) direct canonical match (title-cased normalized string),
      2) full-string alias map (WH_ALIAS),
      3) per-token alias votes (unique winner),
      4) last-name fallback if it doesn't conflict.

    Returns the canonical string or None if no unique clamp.
    """
    if not name:
        return None

    # normalize once
    base_norm = normalize_name(name).strip()
    if not base_norm:
        return None
    base_title = base_norm.title()

    # 1) direct canonical match
    if base_title in CANON_WHITELIST:
        return base_title

    # 2) full-string alias map (e.g., "charlie" -> "Mike Jones")
    full_key = base_norm.lower()
    can = WH_ALIAS.get(full_key)
    if can:
        return can

    # 3) per-token unique vote
    import re

    tokens = [t for t in re.split(r"\s+", base_norm) if t]
    if tokens:
        votes = {WH_ALIAS.get(t.lower()) for t in tokens if WH_ALIAS.get(t.lower())}
        votes.discard(None)
        if len(votes) == 1:
            return next(iter(votes))

        # 4) last-name fallback (non-conflicting)
        last = tokens[-1].lower()
        last_map = WH_ALIAS.get(last)
        if last_map and ((not votes) or (last_map in votes)):
            return last_map

    return None


# --- Cleaning ---
def clean_results(results, qmap=None, alias_inv=None):
    """
    Post-process BookNLP results to clean up noisy attributions,
    while preserving book order.
    """

    # Local helper so we don't forget to pass the right variables around
    def _has_adjacent_quote(idx: int, results_list, cleaned_list):
        prev_is_quote = (
            idx > 0
            and cleaned_list
            and looks_like_direct_speech((cleaned_list[-1].get("text") or ""))
        )
        next_is_quote = (idx + 1) < len(results_list) and looks_like_direct_speech(
            ((results_list[idx + 1].get("text") or ""))
        )
        return prev_is_quote or next_is_quote

    # Local normalizer for quote alignment
    def _norm_for_match(s: str) -> str:
        import re

        if not s:
            return ""
        s = (
            s.replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2018", "'")
            .replace("\u2019", "'")
        )
        return re.sub(r"\s+", " ", s).strip()

    cleaned = []

    for idx, r in enumerate(results):
        # --- text normalization (added detokenizer here)
        text = r.get("text", "") or ""
        text = _fix_tokenization_gaps(_norm_unicode_quotes(text)).strip()
        is_q = looks_like_direct_speech(text)

        # skip empty lines after normalization
        if not text:
            continue

        # speaker normalization
        speaker = (r.get("speaker", "") or "").strip()
        if speaker:
            # Preserve multi-word capitalization (Title Case), not .capitalize()
            speaker = speaker.title()
        else:
            speaker = "Narrator"

        # Drop UNKNOWN and generic/group speakers
        if speaker.lower() in {"unknown", "???"} or _is_banned(speaker):
            speaker = "Narrator"

        # --- Prefer EnglishBookNLP quote assignments when available ---
        row_cid = None
        row_qscore = None
        if is_q and ("ENLP_QUOTE_INDEX" in globals()) and ENLP_QUOTE_INDEX:
            try:
                norm = _norm_for_match(text)
                qrows = ENLP_QUOTE_INDEX.get(norm)
                cid = None
                if qrows:
                    # exact text match to a BookNLP quote
                    cid = qrows[0].get("char_id")
                else:
                    # soft contains: handle short quotes embedded in longer strings
                    if len(norm) >= 12:
                        for k, rows_k in ENLP_QUOTE_INDEX.items():
                            if k and len(k) >= 12 and k in norm:
                                cid = rows_k[0].get("char_id")
                                break
                if cid is not None:
                    # prefer ENLP_CID2CANON, fallback to CJ_MAP when present
                    if ("ENLP_CID2CANON" in globals()) and (cid in ENLP_CID2CANON):
                        speaker = ENLP_CID2CANON[cid]
                    elif (
                        ("CJ_MAP" in globals())
                        and isinstance(CJ_MAP, dict)
                        and (cid in CJ_MAP)
                    ):
                        speaker = CJ_MAP[cid]
                    row_cid = cid
            except Exception:
                # swallow and proceed to qmap fallback
                pass

        # --- Fallback: Reassign quotes using .quotes / CJ_MAP when available ---
        # Prefer ENLP index (exact, then fuzzy) if available
        if is_q and ENLP_QUOTE_INDEX:
            try:
                _hit, _score = _enlp_lookup_quote(text)
            except Exception:
                _hit, _score = (None, None)
            if _hit and (_hit.get("char_id") is not None):
                cid = _hit["char_id"]
                name = ENLP_CID2CANON.get(cid)
                if name and not _is_banned(name):
                    speaker = name
                    # stash meta so later passes don’t flip it
                    r["_cid"] = cid
                    r["_qscore"] = float(_score or 1.0)
            # don’t hard-lock here; we’ll lock after we build row_out

        if (
            is_q
            and qmap is not None
            and (speaker in ("Narrator", "Unknown") or speaker.strip() == "")
        ):
            qrow = None
            score = None
            try:
                # Prefer your BookNLP quote aligner if present
                qrow, score = _best_quote_for_text(text, qmap)
            except Exception:
                qrow = None
                score = None
            if qrow:
                cid2 = qrow.get("char_id")
                if (
                    "CJ_MAP" in globals()
                    and isinstance(CJ_MAP, dict)
                    and cid2 in CJ_MAP
                ):
                    speaker = CJ_MAP[cid2]
                else:
                    # Fallback to your existing remap helper
                    try:
                        qs = reassign_from_quotes(text, qmap, alias_inv or {})
                        if qs and not _is_banned(qs):
                            speaker = qs
                    except Exception:
                        pass
                row_cid = cid2 if cid2 is not None else row_cid
                row_qscore = float(score) if score is not None else row_qscore
            else:
                # No confident quote row found; try your existing helper
                try:
                    qs = reassign_from_quotes(text, qmap, alias_inv or {})
                    if qs and not _is_banned(qs):
                        speaker = qs
                except Exception:
                    pass

        # Demote attribution-only lines ("said X") and drop if there's no dialogue
        if not is_q:
            if _looks_like_attribution_fragment(text):
                log(f"Attribution reassigned to Narrator: {text}")
                speaker = "Narrator"

            # Drop or keep pure attribution fragments with no content
            if _attrib_only(text):
                if KEEP_ATTRIB_TEXT:
                    # keep as Narrator (still demoted above)
                    log(f"Attribution-only kept as Narrator: {text}")
                else:
                    log(f"Attribution-only dropped: {text}")
                    continue

        # Finalize speaker label: sanitize junk, canonicalize role, alias-correct singles
        speaker = _sanitize_person_name(speaker) or "Narrator"
        if speaker != "Narrator":
            speaker = _alias_correct(speaker, alias_inv or {})

        # Junk filter (keep very short if they are direct speech)
        if not is_q and is_junk_line(text):
            log(f"Junk filtered: {speaker} | {text}")
            continue

        # Guard: only force non-dialogue to Narrator when it's truly narration.
        # BUT: if speaker is a real character (not Narrator/Unknown), keep it as quote
        # This handles BookNLP quote continuations that lack opening quote marks
        if not is_q:
            # If speaker is a real character, this is likely a quote continuation
            if speaker not in ("Narrator", "Unknown", ""):
                # Keep as quote continuation
                is_q = True
                row_out = {"speaker": speaker, "text": text, "is_quote": is_q}
                if row_cid is not None:
                    row_out["_cid"] = row_cid
                if row_qscore is not None:
                    row_out["_qscore"] = row_qscore
                cleaned.append(row_out)
                continue
            
            # don't force if this line is an attribution fragment (e.g., 'said King.')
            # or if there is an adjacent quote that could receive the attribution
            if (not _looks_like_attribution_fragment(text)) and (
                not _has_adjacent_quote(idx, results, cleaned)
            ):
                if speaker != "Narrator":
                    log(
                        f"[clean] non-quote forced Narrator early: '{speaker}' -> Narrator | {text[:60]}…"
                    )
                speaker = "Narrator"

        # Build the outgoing row (preserve is_quote for downstream passes)
        row_out = {"speaker": speaker, "text": text, "is_quote": is_q}
        if row_cid is not None:
            row_out["_cid"] = row_cid
        if row_qscore is not None:
            row_out["_qscore"] = row_qscore

        # If ENLP filled a cid/name above, lock it now
        if is_q and row_out.get("_cid") is not None:
            row_out["_lock_speaker"] = True
            row_out["_lock_reason"] = "enlp_quote"

        # Lock when explicit in-text attribution agrees with the chosen speaker
        # (prevents later heuristics from flipping it)
        try:
            if speaker not in ("Narrator", "Unknown") and _explicit_matches_speaker(
                text, speaker
            ):
                row_out["_lock_speaker"] = True
                row_out["_lock_reason"] = "explicit_name_agreement"
        except Exception:
            pass

        cleaned.append(row_out)

    # --- Final passes below (DO NOT early-return above) ---

    # Merge single-token speakers into the most frequent multi-token canonical (if available)
    try:
        cleaned = _merge_speakers(cleaned)
    except Exception:
        # keep moving even if merge isn't available
        pass

    # Demote pronoun-like speakers to Narrator after merge (just in case)
    final = []
    for row in cleaned:
        try:
            sp_norm = normalize_name(row.get("speaker", "")).lower()
        except Exception:
            sp_norm = (row.get("speaker") or "").lower()
        if sp_norm in PRONOUN_BLACKLIST:
            final.append(
                {
                    "speaker": "Narrator",
                    "text": row.get("text", ""),
                    "is_quote": row.get(
                        "is_quote", looks_like_direct_speech(row.get("text") or "")
                    ),
                    "_cid": row.get("_cid"),
                    "_qscore": row.get("_qscore"),
                    "_lock_speaker": row.get("_lock_speaker"),
                    "_lock_reason": row.get("_lock_reason"),
                }
            )
        else:
            final.append(row)

    return final


def enforce_dialogue_narration_rule(results, qmap, alias_inv):
    """
    Normalize rows so that:
      - True quoted lines (has real quote spans) are is_quote=True and never 'Narrator'
      - Promoted dialogue beats (no glyphs but flagged) remain is_quote=True and keep speaker
      - Non-quote lines default to Narrator unless locked or look like attribution fragments
    """
    if not results:
        return results

    def _glyph_count(s: str) -> int:
        s = s or ""
        return s.count('"') + s.count("“") + s.count("”") + s.count("‘") + s.count("’")

    def _has_quote_span(txt: str) -> bool:
        try:
            spans = _quote_spans(_norm_unicode_quotes(txt or ""))
            return bool(spans)
        except Exception:
            return False

    PRESERVE_KEYS = (
        "_promoted_quote",
        "_post_quote_promoted",
        "_pre_quote_promoted",
        "_attrib_triplet_promoted",
        "_midquote_tail_promoted",
    )

    before = sum(_glyph_count(r.get("text") or "") for r in results)
    out = []
    for idx, r in enumerate(results):
        rr = dict(r)
        txt = rr.get("text") or ""
        preserve = any(rr.get(k) for k in PRESERVE_KEYS)

        # Decide is_quote
        if preserve:
            rr["is_quote"] = True
        else:
            rr["is_quote"] = _has_quote_span(txt)

        # Quotes (glyph or promoted) can’t be Narrator (unless hard-locked)
        if (
            rr.get("is_quote")
            and (rr.get("speaker") == "Narrator")
            and not rr.get("_lock_speaker")
        ):
            rr["speaker"] = "Unknown"

        # Non-quote lines → Narrator, except attribution-like fragments (don’t stomp)
        if (
            not rr.get("is_quote")
            and (rr.get("speaker") not in ("Narrator", "Unknown", None, ""))
            and not rr.get("_lock_speaker")
        ):
            try:
                looks_attrib = _looks_like_attribution_fragment(txt)
            except Exception:
                looks_attrib = False
            if not looks_attrib:
                rr["speaker"] = "Narrator"

        out.append(rr)

    after = sum(_glyph_count(r.get("text") or "") for r in out)
    if after != before:
        log(
            f"[ednr] WARNING: glyph_count changed {before} -> {after} (should never happen)"
        )

    return out


def _inherit_microquote_speakers(rows, alias_inv=None):
    """
    If a quote is Unknown and very short (<= 2 tokens),
    inherit its speaker from the nearest neighboring quote.
    If both neighbors exist and agree (and are not Unknown/Narrator), require agreement.
    (alias_inv is currently unused but reserved for future alias-aware checks)
    """

    def token_count(s: str | None) -> int:
        return len(re.findall(r"[A-Za-z0-9']+", s or ""))

    out = rows
    n = len(out)
    for i, r in enumerate(out):
        if not r.get("is_quote"):
            continue
        if (r.get("speaker") or "Unknown") != "Unknown":
            continue
        if token_count(r.get("text", "")) > 2:
            continue

        # find previous/next quote speakers
        prev = next_ = None
        for j in range(i - 1, -1, -1):
            if out[j].get("is_quote"):
                prev = out[j].get("speaker")
                break
        for j in range(i + 1, n):
            if out[j].get("is_quote"):
                next_ = out[j].get("speaker")
                break

        cand = None
        if prev and next_ and prev == next_ and prev not in ("Unknown", "Narrator"):
            cand = prev
        elif prev and prev not in ("Unknown", "Narrator"):
            cand = prev
        elif next_ and next_ not in ("Unknown", "Narrator"):
            cand = next_

        if cand:
            out[i]["speaker"] = cand
            frag = (out[i].get("text", "")[:40]).replace("\n", " ")
            log(f"[microquote] inherit -> '{cand}' | {frag}…")
    return out


def dump_gui_rows_txt(rows, path):
    """
    Write exactly what will be sent to the GUI so we can diff it easily.
    """
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    except Exception:
        pass
    try:
        with open(path, "w", encoding="utf-8") as f:
            for i, r in enumerate(rows or []):
                f.write(f"--- ROW {i:04d} ---\n")
                f.write(f"speaker: {(r.get('speaker') or '')}\n")
                f.write(f"is_quote: {bool(r.get('is_quote'))}\n")
                f.write("text:\n")
                t = (r.get("text") or "").rstrip()
                f.write(t + ("\n" if not t.endswith("\n") else ""))
                f.write("\n")
    except Exception as e:
        try:
            log(f"[dump_gui_rows_txt] failed: {e}")
        except Exception:
            pass


def _qa_ensure_audit_header(output_dir: str, prefix: str):
    """Ensure {prefix}.quote_audit.tsv exists with a header row."""
    try:
        if not output_dir:
            return
        path = os.path.join(output_dir, f"{prefix}.quote_audit.tsv")
        if os.path.exists(path):
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "prev_stage\tstage\trid\tissue\tspan_prev\tspan_cur\tglyph_prev\tglyph_cur\t"
                "bal_prev\tbal_cur\tisq_prev\tisq_cur\tspeaker_prev\tspeaker_cur\t"
                "excerpt_prev\texcerpt_cur\n"
            )
    except Exception as e:
        _qa_safe_log(f"[qa] init audit header failed: {e}")


def emit_stage_stats(output_dir: str, prefix: str):
    """
    Summarize key metrics per stage into {prefix}.stage_stats.tsv using the
    series captured by the quote auditor (_qa_collect_stage).
    """
    try:
        series = DBG.get("_qa_series") or []
        if not output_dir or not series:
            return
        path = os.path.join(output_dir, f"{prefix}.stage_stats.tsv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "stage\trows\tquote_rows\tunknown_quote_rows\tnarrator_quote_rows\tglyphs\n"
            )
            for stage, snap in series:
                rows = len(snap)
                qrows = sum(1 for r in snap if r.get("is_quote"))
                unknown_q = sum(
                    1
                    for r in snap
                    if r.get("is_quote") and (r.get("speaker") in (None, "", "Unknown"))
                )
                narr_q = sum(
                    1
                    for r in snap
                    if r.get("is_quote") and r.get("speaker") == "Narrator"
                )
                glyphs = sum(int(r.get("glyph_cnt") or 0) for r in snap)
                f.write(f"{stage}\t{rows}\t{qrows}\t{unknown_q}\t{narr_q}\t{glyphs}\n")
    except Exception as e:
        try:
            log(f"[stage_stats] failed: {e}")
        except Exception:
            pass


# --- Main Attribution ---
def run_attribution(text, model="big", pipeline="entity,quote,coref"):
    """
    Run BookNLP and process results into ordered speaker/text segments.
    """
    tmpdir = tempfile.mkdtemp(prefix="booknlp_")
    try:
        input_path = os.path.join(tmpdir, "book_input.txt")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(text)

        output_dir = os.path.join("output", f"booknlp_{uuid.uuid4().hex[:8]}")
        os.makedirs(output_dir, exist_ok=True)

        prefix = Path(input_path).stem

        log("--- New Attribution Run ---")
        
        # Reset ALL global state to ensure clean processing for each chapter
        global DBG, CANON_WHITELIST, SURNAME_TO_CANON, WH_ALIAS, QMAP_CACHE, ALIAS_INV_CACHE, CJ_MAP, CLUSTER_STATS
        
        # Reset debug counters to a fresh dict
        DBG = {
            "reassert_strict_runs": 0,
            "reassert_flag_changes": 0,
            "lonely_quote_stripped": 0,
            "narr_tail_splits": 0,
            "coalesce_skipped_kind": 0,
            "coalesce_skipped_quote2quote": 0,
            "coalesce_skipped_attribfrag": 0,
            "coalesce_merges": 0,
        }
        
        # Reset character detection state
        CANON_WHITELIST = set()
        SURNAME_TO_CANON = {}
        WH_ALIAS = {}
        QMAP_CACHE = None
        ALIAS_INV_CACHE = {}
        CJ_MAP = {}
        CLUSTER_STATS = {}
        
        log(f"[GlobalReset] All state variables reset for new chapter processing")
        log(f"Model={model}, Pipeline={pipeline}")
        log(f"TempDir={tmpdir}, OutputDir={output_dir}, Prefix={prefix}")

        run_booknlp(
            input_path=input_path,
            output_dir=output_dir,
            prefix=prefix,
            model=model,
            pipeline=pipeline,
        )

        book_file = os.path.join(output_dir, prefix + ".book.txt")
        if not os.path.exists(book_file):
            log(f"ERROR: Missing {book_file}")
            return []

        # ------------------------------
        # Characters: load clusters, stats (for char_id preference & gating)
        # ------------------------------
        alias_inv = {}
        cjson = os.path.join(output_dir, prefix + ".characters.json")
        cj = None
        if os.path.exists(cjson):
            with open(cjson, "r", encoding="utf-8", errors="replace") as f:
                cj = json.load(f)
            canonicals = [
                c.get("canonical_name") or c.get("normalized_name")
                for c in cj.get("characters", [])
            ]
            # (early) alias map from canonicals (will be replaced later by strict builder)
            alias_inv = build_alias_map([c for c in canonicals if c])

        # Fill globals used by reassign_from_quotes (already declared global at top of function)
        CJ_MAP = {}
        CLUSTER_STATS = {}

        if cj:
            chars = cj.get("characters", []) or []
            for i, c in enumerate(chars):
                # accept id under several possible keys, else fall back to index
                raw_id = c.get("id", c.get("char_id", c.get("cluster_id", i)))
                try:
                    cid = int(raw_id)
                except Exception:
                    cid = i

                name = (
                    c.get("canonical_name") or c.get("normalized_name") or c.get("name")
                )
                if name:
                    CJ_MAP[cid] = name

                # mentions may be dicts, lists, or missing; be defensive
                mentions = c.get("mentions", {}) or {}
                proper_list = mentions.get("proper") or []
                if isinstance(proper_list, list):
                    proper_count = len(proper_list)
                elif isinstance(proper_list, int):
                    proper_count = proper_list
                else:
                    proper_count = 0

                total_count = c.get("count", 0)
                try:
                    total_count = int(total_count)
                except Exception:
                    total_count = 0

                CLUSTER_STATS[cid] = {"count": total_count, "proper": proper_count}

                # Merge ENLP zone counts (per-cluster) into our CLUSTER_STATS
                try:
                    from app.core.english_booknlp import (
                        ENLP_CLUSTER_STATS as _ENLP_ZONE,
                    )
                except Exception:
                    _ENLP_ZONE = {"narr": {}, "quote": {}}

                try:
                    for cid, cnt in (_ENLP_ZONE.get("narr") or {}).items():
                        CLUSTER_STATS.setdefault(cid, {}).update({"narr": int(cnt)})
                    for cid, cnt in (_ENLP_ZONE.get("quote") or {}).items():
                        CLUSTER_STATS.setdefault(cid, {}).update({"quote": int(cnt)})
                    log("[mentions] merged ENLP zone counts into CLUSTER_STATS")
                except Exception as e:
                    log(f"[mentions] merge zone counts failed: {e}")

        # ------------------------------
        # Load the full-name-first simple map written by EnglishBookNLP
        # (reads <prefix>.characters_simple.json or a fallback)
        # ------------------------------
        _load_simple_whitelist(output_dir, prefix)

        # If the simple whitelist missed some legit characters, augment with well-named clusters
        AUGMENT_WHITELIST_FROM_CLUSTERS = True
        if AUGMENT_WHITELIST_FROM_CLUSTERS and CJ_MAP:
            added = 0
            soft = len(CANON_WHITELIST) < 15  # if whitelist is tiny, be more generous
            for cid, name in CJ_MAP.items():
                if _cluster_is_named_enough(
                    cid, min_prop=0.40 if soft else 0.50, min_mentions=2 if soft else 4
                ):
                    if name not in CANON_WHITELIST:
                        CANON_WHITELIST.add(name)
                        for t in re.split(r"\s+", normalize_name(name)):
                            if t:
                                WH_ALIAS[t.lower()] = name
                        added += 1
            if added:
                log(f"[whitelist] augmented with {added} cluster canonical names")

        # ------------------------------
        # Quotes map (normalize + cache)
        # ------------------------------
        qmap = load_quotes_map(output_dir, prefix)
        qmap = _precompute_norm_quotes(qmap)
        log(f"[quotes] normalized={len(qmap)}")
        # Already declared global at top of function
        QMAP_CACHE = qmap
        _merge_quote_counts_into_cluster_stats(qmap)
        _ensure_cluster_defaults()

        # ------------------------------
        # ENLP caches (use fresh output_dir/prefix from this run)
        # ------------------------------
        # --- EnglishBookNLP caches (load once per run) ---
        # For this run, use the same output_dir/prefix we just produced.
        try:
            bootstrap_enlp_caches(output_dir, prefix)  # uses your run's outputs
            log(f"[enlp] caches initialized from: {output_dir}")
        except Exception as e:
            log(f"[enlp] init failed: {e}")

        # ------------------------------
        # Build strict, multi-token-first alias map (unique tokens only)
        # (pass qmap so we can also harvest frequent mentions if your builder uses them)
        # ------------------------------
        alias_inv = _build_alias_map_strict(output_dir, prefix, qmap=qmap)
        log(
            f"[alias] canonicals={len(CANON_WHITELIST)} unique_tokens={len(alias_inv)} cj={len(CJ_MAP)}"
        )

        SURNAME_TO_CANON = _build_surname_map(
            sorted(CANON_WHITELIST)
        )  # optional; safe if unused

        # NEW: cache for finalizer rescue (already declared global at top of function)
        ALIAS_INV_CACHE = build_alias_map(CANON_WHITELIST)  # last/first → canonical
        log(f"[alias] built inv map: {len(ALIAS_INV_CACHE)} tokens")

        # ------------------------------
        # Raw rows from processor (unchanged)
        # ------------------------------
        results = run_book_processor(book_file)
        log(f"Raw results: {len(results)} lines")
        if DEBUG_AUDIT:
            _audit_quotes(
                "after run_book_processor",
                [
                    {
                        "text": r.get("text"),
                        "is_quote": None,
                        "speaker": r.get("speaker"),
                    }
                    for r in results
                ],
            )
        # Merge consecutive Narrator lines early, before further processing
        log(f"[early-merge] BEFORE _merge_consecutive_narrator_rows: {len(results)} rows")
        # DEBUG: Check for "said Smith" before merge
        for i, row in enumerate(results):
            if "said Smith" in row.get("text", ""):
                log(f"[early-merge-before] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} text={row.get('text')}")
        
        results = _merge_consecutive_narrator_rows(results)
        log(f"[early-merge] AFTER _merge_consecutive_narrator_rows: {len(results)} rows")
        # DEBUG: Check for "said Smith" after merge
        for i, row in enumerate(results):
            if "said Smith" in row.get("text", ""):
                log(f"[early-merge-after] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} text={row.get('text')[:100]}")


        # ------------------------------
        # Attribution pipeline (trace-instrumented)
        # ------------------------------

        # 0) Early cleanup/normalization
        log(f"[clean] BEFORE clean_results: {len(results)} rows")
        # DEBUG: Check for "said Smith" before clean
        for i, row in enumerate(results):
            if "said Smith" in row.get("text", ""):
                log(f"[clean-before] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} text={row.get('text')[:80]}")
        
        results = clean_results(results, qmap, alias_inv)
        
        log(f"[clean] AFTER clean_results: {len(results)} rows")
        # DEBUG: Check for "said Smith" after clean
        for i, row in enumerate(results):
            if "said Smith" in row.get("text", ""):
                log(f"[clean-after] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} text={row.get('text')[:80]}")
        
        _qa_ensure_audit_header(output_dir, prefix)
        results = _qaudit("after clean_results", results, output_dir, prefix)
        if DEBUG_AUDIT:
            _audit_quotes("after clean_results", results)

        # DISABLED: book_processor now handles broken quote merging
        # results = _merge_broken_quote_fragments(results)
        # results = trace_stage("after merge_broken_quote_fragments", results, output_dir, prefix)

        # TRACE: init + first snapshot
        trace_init(output_dir, prefix, results)
        DBG["OUTDIR"] = output_dir  # enables writing TSVs to disk
        results = trace_stage("after clean_results", results, output_dir, prefix)

        # DISABLED: stitch_by_quote_balance was causing too much aggressive merging
        # that glued multiple speakers together. BookNLP's splits are usually correct.
        # If we need soft-wrap handling, it should be done more carefully.
        # results = _profile(
        #     "after stitch_by_quote_balance",
        #     _stitch_rows_by_quote_balance,
        #     results,
        #     output_dir,
        #     prefix,
        # )
        # results = _qaudit("after stitch_by_quote_balance", results, output_dir, prefix)
        # log(
        #     f"[stitch] runs={DBG.get('stitch_runs',0)} rows_glued={DBG.get('stitch_rows_glued',0)} chars_joined={DBG.get('stitch_chars_joined',0)}"
        # )
        # results = trace_stage(
        #     "after stitch_by_quote_balance", results, output_dir, prefix
        # )
        # 0a.5) Early seam split: break "…”he said" into quote + tail narration
        results = _profile(
            "after split_midquote_attrib_clauses_early",
            _split_midquote_attrib_clauses_early,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )

        # split mid-quote attribution clauses created/kept by stitching
        results = _profile(
            "after split_midquote_attrib_clauses_early",
            _split_midquote_attrib_clauses_early,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )
        results = trace_stage(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )

        # 0b) Strict reassert + sanity before any splits/peels
        results = _profile(
            "after reassert_quote_flags_strict (early)",
            _reassert_quote_flags_strict,
            results,
            output_dir,
            prefix,
        )
        results = _debug_assert_noquote_text_marked_quote(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = trace_stage(
            "after reassert_quote_flags_strict (early)", results, output_dir, prefix
        )

        # 1) Split multi-quote segments (dialogue vs narrator) and adjacent-quote clumps
        # before = len(results)
        # results = _profile("after split_multiquote_segments",
        #                split_multiquote_segments, results, output_dir, prefix, qmap, alias_inv)
        # results = _qaudit("after split_multiquote_segments", results, output_dir, prefix)
        # log(f"[split] segments: {before} -> {len(results)}")
        # if DEBUG_AUDIT: _audit_quotes("after split_multiquote_segments", results)
        # results = trace_stage("after split_multiquote_segments", results, output_dir, prefix)
        # _trace_glyph_budget("after split_multiquote_segments", results)

        # FIRST split any “...” “...” clumps
        results = _profile(
            "after force_split_adjacent_quotes",
            _force_split_adjacent_quotes,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after force_split_adjacent_quotes", results, output_dir, prefix
        )
        if DEBUG_AUDIT:
            _audit_quotes("after _force_split_adjacent_quotes", results)
        results = trace_stage(
            "after force_split_adjacent_quotes", results, output_dir, prefix
        )
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = _profile(
            "after split_midquote_attrib_clauses_early",
            _split_midquote_attrib_clauses_early,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )

        results = _profile(
            "after demote_quoted_attrib_fragments",
            _demote_quoted_attrib_fragments,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _qaudit(
            "after demote_quoted_attrib_fragments", results, output_dir, prefix
        )
        results = trace_stage(
            "after demote_quoted_attrib_fragments", results, output_dir, prefix
        )

        # NEW: heal the '""' → narrator speech pattern
        results = _profile(
            "after repair_empty_quote_followed_by_speech",
            _repair_empty_quote_followed_by_speech,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after repair_empty_quote_followed_by_speech", results, output_dir, prefix
        )
        results = trace_stage(
            "after repair_empty_quote_followed_by_speech", results, output_dir, prefix
        )
        # NEW: split mid-quote attribution tails (”, said Zack.” / ” explained Smith.” / ” queried Smith.”)
        results = _profile(
            "after split_midquote_attrib_clauses_early",
            _split_midquote_attrib_clauses_early,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )
        results = trace_stage(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )
        # results = _peel_outside_text_from_quote(results)
        # results = _recover_balanced_quotes_from_narration(results)
        # results = _qaudit("after early_peel_and_recover", results, output_dir, prefix)

        # 1a) Early guard BEFORE any merging/coalescing
        results = _profile(
            "after final_guard_no_narrator_quotes (early)",
            _final_guard_no_narrator_quotes,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after final_guard_no_narrator_quotes_1a", results, output_dir, prefix
        )
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = trace_stage(
            "after final_guard+reassert (early)", results, output_dir, prefix
        )

        # 1b) Locks & soft-wrap glue
        results = _profile(
            "after lock_when_explicit_agrees",
            _lock_when_explicit_agrees,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after glue_softwrapped_quotes",
            _glue_softwrapped_quotes,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after promote_softwrap_continuations (early)",
            _promote_softwrap_continuations,
            results,
            output_dir,
            prefix,
        )
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = trace_stage(
            "after glue_softwrapped_quotes", results, output_dir, prefix
        )

        # 1c) Context propagation
        results = _profile(
            "after propagate_quote_context",
            _propagate_quote_context,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit("after propagate_quote_context", results, output_dir, prefix)
        results = trace_stage(
            "after propagate_quote_context", results, output_dir, prefix
        )

        # 1d) Narration-only inline attribution/action splitting + multi-quote span split
        results = _profile(
            "after split_narrator_on_inline_attrib_and_actions",
            _split_narrator_on_inline_attrib_and_actions,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _qaudit(
            "after split_narrator_on_inline_attrib_and_actions",
            results,
            output_dir,
            prefix,
        )
        results = trace_stage(
            "after split_narrator_on_inline_attrib_and_actions",
            results,
            output_dir,
            prefix,
        )

        results = _profile(
            "after split_results_on_multiple_quote_spans",
            _split_results_on_multiple_quote_spans,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _qaudit(
            "after split_results_multi_quote", results, output_dir, prefix
        )
        results = trace_stage(
            "after split_results_multi_quote", results, output_dir, prefix
        )

        results = _profile(
            "after rehydrate_quote_rows_without_spans",
            _rehydrate_quote_rows_without_spans,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit("after rehydrate_quote_rows", results, output_dir, prefix)

        results = _profile(
            "after split_midquote_attrib_clauses_early",
            _split_midquote_attrib_clauses_early,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )
        results = trace_stage("after rehydrate_quote_rows", results, output_dir, prefix)

        # 1e) Edge-peel pass (stable indices) and flag reassert
        results = _profile(
            "after edge_peel_pass_inplace",
            _edge_peel_pass_inplace,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _reassert_quote_flags_inplace(results)
        results = trace_stage(
            "after edge_peel_pass_inplace", results, output_dir, prefix
        )

        # 2) Fix explicit 'Name:' heads
        results = _profile(
            "after apply_name_colon_rule",
            _apply_name_colon_rule,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _qaudit("after name_colon_rule", results, output_dir, prefix)
        results = trace_stage("after name_colon_rule", results, output_dir, prefix)

        # 2b) Split tail attribution inside the last quote
        results = _profile(
            "after split_inline_tail_attrib_in_quotes",
            _split_inline_tail_attrib_in_quotes,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _qaudit(
            "after split_tail_attrib_in_quotes", results, output_dir, prefix
        )
        log("[splitter] ran _split_inline_tail_attrib_in_quotes")
        results = trace_stage(
            "after split_tail_attrib_in_quotes", results, output_dir, prefix
        )
        # recovery step (repairs wrongly demoted interior sentences inside long quotes)
        results = _profile(
            "after rehydrate_monologue_gaps",
            _rehydrate_monologue_gaps,
            results,
            output_dir,
            prefix,
        )
        # demote tiny misquoted attrib rows (you already have this)
        results = _demote_misquoted_attrib_rows(results)
        results = _profile(
            "after demote_quoted_action_sentences",
            _demote_quoted_action_sentences,
            results,
            output_dir,
            prefix,
        )

        results = _profile(
            "after demote_quoted_action_sentences",
            _demote_quoted_action_sentences,
            results,
            output_dir,
            prefix,
        )

        # keep flags sane
        results = _reassert_quote_flags_strict(results)

        # NEW: if a tiny quoted attribution slipped through, demote it to narration
        results = _demote_misquoted_attrib_rows(results)
        results = _qaudit(
            "after demote_misquoted_attrib_rows", results, output_dir, prefix
        )

        # keep flags sane before continuing
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)

        # 2c) Heal any single-quote oddities early
        results = _profile(
            "after fix_lonely_quote_rows",
            _fix_lonely_quote_rows,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit("after fix_lonely_quote_rows", results, output_dir, prefix)
        results = _profile(
            "after coalesce_paragraphs (narr-only)",
            _coalesce_paragraphs,
            results,
            output_dir,
            prefix,
        )
        results = trace_stage(
            "after coalesce_paragraphs (narr-only)", results, output_dir, prefix
        )
        _trace_glyph_budget("after coalesce_paragraphs", results)

        # 3) Stitch attribution/action fragments to the right neighbor quote; scoop 'said X'
        results = trace_stage(
            "before attach_action_fragments", results, output_dir, prefix
        )
        results = _profile(
            "after attach_action_fragments",
            attach_action_fragments,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        if DEBUG_AUDIT:
            _audit_quotes("after attach_action_fragments", results)
        _attrib_dbg_reset()
        # ---- instrumentation: snapshot before harvest ----
        _attrib_dbg_reset()
        DBG["unknown_before"] = sum(
            1
            for r in results
            if looks_like_direct_speech(r.get("text") or "")
            and (r.get("speaker") in ("", None, "Unknown"))
        )
        _attrib_eval_snapshot(results, "before_harvest", outdir=DBG.get("OUTDIR"))
        # --------------------------------------------------

        results = [
            _prefer_enlp_when_matching_quote(r) if r.get("is_quote") else r
            for r in results
        ]
        results = _profile(
            "after attach_inline_attrib_to_adjacent_unknown",
            attach_inline_attrib_to_adjacent_unknown,
            results,
            output_dir,
            prefix,
            alias_inv,
            4,
        )
        # ---- instrumentation: snapshot after harvest ----
        DBG["unknown_after"] = sum(
            1
            for r in results
            if looks_like_direct_speech(r.get("text") or "")
            and (r.get("speaker") in ("", None, "Unknown"))
        )
        _attrib_eval_snapshot(results, "after_harvest", outdir=DBG.get("OUTDIR"))
        # -------------------------------------------------
        results = _reassert_quote_flags_strict(results)
        results = _enforce_locked_speakers(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = trace_stage(
            "after attach_inline_attrib_to_adjacent_unknown",
            results,
            output_dir,
            prefix,
        )

        # 3b) If any narrator sentence got glued to a quote, separate it and reassert
        results = _profile(
            "after separate_accidental_quote_narration_merges",
            _separate_accidental_quote_narration_merges,
            results,
            output_dir,
            prefix,
        )
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)
        log(
            f"[strict] reassert_runs={DBG.get('reassert_strict_runs',0)} flag_changes={DBG.get('reassert_flag_changes',0)} lonely_stripped={DBG.get('lonely_quote_stripped',0)} narr_tail_splits={DBG.get('narr_tail_splits',0)}"
        )
        results = trace_stage(
            "after separate_accidental_quote_narration_merges",
            results,
            output_dir,
            prefix,
        )

        # 3c) Continuity & coref fill (lightweight nudges)
        results = _profile(
            "after continuity_fill_quotes",
            continuity_fill_quotes,
            results,
            output_dir,
            prefix,
            4,
            2,
        )
        results = _profile(
            "after coref_pronoun_fill",
            _coref_pronoun_fill,
            results,
            output_dir,
            prefix,
            ENLP_COREF_MAP,
        )
        results = trace_stage("after coref_pronoun_fill", results, output_dir, prefix)

        # 4) Guardrails: quotes cannot be Narrator; narration cannot be quoted
        results = _profile(
            "after force_quotes_not_narrator",
            _force_quotes_not_narrator,
            results,
            output_dir,
            prefix,
        )
        if STRICT_DIALOGUE_RULE:
            results = _profile(
                "after enforce_dialogue_narration_rule",
                enforce_dialogue_narration_rule,
                results,
                output_dir,
                prefix,
                qmap,
                alias_inv,
            )
            results = _qaudit(
                "after enforce_dialogue_narration_rule", results, output_dir, prefix
            )
        if DEBUG_AUDIT:
            _audit_quotes("after guardrails", results)
        results = trace_stage("after guardrails", results, output_dir, prefix)
        _trace_glyph_budget("after enforce_dialogue_narration_rule", results)

        results = _profile(
            "after filter_subject_only_speakers",
            _filter_subject_only_speakers,
            results,
            output_dir,
            prefix,
        )
        results = trace_stage(
            "after filter_subject_only_speakers", results, output_dir, prefix
        )

        # 5) Carry/flow helpers & vocatives
        results = _profile(
            "after carry_monologue_across_punct",
            _carry_monologue_across_punct,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after carry_same_speaker_across_adjacent_quotes",
            _carry_same_speaker_across_adjacent_quotes,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after inherit_microquote_speakers",
            _inherit_microquote_speakers,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _profile(
            "after carry_burst_attribution",
            _carry_burst_attribution,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after demote_vocative_address",
            _demote_vocative_address,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = trace_stage("after carry/demote passes", results, output_dir, prefix)

        # 6) Heuristics & smoothing
        results = _profile(
            "after apply_addressing_echo_rules",
            _apply_addressing_echo_rules,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _profile(
            "after two_party_fill_unknowns",
            _two_party_fill_unknowns,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after rebalance_quote_bursts",
            _rebalance_quote_bursts,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after apply_conversational_reasoning",
            _apply_conversational_reasoning,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after qa_turn_taking", _qa_turn_taking, results, output_dir, prefix
        )
        results = _profile(
            "after apply_dialogue_pair_hints",
            _apply_dialogue_pair_hints,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = trace_stage("after heuristic passes", results, output_dir, prefix)

        # 6b) Prefer a slightly larger context when fixing Unknowns
        results = _profile(
            "after resolve_unknowns",
            _resolve_unknowns,
            results,
            output_dir,
            prefix,
            qmap,
            alias_inv,
            4,
        )
        results = trace_stage("after resolve_unknowns", results, output_dir, prefix)

        # 6c) Smooth ping-pong, enforce locks again, and hard separate kinds
        results = _profile(
            "after smooth_dialogue_turns",
            smooth_dialogue_turns,
            results,
            output_dir,
            prefix,
            6,
        )
        results = _enforce_locked_speakers(results)
        results = _reassert_quote_flags(results)
        results = _profile(
            "after demote_nonquote_character_rows",
            _demote_nonquote_character_rows,
            results,
            output_dir,
            prefix,
        )
        results = trace_stage("after smooth+demote", results, output_dir, prefix)

        # 6d) HARD separate quotes vs narration (belt-and-suspenders)
        results = _profile(
            "after hard_separate_quotes_and_narration",
            _hard_separate_quotes_and_narration,
            results,
            output_dir,
            prefix,
            qmap,
            alias_inv,
        )
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = trace_stage(
            "after hard_separate_quotes_and_narration", results, output_dir, prefix
        )
        results = _peel_outside_text_from_quote(results)
        results = _recover_balanced_quotes_from_narration(results)
        results = _qaudit(
            "after late_peel_and_recover_premerge", results, output_dir, prefix
        )

        results = _profile(
            "after final_resplit_multiquote_rows (pre-merge)",
            _final_resplit_multiquote_rows,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after final_resplit_multiquote_rows", results, output_dir, prefix
        )
        results = trace_stage(
            "after final_resplit_multiquote_rows (pre-merge)",
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after split_midquote_attrib_clauses_early",
            _split_midquote_attrib_clauses_early,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after split_midquote_attrib_clauses_early", results, output_dir, prefix
        )

        # 6e) MERGE PHASE — obey your UX rules
        results = trace_stage("before merges", results, output_dir, prefix)
        
        # DISABLED FOR AUDIOBOOK: Preserve BookNLP's sentence boundaries.
        # Merging quotes causes problems where multiple sentences from different
        # contexts get glued together (e.g., "Why, Zack?...he went on in a monotone.")
        # For audiobook creation, we want each sentence as a separate row.
        # results = _profile(
        #     "after merge_quote_runs_by_speaker",
        #     _merge_quote_runs_by_speaker,
        #     results,
        #     output_dir,
        #     prefix,
        # )
        # log(
        #     f"[merge-runs] merges={DBG.get('merge_quote_runs_merges',0)} calls={DBG.get('merge_quote_runs_calls',0)}"
        # )
        results = trace_stage(
            "after merge_quote_runs_by_speaker [DISABLED]", results, output_dir, prefix
        )

        results = _profile(
            "after coalesce_paragraphs (post-merge narr-only)",
            _coalesce_paragraphs,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit("after coalesce_paragraphs", results, output_dir, prefix)
        log(
            f"[coalesce] merges={DBG.get('coalesce_merges',0)} skipped_kind={DBG.get('coalesce_skipped_kind',0)} skipped_q2q={DBG.get('coalesce_skipped_quote2quote',0)} skipped_attribfrag={DBG.get('coalesce_skipped_attribfrag',0)}"
        )
        results = trace_stage(
            "after coalesce_paragraphs (post-merge narr-only)",
            results,
            output_dir,
            prefix,
        )

        # 6f) If any quote rows still carry head/tail narration, peel them now and reassert
        results = _profile(
            "after final_peel_narration_from_quotes",
            _final_peel_narration_from_quotes,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after final_peel_narration_from_quotes", results, output_dir, prefix
        )

        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = trace_stage(
            "after final_peel_narration_from_quotes", results, output_dir, prefix
        )
        results = _profile(
            "after peel_seam_tails_from_quote_rows",
            _peel_seam_tails_from_quote_rows,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after peel_seam_tails_from_quote_rows", results, output_dir, prefix
        )
        results = _profile(
            "after promote_post_quote_attrib",
            _promote_post_quote_attrib,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after promote_pre_quote_attrib",
            _promote_pre_quote_attrib,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after promote_inbetween_attrib_triplets",
            _promote_inbetween_attrib_triplets,
            results,
            output_dir,
            prefix,
        )
        results = _peel_outside_text_from_quote(results)
        results = _recover_balanced_quotes_from_narration(results)
        results = _qaudit("after final_peel_and_recover", results, output_dir, prefix)
        # after 6f) peel + reassert + debug
        results = _demote_quoted_attrib_fragments(results, alias_inv)  # LATE
        results = _qaudit(
            "after demote_quoted_attrib_fragments[LATE]", results, output_dir, prefix
        )
        results = _profile(
            "after demote_quoted_action_sentences [LATE]",
            _demote_quoted_action_sentences,
            results,
            output_dir,
            prefix,
        )

        results = _profile(
            "after demote_quoted_action_sentences [LATE]",
            _demote_quoted_action_sentences,
            results,
            output_dir,
            prefix,
        )
        # strict hard separate before any final smoothing/merging
        results = _profile(
            "after hard_separate_quotes_and_narration_strict (pre-merge)",
            _hard_separate_quotes_and_narration_strict,
            results,
            output_dir,
            prefix,
        )
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)

        # --- late cleanups to fix quote-flagged beats without glyphs ---
        results = _profile(
            "after demote_quoted_attrib_fragments [LATE2]",
            _demote_quoted_attrib_fragments,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _profile(
            "after split_inline_tail_attrib_in_quotes [LATE]",
            _split_inline_tail_attrib_in_quotes,
            results,
            output_dir,
            prefix,
        )

        results = _profile(
            "after demote_quoted_action_sentences [LATE2]",
            _demote_quoted_action_sentences,
            results,
            output_dir,
            prefix,
        )

        # Safety net: any is_quote row with NO quote glyphs becomes narration
        results = _profile(
            "after force_nonquote_when_no_glyphs",
            _force_nonquote_when_no_glyphs,
            results,
            output_dir,
            prefix,
        )

        # Reassert, then (optionally) re-harvest attrib fragments so nearby Unknown quotes get locked
        results = _reassert_quote_flags_strict(results)
        results = _profile(
            "after attach_action_fragments [post-flip]",
            attach_action_fragments,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = _reassert_quote_flags_strict(results)

        # 6g) Post-merge sanity
        results = _profile(
            "after post_speaker_sanity",
            _post_speaker_sanity,
            results,
            output_dir,
            prefix,
        )
        results = trace_stage("after post_speaker_sanity", results, output_dir, prefix)
        # collapse junky multi-token speakers
        results = _profile(
            "after speaker_name_sanity",
            _speaker_name_sanity,
            results,
            output_dir,
            prefix,
            alias_inv,
        )
        results = trace_stage("after speaker_name_sanity", results, output_dir, prefix)

        # Inherit speakers for Unknown quotes sandwiched between same speaker
        results = _profile(
            "after inherit_sandwiched_unknowns [FINAL]",
            _inherit_speaker_for_sandwiched_unknowns,
            results,
            output_dir,
            prefix,
        )
        results = trace_stage(
            "after inherit_sandwiched_unknowns", results, output_dir, prefix
        )

        # FINAL split pass: catch any attribution that got re-glued by earlier stages
        results = _profile(
            "after split_midquote_attrib_clauses [FINAL]",
            _split_midquote_attrib_clauses_early,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after split_midquote_attrib_clauses [FINAL]", results, output_dir, prefix
        )

        # NOW merge short attribution tails AFTER all demote/split stages
        results = _profile(
            "after merge_short_narration_tails [FINAL]",
            _merge_short_narration_tails_into_prev_quote,
            results,
            output_dir,
            prefix,
        )
        results = _qaudit(
            "after merge_short_narration_tails [FINAL]", results, output_dir, prefix
        )

        # 7) Kill adjacent duplicate quotes, keep locks
        results = trace_stage(
            "before dedupe_adjacent_quotes", results, output_dir, prefix
        )
        results = _profile(
            "after dedupe_adjacent_quotes",
            _dedupe_adjacent_quotes,
            results,
            output_dir,
            prefix,
        )
        log(
            f"[dedupe] pairs_eval={DBG.get('dedupe_pairs_evaluated',0)} merged={DBG.get('dedupe_pairs_merged',0)} conf_wins={DBG.get('dedupe_length_wins',0)}"
        )
        results = _enforce_locked_speakers(results)
        results = trace_stage(
            "after dedupe_adjacent_quotes", results, output_dir, prefix
        )
        results = _profile(
            "after dedupe_narrator_quote_duplicates",
            _dedupe_narrator_quote_duplicates,
            results,
            output_dir,
            prefix,
        )
        results = trace_stage(
            "after dedupe_narrator_quote_duplicates", results, output_dir, prefix
        )

        # 8) Precision-gate speakers on the final set
        try:
            wl = CANON_WHITELIST
        except NameError:
            wl = set()
        try:
            results = _profile(
                "after final_precision_gate (cache)",
                _final_precision_gate,
                results,
                output_dir,
                prefix,
                wl,
                ALIAS_INV_CACHE,
            )
        except NameError:
            results = _profile(
                "after final_precision_gate",
                _final_precision_gate,
                results,
                output_dir,
                prefix,
                wl,
                alias_inv,
            )
        results = trace_stage("after final_precision_gate", results, output_dir, prefix)

        # 8b) Guarantee narration is Narrator after any late changes
        results = _profile(
            "after strip_character_speaker_from_narration",
            _strip_character_speaker_from_narration,
            results,
            output_dir,
            prefix,
        )
        results = trace_stage(
            "after strip_character_speaker_from_narration", results, output_dir, prefix
        )

        # 9) Late cleanup + finalization
        results = _profile(
            "after strip_internal_tags",
            _strip_internal_tags,
            results,
            output_dir,
            prefix,
        )
        results = _profile(
            "after drop_empty_quote_rows",
            _drop_empty_quote_rows,
            results,
            output_dir,
            prefix,
        )
        results = _reassert_quote_flags(results)
        results = _debug_assert_quote_flag_consistency(results)
        results = trace_stage(
            "after drop_empty_quote_rows", results, output_dir, prefix
        )

        results = _profile(
            "after finalize_speakers", _finalize_speakers, results, output_dir, prefix
        )
        results = _reassert_quote_flags(results)
        results = trace_stage("after finalize_speakers", results, output_dir, prefix)

        # Final guard again (safety net)
        results = _profile(
            "after final_guard_no_narrator_quotes (final)",
            _final_guard_no_narrator_quotes,
            results,
            output_dir,
            prefix,
        )
        if DEBUG_AUDIT:
            results = _assert_invariants(results)
        # last strict guard to kill any residual narrator=quote glitches
        results = _profile(
            "after hard_separate_quotes_and_narration_strict (final-guard)",
            _hard_separate_quotes_and_narration_strict,
            results,
            output_dir,
            prefix,
        )
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)

        # last-chance cleanup before writing anything to disk ---
        results = _profile(
            "after final_quote_sanity_pass",
            _final_quote_sanity_pass,
            results,
            output_dir,
            prefix,
        )
        results = _dedupe_narrator_quote_duplicates(
            results
        )  # pick the quoted row over the narr twin
        results = _dedupe_adjacent_quotes(
            results
        )  # then do same-kind near-dup compaction

        # Reassert once more so flags are perfectly consistent for the UI/auditor
        results = _reassert_quote_flags_strict(results)
        results = _debug_assert_quote_flag_consistency(results)

        # DISABLED FOR AUDIOBOOK: _final_never_break_quotes was merging 274 → 198 rows (28% reduction!).
        # For audiobook TTS, we need sentence-level granularity, not merged quote blocks.
        # results = _profile(
        #     "after final_never_break_quotes",
        #     _final_never_break_quotes,
        #     results,
        #     output_dir,
        #     prefix,
        # )
        results = _reassert_quote_flags_strict(results)
        # remove stray edge quotes on narration (optional)
        results = _profile(
            "after strip_stray_edge_quotes",
            _strip_stray_edge_quotes,
            results,
            output_dir,
            prefix,
        )
        # diagnostics: assert we didn't leave a Narrator inside an open quote run
        if DEBUG_AUDIT:
            results = _profile(
                "after assert_no_broken_quotes",
                _assert_no_broken_quotes,
                results,
                output_dir,
                prefix,
            )

        # Take the real final snapshot *after* cleanup
        results = trace_stage("final", results, output_dir, prefix)
        _trace_glyph_budget("final", results)

        # (Optional) snapshot if you want to see it in trace
        results = trace_stage(
            "after final_quote_sanity_pass", results, output_dir, prefix
        )

        # NEW: Global dedupe to catch non-adjacent duplicates that slipped through
        before_global_dedupe = len(results)
        results = _global_dedupe_by_text_and_speaker(results)
        after_global_dedupe = len(results)
        if after_global_dedupe < before_global_dedupe:
            log(f"[global_dedupe] {before_global_dedupe} -> {after_global_dedupe} rows (removed {before_global_dedupe - after_global_dedupe} duplicates)")

        # Log Cleaned Results
        log(f"Cleaned results: {len(results)} lines")
        for seg in results[:200]:
            log(f"SEGMENT: {seg['speaker']} | {seg['text'][:60]}...")

        # ---- Final character histogram (for the Characters tab / sanity checks)
        from collections import Counter

        counts = Counter(r["speaker"] for r in results)
        hist = ", ".join(
            f"{name}:{counts[name]}"
            for name in sorted(counts, key=lambda k: (-counts[k], k))[:100]
        )
        log(f"[final-characters] {hist}")

        # Also write to disk, next to other BookNLP outputs
        fc_path = os.path.join(output_dir, f"{prefix}.final_characters.txt")
        try:
            with open(fc_path, "w", encoding="utf-8") as f:
                for name, cnt in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
                    f.write(f"{name}\t{cnt}\n")
            log(f"[final-characters] wrote {fc_path}")
        except Exception as e:
            log(f"[final-characters] write failed: {e}")

        # Unknown count for quoted lines
        unk = sum(
            1
            for r in results
            if looks_like_direct_speech(r["text"]) and r["speaker"] == "Unknown"
        )
        log(f"[unknown] quoted_unknown={unk}")

        # UI-only de-tokenization (fix "are n’t" / "are n't" -> "aren't", etc.)
        for _i in range(len(results)):
            results[_i]["text"] = _fix_tokenization_artifacts(
                results[_i].get("text") or ""
            )

        try:
            _qa_emit_quote_report(output_dir, prefix)
        except Exception as e:
            log(f"[qa] emit report failed: {e}")

        try:
            _emit_attrib_ops(output_dir, prefix)
        except Exception as e:
            log(f"[attrib-ops] emit failed: {e}")

        try:
            emit_stage_stats(output_dir, prefix)
        except Exception as e:
            log(f"[stage_stats] emit failed: {e}")


        # FINALIZE: fix misclassified attribution, then merge same-speaker quotes + narration
        # Character lines = is_quote=True (dialogue only, gets character voice)
        # Narrator lines = is_quote=False (narration + attribution, gets narrator voice)
        # Note: BookNLP sometimes has speaker attribution errors - users can correct in GUI
        try:
            log(f"[finalize] Starting finalization pipeline with {len(results)} rows...")
            
            # DEBUG: Check for "said Smith" before finalization
            said_hatfield_count = 0
            for i, row in enumerate(results):
                if "said Smith" in row.get("text", ""):
                    said_hatfield_count += 1
                    log(f"[finalize-pre] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} text={row.get('text')[:80]}")
            log(f"[finalize-pre] Found {said_hatfield_count} rows with 'said Smith'")
            
            # DEBUG: Check for rows containing "Because it's expected"
            for i, row in enumerate(results):
                if "Because it" in row.get("text", ""):
                    log(f"[finalize-debug] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} text={row.get('text')[:100]}")
            
            final_rows = fix_misclassified_attribution_fragments(results)
            log(f"[finalize] After fix_misclassified: {len(final_rows)} rows")
            
            final_rows = split_multi_quote_rows(final_rows)  # Split multi-speaker rows (turn-taking)
            log(f"[finalize] After split_multi_quote_rows: {len(final_rows)} rows")
            
            # DEBUG: Check for rows containing "Because it's expected" after split_multi_quote
            for i, row in enumerate(final_rows):
                if "Because it" in row.get("text", ""):
                    log(f"[finalize-debug-multi] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} _was_multi_span={row.get('_was_multi_span')} text={row.get('text')[:100]}")
            
            final_rows = split_attribution_from_quotes(final_rows)  # Split "said X."quote" patterns
            log(f"[finalize] After split_attribution_from_quotes: {len(final_rows)} rows")
            
            # DEBUG: Check for rows containing "Because it's expected" after split_attribution
            for i, row in enumerate(final_rows):
                if "Because it" in row.get("text", ""):
                    log(f"[finalize-debug-attrib] ROW {i}: speaker={row.get('speaker')} is_quote={row.get('is_quote')} text={row.get('text')[:100]}")
            
            final_rows = finalize_quote_narration_blocks(final_rows)
            log(f"[finalize] After finalize_quote_narration_blocks: {len(final_rows)} rows")
            
            dump_gui_rows_txt(
                final_rows,
                os.path.join(output_dir, f"{prefix}.gui_rows.txt")
            )
            log(f"[finalize] Successfully wrote gui_rows.txt with {len(final_rows)} rows")
            
            # Return finalized rows to GUI (consolidated character lines + narration)
            results = final_rows
        except Exception as e:
            log(f"[finalize] ERROR in finalization pipeline: {e}")
            import traceback
            log(f"[finalize] Traceback: {traceback.format_exc()}")
            log(f"[finalize] Returning UNFINALIZED results ({len(results)} rows)")
            # Still try to dump what we have
            try:
                dump_gui_rows_txt(results, os.path.join(output_dir, f"{prefix}.gui_rows.txt"))
            except:
                pass

        return results

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
