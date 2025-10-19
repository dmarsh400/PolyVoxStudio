import sys
import spacy
import copy

# ? Updated imports to point into /app/core
from app.core.pipelines import SpacyPipeline
from app.core.entity_tagger import LitBankEntityTagger
from app.core.gender_inference_model_1 import GenderEM
from app.core.name_coref import NameCoref
from app.core.litbank_coref import LitBankCoref
from app.core.litbank_quote import QuoteTagger
from app.core.bert_qa import QuotationAttribution

from os.path import join
import os
import json
import re
from collections import Counter
from html import escape
import time
from pathlib import Path
import urllib.request 
import pkg_resources
import torch
import datetime


# ---- Stats export for other modules ----
ENLP_CLUSTER_STATS = {"narr": {}, "quote": {}}

# ---- ENLP caches (safe defaults; will be overwritten by init_enlp_caches) ----
ENLP_QUOTE_INDEX: dict[str, list] = {}
ENLP_CID2CANON: dict[int, str] = {}
ENLP_COREF_MAP: dict[str, int] = {}

# --- ENLP run context (set by init_enlp_caches) ---
ENLP_LAST_DIR = None
ENLP_LAST_PREFIX = None
ENLP_CLUSTER_STATS = {"narr": {}, "quote": {}}

# Ensure these exist at module import time
try:
    ENLP_CLUSTER_STATS
except NameError:
    ENLP_CLUSTER_STATS = {"narr": {}, "quote": {}}

def _set_enlp_zone_counts(narr_counts: dict | None, quote_counts: dict | None) -> None:
    """
    Update ENLP_CLUSTER_STATS without rebinding the name (no 'global' needed).
    Safe to call multiple times.
    """
    d = globals().get("ENLP_CLUSTER_STATS")
    if not isinstance(d, dict):
        d = {"narr": {}, "quote": {}}
        globals()["ENLP_CLUSTER_STATS"] = d

    # normalize to ints and replace the two sub-maps
    narr = {int(k): int(v) for k, v in (narr_counts or {}).items()}
    quote = {int(k): int(v) for k, v in (quote_counts or {}).items()}
    d["narr"] = narr
    d["quote"] = quote

# --- lightweight logger (falls back to print if 'log' isn't available here) ---
def _elog(msg: str) -> None:
    try:
        log(msg)  # if caller injected a 'log'
    except Exception:
        try:
            print(msg)
        except Exception:
            pass

# --- resolve ENLP file paths from the last init (handles (edit).txt variants) ---
def _resolve_enlp_paths():
    outdir = globals().get("ENLP_LAST_DIR")
    pref   = globals().get("ENLP_LAST_PREFIX")
    if not outdir or not pref:
        return None, None, None

    def _pick_existing(*cands):
        import os
        for p in cands:
            if p and os.path.exists(p):
                return p
        return None

    import os
    tokens_path = _pick_existing(
        os.path.join(outdir, f"{pref}.tokens(edit).txt"),
        os.path.join(outdir, f"{pref}.tokens.txt"),
        os.path.join(outdir, f"{pref}.tokens"),
    )
    quotes_path = _pick_existing(
        os.path.join(outdir, f"{pref}.quotes(edit).txt"),
        os.path.join(outdir, f"{pref}.quotes.txt"),
        os.path.join(outdir, f"{pref}.quotes"),
    )
    entities_path = _pick_existing(
        os.path.join(outdir, f"{pref}.entities(edit).txt"),
        os.path.join(outdir, f"{pref}.entities.txt"),
        os.path.join(outdir, f"{pref}.entities"),
    )
    return tokens_path, quotes_path, entities_path

# -------- zone helpers (used by golden block fallback) --------

def _build_quote_token_ranges(quotes):
    """
    Build [(start_token, end_token), ...] for fast zone tests.
    Supports:
      - tuples/lists: (start, end)
      - dicts: {"start_token": s, "end_token": e}
      - objects with .start_token/.end_token
    """
    ranges = []
    for q in quotes or []:
        st = en = None

        # object attributes
        if hasattr(q, "start_token") and hasattr(q, "end_token"):
            st = getattr(q, "start_token")
            en = getattr(q, "end_token")

        # dict
        elif isinstance(q, dict):
            st = q.get("start_token")
            en = q.get("end_token")

        # tuple/list
        elif isinstance(q, (tuple, list)) and len(q) >= 2:
            st, en = q[0], q[1]

        if st is None or en is None:
            continue
        try:
            st = int(st); en = int(en)
        except Exception:
            continue
        ranges.append((st, en))
    return ranges


def _span_overlaps_any(ranges, s, e):
    """True iff [s,e] intersects any (qs,qe) in ranges."""
    for (qs, qe) in ranges or []:
        if not (e < qs or s > qe):
            return True
    return False


def _count_mentions_by_zone(entities, assignments, quote_ranges):
    """
    Count mentions by zone for each cluster_id:
      - entities: tuples (start,end,cat,text), dicts, or objects with .start/.end
      - assignments: list mapping mention index -> cluster_id (int/str)
      - quote_ranges: list[(start_token, end_token)]
    Returns (narr_mentions: dict[cid]->int, quote_mentions: dict[cid]->int)
    """
    narr_mentions = {}
    quote_mentions = {}

    for idx, ent in enumerate(entities or []):
        # token span (start, end)
        ms = me = None
        if isinstance(ent, (tuple, list)):
            if len(ent) >= 2:
                ms, me = ent[0], ent[1]
        elif isinstance(ent, dict):
            ms = ent.get("start") or ent.get("begin")
            me = ent.get("end") or ent.get("finish")
        else:
            ms = getattr(ent, "start", None)
            me = getattr(ent, "end", None)

        if ms is None or me is None:
            continue
        try:
            ms = int(ms); me = int(me)
        except Exception:
            continue

        # cluster id from assignments
        try:
            cid = assignments[idx]
        except Exception:
            continue
        try:
            cid = int(cid)
        except Exception:
            continue
        if cid < 0:
            continue

        if _span_overlaps_any(quote_ranges, ms, me):
            quote_mentions[cid] = quote_mentions.get(cid, 0) + 1
        else:
            narr_mentions[cid] = narr_mentions.get(cid, 0) + 1

    return narr_mentions, quote_mentions

def _quote_counts_from_quotes_file(path_quotes: str) -> dict[int, int]:
    """
    Fallback: count how many quotes are attributed to each char_id from the quotes file.
    Works even if entities/tokens lack usable spans.
    """
    import os
    counts: dict[int, int] = {}
    if not (path_quotes and os.path.exists(path_quotes)):
        return counts

    with open(path_quotes, "r", encoding="utf-8", errors="replace") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            # split on tab first; fallback to any whitespace
            parts = line.split("\t")
            if len(parts) == 1:
                parts = line.split()

            if header is None:
                header = [c.strip().lower() for c in parts]
                # find char_id column name or position
                if "char_id" in header:
                    char_idx = header.index("char_id")
                elif "character_id" in header:
                    char_idx = header.index("character_id")
                elif "charid" in header:
                    char_idx = header.index("charid")
                else:
                    # unknown header; treat as no header row
                    header = None
                    # Let the next iteration parse this line as data again
                    # by continuing without consuming it as header
                    continue
                continue

            # if we have no header, try to parse with some heuristics:
            if header is None:
                # Heuristic: try last column as char_id; else skip
                try:
                    cid = int(parts[-1])
                    counts[cid] = counts.get(cid, 0) + 1
                except Exception:
                    pass
                continue

            # Header-based parse:
            try:
                cid = int(parts[char_idx])
                counts[cid] = counts.get(cid, 0) + 1
            except Exception:
                # ignore malformed rows
                pass

    return counts

def _pick_existing(*cands):
    for p in cands:
        if os.path.exists(p):
            return p
    return cands[0]

# --- logging shim (english_booknlp.py) ---
def log(msg: str):
    try:
        print(msg)
    except Exception:
        pass

# (class EnglishBookNLP, all methods, logic, JSON writers, etc.)

def _gap_is_punct_only(tokens, a_token_id, b_token_id):
    """True if all tokens strictly between a and b are punctuation-like (no letters/digits)."""
    for t in tokens:
        if a_token_id < t.token_id < b_token_id:
            # if any alphanumeric char appears, it's not a pure punct gap
            if any(ch.isalnum() for ch in t.text):
                return False
    return True

def _merge_quote_spans(quotes, attributed_quotations, tokens, max_token_gap=3):
    """
    Merge adjacent quote spans into longer monologues when:
      - same attributed speaker_id (or one side is None), and
      - the token gap between them is small and punctuation-only.
    Returns (merged_quotes, merged_attribs).
    """
    if not quotes:
        return quotes, attributed_quotations

    pairs = sorted(zip(quotes, attributed_quotations), key=lambda x: x[0][0])
    merged = []

    (cur_s, cur_e), cur_sid = pairs[0]
    for (s, e), sid in pairs[1:]:
        gap = s - cur_e - 1
        same_or_unknown = (sid == cur_sid) or (sid is None) or (cur_sid is None)
        if gap >= 0 and gap <= max_token_gap and same_or_unknown and _gap_is_punct_only(tokens, cur_e, s):
            # extend current span; prefer concrete speaker if one side is None
            cur_e = e
            if cur_sid is None and sid is not None:
                cur_sid = sid
        else:
            merged.append(((cur_s, cur_e), cur_sid))
            cur_s, cur_e, cur_sid = s, e, sid

    merged.append(((cur_s, cur_e), cur_sid))
    new_quotes = [span for span, _sid in merged]
    new_attribs = [_sid for _span, _sid in merged]
    return new_quotes, new_attribs

# --- Subject-only suppression (mentioned but never speaking) ------------------
SUBJECT_ONLY_SUPPRESS = True
SUBJECT_ONLY_MIN_QUOTE_MENTIONS = 2     # require at least 2 in-quote mentions
SUBJECT_ONLY_MAX_NARR_MENTIONS = 0      # allow 0 (or 1 if you want to be looser)

# --- robust zone counting (english_booknlp.py) ---
def _load_mentions_from_entities(path_entities: str, path_tokens: str | None = None):
    """
    Return list of (cid, t_lo, t_hi) *token* spans (inclusive) for person/coref mentions.
    Accepts {char_id|cluster_id|id|coref} for the cluster id and
    {token_begin|token_start|token_id_begin|begin_token|begin} for token starts.
    If only char offsets exist, we map to tokens using `path_tokens`.
    """
    import os, re

    def _build_char2tok(tokens_path: str | None):
        if not tokens_path or not os.path.exists(tokens_path):
            return None
        idx = []
        with open(tokens_path, "r", encoding="utf-8", errors="replace") as tf:
            h = None
            for line in tf:
                line = line.rstrip("\n")
                if not line: 
                    continue
                cols = line.split("\t")
                if h is None:
                    h = [c.strip().lower() for c in cols]
                    continue
                row = {h[i]: cols[i] for i in range(min(len(h), len(cols)))}
                try:
                    ti = int(row.get("token_id", row.get("id", len(idx))))
                    cb = int(row.get("char_begin", row.get("char_start", row.get("begin", "-1"))))
                    ce = int(row.get("char_end",   row.get("char_stop",  row.get("end",   "-1"))))
                except Exception:
                    continue
                idx.append((ti, cb, ce))
        idx.sort(key=lambda x: x[1])
        return idx

    def _char_to_token(cpos: int, char2tok):
        if not char2tok:
            return None
        # linear is fine for chapters; you can swap in bisect if needed
        for ti, cb, ce in char2tok:
            if cb <= cpos < ce:
                return ti
        return None

    mentions = []
    if not os.path.exists(path_entities):
        return mentions

    char2tok = _build_char2tok(path_tokens)

    with open(path_entities, "r", encoding="utf-8", errors="replace") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            cols = line.split("\t")
            if header is None:
                header = [c.strip().lower() for c in cols]
                continue
            row = {header[i]: cols[i] for i in range(min(len(header), len(cols)))}

            # ---- cluster/character id ----
            cid = (
                row.get("char_id") or
                row.get("cluster_id") or
                row.get("id") or
                row.get("coref")        # <-- IMPORTANT for your files
            )
            try:
                cid = int(cid)
            except Exception:
                continue

            # ---- token spans, if present ----
            t_lo = (
                row.get("token_begin") or row.get("token_start") or
                row.get("token_id_begin") or row.get("begin_token") or
                row.get("begin")
            )
            t_hi = (
                row.get("token_end")   or row.get("token_stop")  or
                row.get("token_id_end")   or row.get("end_token")   or
                row.get("end")
            )
            try:
                t_lo_i = int(t_lo)
                t_hi_i = int(t_hi)
                if t_hi_i < t_lo_i:
                    t_lo_i, t_hi_i = t_hi_i, t_lo_i
                mentions.append((cid, t_lo_i, t_hi_i))
                continue
            except Exception:
                pass  # fall through to char-offset mapping

            # ---- map char offsets to tokens ----
            c_lo = row.get("char_begin", row.get("char_start"))
            c_hi = row.get("char_end",   row.get("char_stop"))
            try:
                c_lo_i = int(c_lo); c_hi_i = int(c_hi)
            except Exception:
                continue

            if not char2tok:
                # no mapping available; skip
                continue

            t_lo_i = _char_to_token(c_lo_i, char2tok)
            # use inclusive end, so map c_hi-1
            t_hi_i = _char_to_token(max(c_lo_i, c_hi_i - 1), char2tok)

            if t_lo_i is None or t_hi_i is None:
                continue
            if t_hi_i < t_lo_i:
                t_lo_i, t_hi_i = t_hi_i, t_lo_i
            mentions.append((cid, t_lo_i, t_hi_i))

    return mentions


def _load_quote_token_ranges(path_quotes: str, path_tokens: str | None = None):
    """
    Return list of (q_lo, q_hi) token ranges inclusive. 
    Tries token fields first; if only char offsets exist, map via tokens.
    """
    import os
    ranges = []
    if not os.path.exists(path_quotes):
        return ranges

    # optional char->token index
    char2tok = None
    if path_tokens and os.path.exists(path_tokens):
        try:
            with open(path_tokens, "r", encoding="utf-8", errors="replace") as tf:
                h = None; offsets = []
                for line in tf:
                    line = line.rstrip("\n")
                    if not line: continue
                    cols = line.split("\t")
                    if h is None:
                        h = [c.strip().lower() for c in cols]
                        continue
                    row = {h[i]: cols[i] for i in range(min(len(h), len(cols)))}
                    ti = int(row.get("token_id", row.get("id", len(offsets))))
                    cb = int(row.get("char_begin", row.get("char_start", row.get("begin", "-1"))))
                    ce = int(row.get("char_end",   row.get("char_stop",  row.get("end",   "-1"))))
                    offsets.append((ti, cb, ce))
            offsets.sort(key=lambda x: x[1])
            char2tok = offsets
        except Exception:
            char2tok = None

    def _char_to_token(cpos: int):
        if char2tok is None:
            return None
        for ti, cb, ce in char2tok:
            if cb <= cpos < ce:
                return ti
        return None

    with open(path_quotes, "r", encoding="utf-8", errors="replace") as f:
        h = None
        for line in f:
            line = line.rstrip("\n")
            if not line: continue
            cols = line.split("\t")
            if h is None:
                h = [c.strip().lower() for c in cols]
                continue
            row = {h[i]: cols[i] for i in range(min(len(h), len(cols)))}

            qlo = row.get("token_begin") or row.get("token_start") or row.get("token_id_begin") or row.get("begin_token") or row.get("begin")
            qhi = row.get("token_end")   or row.get("token_stop")  or row.get("token_id_end")   or row.get("end_token")   or row.get("end")

            try:
                qlo = int(qlo); qhi = int(qhi)
                if qhi < qlo: qlo, qhi = qhi, qlo
                ranges.append((qlo, qhi))
                continue
            except Exception:
                pass  # fallback to char mapping

            c_lo = row.get("char_begin", row.get("char_start"))
            c_hi = row.get("char_end",   row.get("char_stop"))
            try:
                c_lo = int(c_lo); c_hi = int(c_hi)
            except Exception:
                continue
            t_lo = _char_to_token(c_lo)
            t_hi = _char_to_token(max(c_lo, c_hi - 1))
            if t_lo is not None and t_hi is not None:
                if t_hi < t_lo: t_lo, t_hi = t_hi, t_lo
                ranges.append((t_lo, t_hi))

    return ranges


def count_mentions_by_zone_strong(path_entities: str, path_quotes: str, path_tokens: str | None = None):
    """
    Intersect mention token spans with quote token ranges.
    Returns (narr_counts, quote_counts) by cluster id.
    """
    mentions = _load_mentions_from_entities(path_entities, path_tokens)
    qranges  = _load_quote_token_ranges(path_quotes, path_tokens)
    if not mentions or not qranges:
        return {}, {}

    def _overlaps(a_lo, a_hi, b_lo, b_hi):
        return not (a_hi < b_lo or b_hi < a_lo)

    narr, quote = {}, {}
    for cid, m_lo, m_hi in mentions:
        in_quote = any(_overlaps(m_lo, m_hi, q_lo, q_hi) for (q_lo, q_hi) in qranges)
        if in_quote:
            quote[cid] = quote.get(cid, 0) + 1
        else:
            narr[cid]  = narr.get(cid, 0) + 1
    return narr, quote


def compute_zone_counts(outdir: str | None = None, prefix: str | None = None):
    """
    Compute mention counts in narration vs inside quotes.
    Primary: intersect entity mention token spans with quote token ranges.
    Fallback: if that yields empty, count quotes per char_id directly from the quotes file.
    """
    global ENLP_CLUSTER_STATS
    try:
        # Use the remembered last-run dir/prefix if not provided
        if outdir is None:
            outdir = globals().get("ENLP_LAST_DIR")
        if prefix is None:
            prefix = globals().get("ENLP_LAST_PREFIX")
        if not outdir or not prefix:
            log("[mentions] zone counter skipped: ENLP_LAST_DIR/PREFIX not set")
            ENLP_CLUSTER_STATS = {}
            return {}, {}

        # Resolve the three paths (tolerate .txt / (edit).txt variants)
        def _pick_existing(*cands):
            import os
            for p in cands:
                if p and os.path.exists(p):
                    return p
            return None

        import os
        quotes_path  = _pick_existing(os.path.join(outdir, f"{prefix}.quotes(edit).txt"),
                                      os.path.join(outdir, f"{prefix}.quotes.txt"),
                                      os.path.join(outdir, f"{prefix}.quotes"))
        entities_path= _pick_existing(os.path.join(outdir, f"{prefix}.entities(edit).txt"),
                                      os.path.join(outdir, f"{prefix}.entities.txt"),
                                      os.path.join(outdir, f"{prefix}.entities"))
        tokens_path  = _pick_existing(os.path.join(outdir, f"{prefix}.tokens(edit).txt"),
                                      os.path.join(outdir, f"{prefix}.tokens.txt"),
                                      os.path.join(outdir, f"{prefix}.tokens"))

        log(f"[mentions] strong counter using: tokens={tokens_path} quotes={quotes_path} entities={entities_path}")

        narr, quote, used_fallback = {}, {}, False

        # Primary strong counter
        try:
            if quotes_path and entities_path:
                narr, quote = count_mentions_by_zone_strong(entities_path, quotes_path, tokens_path)
        except Exception as e:
            log(f"[mentions] strong counter primary failed: {e}")
            narr, quote = {}, {}

        # Fallback: if the strong counter produced no quote counts, recover quotes
        # from the quotes file *and* still try to compute narration via mentions.
        if not quote and quotes_path:
            qc = _quote_counts_from_quotes_file(quotes_path)
            if qc:
                quote = qc
                used_fallback = True

                # Try to compute narration counts using entities/tokens vs the quote ranges.
                # This gives us narr>0 instead of a quotes-only view.
                try:
                    if entities_path and os.path.exists(entities_path):
                        # Use the same strong routine to get narr/quote splits.
                        n2, q2 = count_mentions_by_zone_strong(entities_path, quotes_path, tokens_path)
                        # Only adopt narration from n2; keep our fallback quotes 'quote'
                        if n2:
                            narr = n2
                except Exception as _e:
                    # Keep narr as-is (possibly empty) if this secondary attempt fails.
                    pass

        # Publish/merge
        cs: dict[int, dict[str, int]] = {}
        for cid, cnt in (narr or {}).items():
            cs.setdefault(cid, {}).update({"narr": int(cnt)})
        for cid, cnt in (quote or {}).items():
            cs.setdefault(cid, {}).update({"quote": int(cnt)})
        ENLP_CLUSTER_STATS = cs

        src = "fallback(quotes+entities)" if used_fallback else "strong"
        log(f"[mentions] zone counts ({src}): quote={sum((quote or {}).values())} narr={sum((narr or {}).values())}")

        return narr, quote

    except Exception as e:
        log(f"[mentions] zone counter failed: {e}")
        ENLP_CLUSTER_STATS = {}
        return {}, {}

# ===== EnglishBookNLP loaders & indices =====

def _norm_for_match(s: str) -> str:
    import re
    if not s:
        return ""
    s = (s.replace("\u201c", '"').replace("\u201d", '"')
           .replace("\u2018", "'").replace("\u2019", "'"))
    return re.sub(r"\s+", " ", s).strip()

def load_enlp_quotes(quotes_tsv_path):
    """
    Read book_input.quotes (TSV) -> list of {"text","char_id","start","end"}.
    Columns vary across versions: we handle both
      quote/text, quote_start/start, quote_end/end, char_id
    """
    import csv
    rows = []
    with open(quotes_tsv_path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            qt = _norm_for_match(r.get("quote") or r.get("text") or "")
            cid = r.get("char_id")
            try:
                cid = int(cid) if cid not in (None, "", "-1") else None
            except Exception:
                cid = None
            try:
                qstart = int(r.get("quote_start") or r.get("start") or -1)
                qend   = int(r.get("quote_end")   or r.get("end")   or -1)
            except Exception:
                qstart, qend = -1, -1
            rows.append({"text": qt, "char_id": cid, "start": qstart, "end": qend})
    return rows

def _build_quote_index(enlp_quotes):
    from collections import defaultdict
    idx = defaultdict(list)
    for q in enlp_quotes:
        idx[_norm_for_match(q["text"])].append(q)
    return dict(idx)

def load_enlp_canonical_map_from_entities(entities_tsv_path):
    """
    Build {char_id -> canonical_name} from book_input.entities,
    preferring PROP/PER names and longer 2-token tails.
    """
    import csv, re
    def tail_name(s):
        caps = re.findall(r"[A-Z][A-Za-z'-]+", s or "")
        if not caps:
            return None
        return (f"{caps[-2]} {caps[-1]}" if len(caps) >= 2 else caps[-1])

    best = {}  # id -> (score, name)
    with open(entities_tsv_path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            try:
                cid = int(r.get("COREF"))
            except Exception:
                continue
            prop = (r.get("prop") or "").upper()
            cat  = (r.get("cat") or "").upper()
            text = r.get("text") or ""
            score = 0
            if prop == "PROP" and cat == "PER":
                score = 3
            elif prop == "NOM" and cat == "PER":
                score = 2
            elif cat == "PER":
                score = 1
            name_tail = tail_name(text) or text.strip()
            if not name_tail:
                continue
            if " " in name_tail:
                score += 1
            prev = best.get(cid)
            if (prev is None) or (score > prev[0]) or (score == prev[0] and len(name_tail) > len(prev[1])):
                best[cid] = (score, name_tail)
    return {cid: name for cid, (_sc, name) in best.items()}

def load_enlp_named_characters_html(html_path):
    """
    Optional: parse book_input.book.html 'Named characters' lines to reinforce canonical choice.
    Returns {alias -> canonical} using the longest multi-token candidate per line.
    """
    import re
    text = open(html_path, "r", encoding="utf-8", errors="ignore").read()
    alias2canon = {}
    for line in text.splitlines():
        if re.search(r"\(\d+\)/", line) and "/" in line:
            parts = [p.strip() for p in line.split("/") if "(" in p]
            tokens = []
            for p in parts:
                m = re.match(r"(.+?)\s*\(\d+\)", p)
                if m:
                    tokens.append(m.group(1).strip())
            if tokens:
                canonical = max(tokens, key=lambda s: (len(s.split())>=2, len(s)))
                for a in tokens:
                    alias2canon[a] = canonical
    return alias2canon

def load_enlp_coref_surface_map(entities_tsv_path, cid2canon):
    """
    Return {surface_string -> cid} using PROP/PER surfaces (<=4 tokens) and canonical forms.
    Used later to resolve Unknown quotes by substring hits.
    """
    import csv
    surface2cid = {}

    # Canonicals + last names
    for cid, name in (cid2canon or {}).items():
        surface2cid[name] = cid
        parts = name.split()
        if len(parts) >= 2:
            surface2cid[parts[-1]] = cid

    # Proper person surfaces from entities
    try:
        with open(entities_tsv_path, newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for r in reader:
                try:
                    cid = int(r.get("COREF"))
                except Exception:
                    continue
                text = (r.get("text") or "").strip()
                prop = (r.get("prop") or "").upper()
                cat  = (r.get("cat") or "").upper()
                if cat == "PER" and prop == "PROP" and 0 < len(text.split()) <= 4:
                    surface2cid[text] = cid
    except Exception:
        pass

    return surface2cid

def init_enlp_caches(quotes_path, entities_path, html_path=None):
    """
    Initialize globals:
      - ENLP_QUOTE_INDEX  : normed-quote -> rows
      - ENLP_CID2CANON    : cid -> canonical name
      - ENLP_COREF_MAP    : normalized surface -> cid (conservative)
      - ENLP_LAST_DIR     : directory containing this run's ENLP files
      - ENLP_LAST_PREFIX  : prefix (e.g., 'book_input')
      - ENLP_CLUSTER_STATS: {'narr': {...}, 'quote': {...}} (ensured)
    Call once per run_attribution.
    """
    # Keep track of this run's directory & prefix (for later file lookups)
    try:
        import os  # ensure available even if not at module top
        q_dir = os.path.dirname(os.path.abspath(quotes_path))
        base = os.path.basename(quotes_path)           # e.g., 'book_input.quotes(edit).txt'
        prefix = base.split(".")[0]                    # -> 'book_input'
        globals()["ENLP_LAST_DIR"] = q_dir
        globals()["ENLP_LAST_PREFIX"] = prefix
    except Exception:
        globals()["ENLP_LAST_DIR"] = None
        globals()["ENLP_LAST_PREFIX"] = None

    # Ensure cluster stats container exists (even if empty now)
    if not isinstance(globals().get("ENLP_CLUSTER_STATS"), dict):
        globals()["ENLP_CLUSTER_STATS"] = {"narr": {}, "quote": {}}

    # Load ENLP artifacts
    quotes = load_enlp_quotes(quotes_path)
    cid2canon = load_enlp_canonical_map_from_entities(entities_path)
    quote_index = _build_quote_index(quotes)
    coref_map = load_enlp_coref_surface_map(entities_path, cid2canon)

    # Publish globals
    globals()["ENLP_QUOTE_INDEX"] = quote_index
    globals()["ENLP_CID2CANON"] = cid2canon
    globals()["ENLP_COREF_MAP"] = coref_map

    # Optional: lightweight telemetry
    try:
        qcount = sum(len(v) for v in quote_index.values())
    except Exception:
        qcount = 0
    try:
        ccount = len(cid2canon)
    except Exception:
        ccount = 0
    try:
        log(f"[enlp/init] dir={globals().get('ENLP_LAST_DIR')} "
            f"prefix={globals().get('ENLP_LAST_PREFIX')} "
            f"quotes={qcount} chars={ccount} coref={len(coref_map)}")
    except Exception:
        pass

    return {
        "ENLP_QUOTE_INDEX": quote_index,
        "ENLP_CID2CANON": cid2canon,
        "ENLP_COREF_MAP": coref_map
    }

class EnglishBookNLP:

    def __init__(self, model_params):

        with torch.no_grad():

            start_time = time.time()

            print(model_params)

            spacy_model="en_core_web_md"
            if "spacy_model" in model_params:
                spacy_model=model_params["spacy_model"]

            spacy_nlp = spacy.load(spacy_model, disable=["ner"])

            valid_keys=set("entity,event,supersense,quote,coref".split(","))
            
            pipes=model_params["pipeline"].split(",")

            self.gender_cats= [ ["he", "him", "his"], ["she", "her"], ["they", "them", "their"], ["xe", "xem", "xyr", "xir"], ["ze", "zem", "zir", "hir"] ] 

            if "referential_gender_cats" in model_params:
                self.gender_cats=model_params["referential_gender_cats"]

            home = str(Path.home())
            modelPath=os.path.join(home, "booknlp_models")
            if "model_path"  in model_params:            
                modelPath=model_params["model_path"]

            if not Path(modelPath).is_dir():
                Path(modelPath).mkdir(parents=True, exist_ok=True)

            # Handle legacy "english" model name - map to "small"
            model_name = model_params["model"]
            if model_name == "english":
                model_name = "small"
                print("Note: 'english' model mapped to 'small' model")

            if model_name == "big":
                entityName="entities_google_bert_uncased_L-6_H-768_A-12-v1.0.model"
                corefName="coref_google_bert_uncased_L-12_H-768_A-12-v1.0.model"
                quoteAttribName="speaker_google_bert_uncased_L-12_H-768_A-12-v1.0.1.model"

                self.entityPath=os.path.join(modelPath, entityName)
                if not Path(self.entityPath).is_file():
                    print("downloading %s" % entityName)
                    urllib.request.urlretrieve("http://people.ischool.berkeley.edu/~dbamman/booknlp_models/%s" % entityName, self.entityPath)

                self.coref_model=os.path.join(modelPath, corefName)
                if not Path(self.coref_model).is_file():
                    print("downloading %s" % corefName)
                    urllib.request.urlretrieve("http://people.ischool.berkeley.edu/~dbamman/booknlp_models/%s" % corefName, self.coref_model)

                self.quoteAttribModel=os.path.join(modelPath, quoteAttribName)
                if not Path(self.quoteAttribModel).is_file():
                    print("downloading %s" % quoteAttribName)
                    urllib.request.urlretrieve("http://people.ischool.berkeley.edu/~dbamman/booknlp_models/%s" % quoteAttribName, self.quoteAttribModel)


            elif model_name == "small":
                entityName="entities_google_bert_uncased_L-4_H-256_A-4-v1.0.model"
                corefName="coref_google_bert_uncased_L-2_H-256_A-4-v1.0.model"
                quoteAttribName="speaker_google_bert_uncased_L-8_H-256_A-4-v1.0.1.model"

                self.entityPath=os.path.join(modelPath, entityName)
                if not Path(self.entityPath).is_file():
                    print("downloading %s" % entityName)
                    urllib.request.urlretrieve("http://people.ischool.berkeley.edu/~dbamman/booknlp_models/%s" % entityName, self.entityPath)

                self.coref_model=os.path.join(modelPath, corefName)
                if not Path(self.coref_model).is_file():
                    print("downloading %s" % corefName)
                    urllib.request.urlretrieve("http://people.ischool.berkeley.edu/~dbamman/booknlp_models/%s" % corefName, self.coref_model)

                self.quoteAttribModel=os.path.join(modelPath, quoteAttribName)
                if not Path(self.quoteAttribModel).is_file():
                    print("downloading %s" % quoteAttribName)
                    urllib.request.urlretrieve("http://people.ischool.berkeley.edu/~dbamman/booknlp_models/%s" % quoteAttribName, self.quoteAttribModel)

            elif model_name == "custom":
                self.entityPath=model_params["entity_model_path"]
                self.coref_model=model_params["coref_model_path"]
                self.quoteAttribModel=model_params["quote_attribution_model_path"]


            self.doEntities=self.doCoref=self.doQuoteAttrib=self.doSS=self.doEvent=False

            for pipe in pipes:
                if pipe not in valid_keys:
                    print("unknown pipe: %s" % pipe)
                    sys.exit(1)
                if pipe == "entity":
                    self.doEntities=True
                elif pipe == "event":
                    self.doEvent=True
                elif pipe == "coref":
                    self.doCoref=True
                elif pipe == "supersense":
                    self.doSS=True
                elif pipe == "quote":
                    self.doQuoteAttrib=True

            tagsetPath="data/entity_cat.tagset"
            tagsetPath = pkg_resources.resource_filename(__name__, tagsetPath)


            if "referential_gender_hyperparameterFile" in model_params:
                self.gender_hyperparameterFile=model_params["referential_gender_hyperparameterFile"]
            else:
                self.gender_hyperparameterFile = pkg_resources.resource_filename(__name__, "data/gutenberg_prop_gender_terms.txt")
            
            pronominalCorefOnly=True

            if "pronominalCorefOnly" in model_params:
                pronominalCorefOnly=model_params["pronominalCorefOnly"]

            if not self.doEntities and self.doCoref:
                print("coref requires entity tagging")
                sys.exit(1)

            if not self.doQuoteAttrib and self.doCoref:
                print("coref requires quotation attribution")
                sys.exit(1)
            if not self.doEntities and self.doQuoteAttrib:
                print("quotation attribution requires entity tagging")
                sys.exit(1)    


            self.quoteTagger=QuoteTagger()

            if self.doEntities:
                self.entityTagger=LitBankEntityTagger(self.entityPath, tagsetPath)
                aliasPath = pkg_resources.resource_filename(__name__, "data/aliases.txt")
                self.name_resolver=NameCoref(aliasPath)


            if self.doQuoteAttrib:
                self.quote_attrib=QuotationAttribution(self.quoteAttribModel)

            
            if self.doCoref:
                self.litbank_coref=LitBankCoref(self.coref_model, self.gender_cats, pronominalCorefOnly=pronominalCorefOnly)

            self.tagger=SpacyPipeline(spacy_nlp)

            print("--- startup: %.3f seconds ---" % (time.time() - start_time))

    def get_syntax(self, tokens, entities, assignments, genders):

        def check_conj(tok, tokens):
            if tok.deprel == "conj" and tok.dephead != tok.token_id:
                # print("found conj", tok.text)
                return tokens[tok.dephead]
            return tok

        def get_head_in_range(start, end, tokens):
            for i in range(start, end+1):
                if tokens[i].dephead < start or tokens[i].dephead > end:
                    return tokens[i]
            return None

        agents={}
        patients={}
        poss={}
        mods={}
        prop_mentions={}
        pron_mentions={}
        nom_mentions={}
        keys=Counter()


        toks_by_children={}
        for tok in tokens:
            if tok.dephead not in toks_by_children:
                toks_by_children[tok.dephead]={}
            toks_by_children[tok.dephead][tok]=1

        for idx, (start_token, end_token, cat, phrase) in enumerate(entities):
            ner_prop=cat.split("_")[0]
            ner_type=cat.split("_")[1]

            if ner_type != "PER":
                continue

            coref=assignments[idx]

            keys[coref]+=1
            if coref not in agents:
                agents[coref]=[]
                patients[coref]=[]
                poss[coref]=[]
                mods[coref]=[]
                prop_mentions[coref]=Counter()
                pron_mentions[coref]=Counter()
                nom_mentions[coref]=Counter()

            if ner_prop == "PROP":
                prop_mentions[coref][phrase]+=1
            elif ner_prop == "PRON":
                pron_mentions[coref][phrase]+=1
            elif ner_prop == "NOM":
                nom_mentions[coref][phrase]+=1


            tok=get_head_in_range(start_token, end_token, tokens)
            if tok is not None:

                tok=check_conj(tok, tokens)
                head=tokens[tok.dephead]

                # nsubj
                # mod
                if tok.deprel == "nsubj" and head.lemma == "be":
                    for sibling in toks_by_children[head.token_id]:

                        # "he was strong and happy", where happy -> conj -> strong -> attr/acomp -> be
                        sibling_id=sibling.token_id
                        sibling_tok=tokens[sibling_id]
                        if (sibling_tok.deprel == "attr" or sibling_tok.deprel == "acomp") and (sibling_tok.pos == "NOUN" or sibling_tok.pos == "ADJ"):
                            mods[coref].append({"w":sibling_tok.text, "i":sibling_tok.token_id})

                            if sibling.token_id in toks_by_children:
                                for grandsibling in toks_by_children[sibling.token_id]:
                                    grandsibling_id=grandsibling.token_id
                                    grandsibling_tok=tokens[grandsibling_id]

                                    if grandsibling_tok.deprel == "conj" and (grandsibling_tok.pos == "NOUN" or grandsibling_tok.pos == "ADJ"):
                                        mods[coref].append({"w":grandsibling_tok.text, "i":grandsibling_tok.token_id})



                # ("Bill and Ted ran" conj captured by check_conj above)
                elif tok.deprel == "nsubj" and head.pos == ("VERB"):
                    agents[coref].append({"w":head.text, "i":head.token_id})

                # "Bill ducked and ran", where ran -> conj -> ducked
                    for sibling in toks_by_children[head.token_id]:
                        sibling_id=sibling.token_id
                        sibling_tok=tokens[sibling_id]
                        if sibling_tok.deprel == "conj" and sibling_tok.pos == "VERB":
                            agents[coref].append({"w":sibling_tok.text, "i":sibling_tok.token_id})
                
                # "Jack was hit by John and William" conj captured by check_conj above
                elif tok.deprel == "pobj" and head.deprel == "agent":
                    # not root
                    if head.dephead != head.token_id:
                        grandparent=tokens[head.dephead]
                        if grandparent.pos.startswith("V"):
                            agents[coref].append({"w":grandparent.text, "i":grandparent.token_id})


                # patient ("He loved Bill and Ted" conj captured by check_conj above)
                elif (tok.deprel == "dobj" or tok.deprel == "nsubjpass") and head.pos == "VERB":
                    patients[coref].append({"w":head.text, "i":head.token_id})


                # poss

                elif tok.deprel == "poss":
                    poss[coref].append({"w":head.text, "i":head.token_id})

                    # "her house and car", where car -> conj -> house
                    for sibling in toks_by_children[head.token_id]:
                        sibling_id=sibling.token_id
                        sibling_tok=tokens[sibling_id]
                        if sibling_tok.deprel == "conj":
                            poss[coref].append({"w":sibling_tok.text, "i":sibling_tok.token_id})
                    

        data={}
        data["characters"]=[]

        for coref, total_count in keys.most_common():

            # must observe a character at least *twice*

            if total_count > 1:
                chardata={}
                chardata["agent"]=agents[coref]
                chardata["patient"]=patients[coref]
                chardata["mod"]=mods[coref]
                chardata["poss"]=poss[coref]
                chardata["id"]=coref
                if coref in genders:
                    chardata["g"]=genders[coref]
                else:
                    chardata["g"]=None
                chardata["count"]=total_count

                mentions={}

                pnames=[]
                for k,v in prop_mentions[coref].most_common():
                    pnames.append({"c":v, "n":k})
                mentions["proper"]=pnames

                nnames=[]
                for k,v in nom_mentions[coref].most_common():
                    nnames.append({"c":v, "n":k})
                mentions["common"]=nnames

                prnames=[]
                for k,v in pron_mentions[coref].most_common():
                    prnames.append({"c":v, "n":k})
                mentions["pronoun"]=prnames

                chardata["mentions"]=mentions

                
                data["characters"].append(chardata)
            
        return data


    def normalize_character_name(self, name):
        """
        Normalize character name to camelCase format without spaces or special characters
        """
        import re
        
        # Remove special characters except spaces and apostrophes
        name = re.sub(r"[^\w\s']", "", name)
        
        # Handle possessives (e.g., "Tom's" -> "Toms")
        name = re.sub(r"'s\b", "s", name)
        name = re.sub(r"'", "", name)
        
        # Split on whitespace and capitalize each word
        words = name.split()
        if not words:
            return "UnknownCharacter"
        
        # First word capitalized, rest capitalized (camelCase)
        normalized = words[0].capitalize()
        for word in words[1:]:
            normalized += word.capitalize()
        
        # Ensure it starts with a letter
        if not normalized or not normalized[0].isalpha():
            normalized = "character" + normalized.capitalize()
        
        return normalized

    def infer_age_category_with_scores(self, character_data):
        """
        Use semantic similarity to infer age category with confidence scores for all categories
        """
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(self, '_age_model'):
                self._age_model = SentenceTransformer('all-MiniLM-L6-v2')
            model = self._age_model
        except ImportError:
            print("Warning: sentence-transformers not installed. Age inference unavailable.")
            return {"category": "unknown", "scores": {"child": 0.0, "teen": 0.0, "adult": 0.0, "elder": 0.0}}
        except Exception as e:
            print(f"Warning: Could not load sentence transformer model: {e}")
            return {"category": "unknown", "scores": {"child": 0.0, "teen": 0.0, "adult": 0.0, "elder": 0.0}}
        
        age_prototypes = {
            'child': [
                "young child", "little kid", "small child", "baby", "toddler", 
                "young boy", "little girl", "infant", "youngster"
            ],
            'teen': [
                "teenager", "adolescent", "young person", "teenage boy", 
                "teenage girl", "youth", "high school student"
            ],
            'adult': [
                "adult man", "adult woman", "grown person", "mature person",
                "middle-aged man", "middle-aged woman", "working adult"
            ],
            'elder': [
                "elderly person", "old man", "old woman", "senior citizen",
                "aged person", "grandfather", "grandmother", "elderly gentleman"
            ]
        }
        
        # Get descriptors
        descriptors = []
        descriptors.extend([mod['w'] for mod in character_data.get('mod', [])])
        descriptors.extend([mention['n'] for mention in character_data.get('mentions', {}).get('common', [])])
        
        if not descriptors:
            return {"category": "unknown", "scores": {"child": 0.0, "teen": 0.0, "adult": 0.0, "elder": 0.0}}
        
        character_description = " ".join(descriptors)
        
        # Calculate similarities for ALL categories
        category_scores = {}
        best_category = "unknown"
        best_score = 0.0
        
        try:
            for category, prototypes in age_prototypes.items():
                prototype_embeddings = model.encode(prototypes)
                char_embedding = model.encode([character_description])
                
                similarities = model.similarity(char_embedding, prototype_embeddings)
                max_similarity = float(similarities.max())
                
                category_scores[category] = round(max_similarity, 3)
                
                if max_similarity > best_score and max_similarity > 0.2:
                    best_score = max_similarity
                    best_category = category
            
        except Exception as e:
            print(f"Warning: Error during age inference: {e}")
            return {"category": "unknown", "scores": {"child": 0.0, "teen": 0.0, "adult": 0.0, "elder": 0.0}}
        
        return {"category": best_category, "scores": category_scores}

    def generate_character_json(self, entities, assignments, genders, chardata, outFolder, idd):
        """
        Generate a JSON file with character information including TTS settings and age inference with scores
        """
                # --- NEW: init ENLP caches and compute zone counts for this run ---
        try:
            quotes_path   = os.path.join(outFolder, f"{idd}.quotes")
            entities_path = os.path.join(outFolder, f"{idd}.entities")
            # Initialize caches (indexes + canonical names + surface map)
            init_enlp_caches(quotes_path, entities_path)
            # Compute narration vs in-quote mention counts; stored in ENLP_CLUSTER_STATS
            _ = compute_zone_counts(outdir=outFolder, prefix=idd)
        except Exception as e:
            print(f"[enlp/init] skipped: {e}")

        # QUOTE_COUNTS_LOCAL: count quotes per char_id from <outFolder>/<idd>.quotes
        quote_counts = {}
        try:
            quotes_path = os.path.join(outFolder, f"{idd}.quotes")
            with open(quotes_path, 'r', encoding='utf-8', errors='replace') as _f:
                _ = _f.readline()  # header
                for _line in _f:
                    _parts = _line.rstrip('\n').split('\t')
                    if len(_parts) >= 6:
                        _cid = _parts[5].strip()  # char_id column
                        if _cid:
                            quote_counts[_cid] = quote_counts.get(_cid, 0) + 1
        except Exception:
            quote_counts = {}

        # CLUSTER_PROP_PER_LOCAL: compute clusters with at least one PROP_PER mention
        cluster_has_prop_per = set()
        for _idx, (_s, _e, _cat, _text) in enumerate(entities):
            try:
                _coref = assignments[_idx]
            except Exception:
                continue
            _parts = _cat.split('_') if isinstance(_cat, str) else []
            if len(_parts) >= 2 and _parts[0] == 'PROP' and _parts[1] == 'PER':
                cluster_has_prop_per.add(_coref)

                # ---- SUBJECT-ONLY SUPPORT: build quote token ranges and mention counts ----
                # Load quote token spans from the quotes file so we can detect mentions "inside quotes" vs narration
                quote_ranges = []
                try:
                    quotes_path = os.path.join(outFolder, f"{idd}.quotes")
                    with open(quotes_path, 'r', encoding='utf-8', errors='replace') as _f:
                        _ = _f.readline()  # header
                        for _line in _f:
                            _parts = _line.rstrip('\n').split('\t')
                            if len(_parts) >= 2:
                                try:
                                    qs = int(_parts[0]); qe = int(_parts[1])
                                    quote_ranges.append((qs, qe))
                                except Exception:
                                    pass
                except Exception:
                    quote_ranges = []

                def _overlaps_any(_s, _e, _ranges):
                    for (qs, qe) in _ranges:
                        if not (_e < qs or _s > qe):
                            return True
                    return False

                # Count mentions by zone (in-quote vs narration), keyed by cluster_id
                narr_mentions = {}
                quote_mentions = {}
                for idx_ent, (start, end, cat, text) in enumerate(entities):
                    try:
                        cid = int(assignments[idx_ent])
                    except Exception:
                        continue
                    if cid is None:
                        continue
                    if _overlaps_any(int(start), int(end), quote_ranges):
                        quote_mentions[cid] = quote_mentions.get(cid, 0) + 1
                    else:
                        narr_mentions[cid] = narr_mentions.get(cid, 0) + 1

        def map_gender_to_standard(gender_data):
            """
            Map gender inference results to 'male', 'female', or 'unknown' based on highest score
            """
            if gender_data is None:
                return "unknown"
                
            # Get the inference scores
            inference_scores = gender_data.get("inference", {})
            
            # Map pronoun groups to standard genders
            gender_mapping = {
                "he/him/his": "male",
                "she/her": "female",
                # Ignore other categories like "they/them/their", "xe/xem/xyr", etc.
            }
            
            # Find the highest scoring valid gender
            max_score = 0.0
            best_gender = "unknown"
            
            for pronoun_group, score in inference_scores.items():
                if pronoun_group in gender_mapping and score > max_score:
                    max_score = score
                    best_gender = gender_mapping[pronoun_group]
            
            # Only return a gender if the confidence is reasonable (e.g., > 0.1)
            if max_score > 0.1:
                return best_gender
            else:
                return "unknown"
        
        # Get canonical names for characters
        names = {}
        for idx, (start, end, cat, text) in enumerate(entities):
            coref = assignments[idx]
            if coref not in names:
                names[coref] = Counter()
            ner_prop = cat.split("_")[0]
            ner_type = cat.split("_")[1]
            if ner_prop == "PROP":
                names[coref][text.lower()] += 10
            elif ner_prop == "NOM":
                names[coref][text.lower()] += 1
            else:
                names[coref][text.lower()] += 0.001
        
        # Get canonical name for each character ID
        char_names = {}
        for coref, name_counter in names.items():
            if name_counter:
                char_names[coref] = name_counter.most_common(1)[0][0]
            else:
                char_names[coref] = f"character_{coref}"
        
        # Build character information
        characters_info = []
        
        # Add narrator first
        narrator_char = {
            "character_id": "Narrator",
            "canonical_name": "Narrator",
            "normalized_name": "Narrator",
            "inferred_gender": "unknown",
            "gender_scores": {},
            "inferred_age_category": "unknown",
            "age_confidence_scores": {"child": 0.0, "teen": 0.0, "adult": 0.0, "elder": 0.0},
            "mention_count": 0,
            "tts_engine": "XTTSv2",
            "language": "eng",
            "voice": None
        }
        characters_info.append(narrator_char)

                # --- NEW: garbage/ambiguous surface blacklist + alias normalization ---
        BAD_SURFACES = {
            "we","you","they","guys","boys","girls","men","women","man","woman",
            "god","lord","sir","maam","mr","mrs","ms","miss","buddy","pal","dude"
        }

        def _canonicalize_name(cid, fallback):
            name = (char_names.get(cid) or fallback or "").strip()
            import re
            safe = re.sub(r"[^A-Za-z'\- ]+", " ", name).strip()
            toks = [t for t in re.split(r"\s+", safe) if t]
            if not toks:
                return fallback
            if safe.lower() in BAD_SURFACES:
                return None
            if len(toks) >= 2:
                return " ".join(w.title() for w in toks)
            if toks[0].lower() in BAD_SURFACES or not toks[0].isalpha():
                return None
            return toks[0].title()

        
        # Add characters from chardata
        for character in chardata["characters"]:
            char_id = character["id"]
            age_result = self.infer_age_category_with_scores(character)
            canonical_name = _canonicalize_name(char_id, f"character_{char_id}")
            if not canonical_name:
                # skip garbage-only clusters
                continue

            
            # Map the gender to standard format
            raw_gender_data = character.get("g", None)
            standardized_gender = map_gender_to_standard(raw_gender_data)
            
            # Preserve the original gender scores
            gender_scores = {}
            if raw_gender_data and "inference" in raw_gender_data:
                gender_scores = raw_gender_data["inference"]
            
            char_info = {
                "character_id": char_id,
                "canonical_name": canonical_name,
                "normalized_name": self.normalize_character_name(canonical_name),
                "inferred_gender": standardized_gender,
                "gender_scores": gender_scores,
                "inferred_age_category": age_result["category"],
                "age_confidence_scores": age_result["scores"],
                "mention_count": character["count"],
                "tts_engine": "XTTSv2",
                "language": "eng",
                "voice": None
            }

             # ---- SUBJECT-ONLY SUPPRESSION --------------------------------------
            SUBJECT_ONLY_MIN_QUOTE_MENTIONS = 2   # tweakable
            SUBJECT_ONLY_MAX_NARR_MENTIONS = 0    # tweakable

            # speaker line count (from the quotes file)
            spk_lines = quote_counts.get(str(char_id), 0)

            # mention counts by zone (computed above from entities + quote_ranges)
            qm = quote_mentions.get(char_id, 0)
            nm = narr_mentions.get(char_id, 0)

            # If a character never speaks, is mentioned multiple times inside quotes,
            # and is (almost) not mentioned in narration → treat as “subject-only” and skip.
            if (spk_lines == 0) and (qm >= SUBJECT_ONLY_MIN_QUOTE_MENTIONS) and (nm <= SUBJECT_ONLY_MAX_NARR_MENTIONS):
                # e.g., Liddy King discussed by others but never speaks
                continue

            # EMIT_GUARD_PATCH: skip clusters without proper names, undermentioned, or generic names
            MIN_MENTIONS = 2
            canonical_for_id = char_names.get(char_id, f"character_{char_id}")
            norm_name = self.normalize_character_name(canonical_for_id).lower()
            import re
            if (char_id not in cluster_has_prop_per) or (character.get("count", 0) < MIN_MENTIONS) or re.match(r'^(the\s+)?(old|older|young|tall|short)\s+(man|woman|men|women)$', norm_name):
                continue
            # QUOTE_GUARD_PATCH: require at least N quoted lines for this character
            MIN_QUOTE_LINES = 0  # allow characters with few attributed lines to pass
            if quote_counts.get(str(char_id), 0) < MIN_QUOTE_LINES:
              continue
            characters_info.append(char_info)
                # --- NEW: enforce single Narrator at index 0 ---
        if characters_info and characters_info[0].get("normalized_name","") != "Narrator":
            characters_info = [c for c in characters_info if c.get("normalized_name","") != "Narrator"]
            narrator_stub = {
                "character_id": "Narrator",
                "canonical_name": "Narrator",
                "normalized_name": "Narrator",
                "inferred_gender": "unknown",
                "gender_scores": {},
                "inferred_age_category": "unknown",
                "age_confidence_scores": {"child": 0.0, "teen": 0.0, "adult": 0.0, "elder": 0.0},
                "mention_count": 0,
                "tts_engine": "XTTSv2",
                "language": "eng",
                "voice": None
            }
            characters_info.insert(0, narrator_stub)
        
        # Build the JSON structure
        result = {
            "metadata": {
                "generated_by": "BookNLP",
                "generated_at": "2025-07-18 05:43:37",
                "generated_by_user": "DrewThomasson",
                "document_id": idd,
                "total_characters": len(characters_info)
            },
            "characters": characters_info
        }
        
        # Write JSON file
        with open(join(outFolder, "%s.characters.json" % (idd)), "w", encoding="utf-8") as out:
            json.dump(result, out, indent=2, ensure_ascii=False)
        
        return result


    def generate_simplified_character_json(self, entities, assignments, genders, chardata, outFolder, idd):
        """
        Generate a simplified JSON file with only essential character information for TTS
        """
                # --- NEW: init ENLP caches and compute zone counts for this run ---
        try:
            quotes_path   = os.path.join(outFolder, f"{idd}.quotes")
            entities_path = os.path.join(outFolder, f"{idd}.entities")
            init_enlp_caches(quotes_path, entities_path)
            _ = compute_zone_counts(outdir=outFolder, prefix=idd)
        except Exception as e:
            print(f"[enlp/init] skipped: {e}")

        # QUOTE_COUNTS_LOCAL: count quotes per char_id from <outFolder>/<idd>.quotes
        quote_counts = {}
        try:
            quotes_path = os.path.join(outFolder, f"{idd}.quotes")
            with open(quotes_path, 'r', encoding='utf-8', errors='replace') as _f:
                _ = _f.readline()  # header
                for _line in _f:
                    _parts = _line.rstrip('\n').split('\t')
                    if len(_parts) >= 6:
                        _cid = _parts[5].strip()  # char_id column
                        if _cid:
                            quote_counts[_cid] = quote_counts.get(_cid, 0) + 1
        except Exception:
            quote_counts = {}

        # CLUSTER_PROP_PER_LOCAL: compute clusters with at least one PROP_PER mention
        cluster_has_prop_per = set()
        for _idx, (_s, _e, _cat, _text) in enumerate(entities):
            try:
                _coref = assignments[_idx]
            except Exception:
                continue
            _parts = _cat.split('_') if isinstance(_cat, str) else []
            if len(_parts) >= 2 and _parts[0] == 'PROP' and _parts[1] == 'PER':
                cluster_has_prop_per.add(_coref)
        # ---- SUBJECT-ONLY SUPPORT: build quote token ranges and mention counts ----
        # Build quote token spans from the quotes file so we can detect mentions "inside quotes" vs narration
        quote_ranges = []
        try:
            quotes_path = os.path.join(outFolder, f"{idd}.quotes")
            with open(quotes_path, 'r', encoding='utf-8', errors='replace') as _f:
                _ = _f.readline()  # header
                for _line in _f:
                    _parts = _line.rstrip('\n').split('\t')
                    if len(_parts) >= 2:
                        try:
                            qs = int(_parts[0]); qe = int(_parts[1])
                            quote_ranges.append((qs, qe))
                        except Exception:
                            pass
        except Exception:
            quote_ranges = []

        def _overlaps_any(_s, _e, _ranges):
            for (qs, qe) in _ranges:
                if not (_e < qs or _s > qe):
                    return True
            return False

        # Count mentions by zone (in-quote vs narration), keyed by cluster_id
        narr_mentions = {}
        quote_mentions = {}
        for idx_ent, (start, end, cat, text) in enumerate(entities):
            # cluster id from assignments
            cid = None
            try:
                cid = assignments[idx_ent]
            except Exception:
                cid = None
            try:
                cid = int(cid)
            except Exception:
                continue
            if cid is None or cid < 0:
                continue

            # token span
            try:
                ms = int(start); me = int(end)
            except Exception:
                continue

            if _overlaps_any(ms, me, quote_ranges):
                quote_mentions[cid] = quote_mentions.get(cid, 0) + 1
            else:
                narr_mentions[cid] = narr_mentions.get(cid, 0) + 1


        
        def map_gender_to_standard(gender_data):
            """
            Map gender inference results to 'male', 'female', or 'unknown' based on highest score
            """
            if gender_data is None:
                return "unknown"
                
            # Get the inference scores
            inference_scores = gender_data.get("inference", {})
            
            # Map pronoun groups to standard genders
            gender_mapping = {
                "he/him/his": "male",
                "she/her": "female",
                # Ignore other categories like "they/them/their", "xe/xem/xyr", etc.
            }
            
            # Find the highest scoring valid gender
            max_score = 0.0
            best_gender = "unknown"
            
            for pronoun_group, score in inference_scores.items():
                if pronoun_group in gender_mapping and score > max_score:
                    max_score = score
                    best_gender = gender_mapping[pronoun_group]
            
            # Only return a gender if the confidence is reasonable (e.g., > 0.1)
            if max_score > 0.1:
                return best_gender
            else:
                return "unknown"
        
        # Get canonical names for characters
        names = {}
        for idx, (start, end, cat, text) in enumerate(entities):
            coref = assignments[idx]
            if coref not in names:
                names[coref] = Counter()
            ner_prop = cat.split("_")[0]
            ner_type = cat.split("_")[1]
            if ner_prop == "PROP":
                names[coref][text.lower()] += 10
            elif ner_prop == "NOM":
                names[coref][text.lower()] += 1
            else:
                names[coref][text.lower()] += 0.001
        
        # Get canonical name for each character ID
        char_names = {}
        for coref, name_counter in names.items():
            if name_counter:
                char_names[coref] = name_counter.most_common(1)[0][0]
            else:
                char_names[coref] = f"character_{coref}"
        
        # Build simplified character information
        characters_info = []
        
        # Add narrator first
        narrator_char = {
            "normalized_name": "Narrator",
            "inferred_gender": "unknown",
            "inferred_age_category": "unknown",
            "tts_engine": "XTTSv2",
            "language": "eng",
            "voice": None
        }
        characters_info.append(narrator_char)

                # --- NEW: garbage/ambiguous surface blacklist + alias normalization ---
        BAD_SURFACES = {
            "we","you","they","guys","boys","girls","men","women","man","woman",
            "god","lord","sir","maam","mr","mrs","ms","miss","buddy","pal","dude"
        }

        def _canonicalize_name(cid, fallback, char_names_local):
            name = (char_names_local.get(cid) or fallback or "").strip()
            import re
            safe = re.sub(r"[^A-Za-z'\- ]+", " ", name).strip()
            toks = [t for t in re.split(r"\s+", safe) if t]
            if not toks:
                return fallback
            if safe.lower() in BAD_SURFACES:
                return None
            if len(toks) >= 2:
                return " ".join(w.title() for w in toks)
            if toks[0].lower() in BAD_SURFACES or not toks[0].isalpha():
                return None
            return toks[0].title()
        
        # Add characters from chardata
        for character in chardata["characters"]:
            char_id = character["id"]
            age_result = self.infer_age_category_with_scores(character)
            canonical_name = _canonicalize_name(char_id, f"character_{char_id}", char_names)
            if not canonical_name:
                continue

            
            # Map the gender to standard format
            raw_gender_data = character.get("g", None)
            standardized_gender = map_gender_to_standard(raw_gender_data)
            
            char_info = {
                "normalized_name": self.normalize_character_name(canonical_name),
                "inferred_gender": standardized_gender,
                "inferred_age_category": age_result["category"],
                "tts_engine": "XTTSv2",
                "language": "eng",
                "voice": None
            }
            # EMIT_GUARD_PATCH: skip clusters without proper names, undermentioned, or generic names
            MIN_MENTIONS = 4
            canonical_for_id = char_names.get(char_id, f"character_{char_id}")
            norm_name = self.normalize_character_name(canonical_for_id).lower()
            import re
            if (char_id not in cluster_has_prop_per) or (character.get("count", 0) < MIN_MENTIONS) or re.match(r'^(the\s+)?(old|older|young|tall|short)\s+(man|woman|men|women)$', norm_name):
                continue
            # QUOTE_GUARD_PATCH: require at least N quoted lines for this character
            MIN_QUOTE_LINES = 1  # still a touch stricter for the 'simple' file
            if quote_counts.get(str(char_id), 0) < MIN_QUOTE_LINES:
                continue
            characters_info.append(char_info)
        
        # Build the simplified JSON structure
        result = {
            "characters": characters_info
        }
                
        return result

    def write_characters_simple(self, entities, assignments, outFolder, idd):
        """
        Build a full-name-first character map and write <idd>.characters_simple.json

        Output:
        {
        "characters": [
            {"normalized_name": "Zack Hatfield", "aliases": ["Zack","Hatfield"], "char_id": 12},
            ...
        ]
        }
        """
        import os, re, json
        from collections import Counter, defaultdict

        path = os.path.join(outFolder, f"{idd}.characters_simple.json")

        # 1) collect name evidence per coref cluster
        prop = defaultdict(Counter)   # proper names (weighted)
        nom  = defaultdict(Counter)   # nominal heads (light)
        for idx, ent in enumerate(entities or []):
            # expect ent like: (start, end, cat, text)
            try:
                _s, _e, cat, text = ent
            except Exception:
                continue
            coref = assignments[idx] if idx < len(assignments) else None
            if not isinstance(coref, int):
                continue
            if not text:
                continue
            t = (text or "").strip()
            if not t:
                continue
            tag = str(cat).split("_")[0] if cat else ""
            if tag == "PROP":
                prop[coref][t] += 10
            elif tag == "NOM":
                nom[coref][t] += 1

        def _norm(s):
            return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z\s'\-]", "", s or "")).strip()

        # 2) choose canonical: prefer the most frequent multi-token proper name
        canon = {}
        raw_mentions = {}
        for cid, cnt in prop.items():
            if not cnt:
                continue
            cand = sorted(cnt.items(),
                        key=lambda kv: (len(_norm(kv[0]).split()), kv[1]),
                        reverse=True)
            best = _norm(cand[0][0]).title()
            canon[cid] = best
            raw_mentions[cid] = { _norm(x).title() for x, _c in cnt.items() if _norm(x) }

        # 3) fallback to nominal if no proper name
        for cid, cnt in nom.items():
            if cid in canon or not cnt:
                continue
            best = _norm(cnt.most_common(1)[0][0]).title()
            if best.lower() in {"man","woman","person","boy","girl"}:
                continue
            canon[cid] = best
            raw_mentions[cid] = {best}

        def toks(n):
            return [t for t in _norm(n).split() if t]

        # 4) gather candidate aliases (full, first, last, proper variants)
        bag = defaultdict(set)  # canonical -> set of alias tokens/variants
        for cid, cname in canon.items():
            ts = toks(cname)
            if not ts:
                continue
            bag[cname].add(" ".join(ts).title())
            bag[cname].add(ts[0].title())
            bag[cname].add(ts[-1].title())
            for m in (raw_mentions.get(cid) or []):
                bag[cname].add(m)

        # 5) keep only aliases that are UNIQUE across canonicals (avoid “King” ambiguity)
        token_to_cans = defaultdict(set)
        for can, vals in bag.items():
            for v in vals:
                for t in toks(v):
                    token_to_cans[t.lower()].add(can)

        uniq = defaultdict(set)
        for can, vals in bag.items():
            for v in vals:
                for t in toks(v):
                    tl = t.lower()
                    if len(token_to_cans[tl]) == 1:
                        uniq[can].add(t.title())

        # 6) emit JSON
        out = {"characters": []}

        def sort_key(nm):
            ts = nm.split()
            return (ts[-1] if ts else nm, ts[0] if ts else nm)

        for cid, cname in sorted(canon.items(), key=lambda kv: sort_key(kv[1])):
            out["characters"].append({
                "normalized_name": cname,
                "aliases": sorted(uniq[cname]),
                "char_id": cid
            })

        os.makedirs(outFolder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"[characters_simple] wrote {os.path.basename(path)} with {len(out['characters'])} entries")

        
    def fix_punctuation_spacing(self, text):
        """
        Fix spacing around punctuation marks to follow standard English conventions.
        """
        import re

        # NEW: ensure a space when a closing quote is immediately followed by a letter
        text = re.sub(r'([”"])([A-Za-z])', r'\1 \2', text)

        # Remove ALL spaces immediately after opening quotes
        text = re.sub(r'"\s+', '"', text)
        text = re.sub(r"'\s+", "'", text)

        # Remove ALL spaces immediately before closing quotes
        text = re.sub(r'\s+"', '"', text)
        text = re.sub(r"\s+'", "'", text)
        text = re.sub(r'([”"])([A-Za-z])', r'\1 \2', text)

        # Remove spaces before common punctuation marks
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)

        # Remove spaces before closing quotes, parentheses, brackets
        text = re.sub(r'\s+(["\'\)\]\}])', r'\1', text)

        # Fix contractions / possessives
        text = re.sub(r'\s+\'\s*(\w+)', r"'\1", text)
        text = re.sub(r'(\w+)\s+\'\s*(\w+)', r"\1'\2", text)
        text = re.sub(r'(\w+)\s+\'\s*s\b', r"\1's", text)

        # Add space after punctuation if missing (but not before closing punctuation)
        text = re.sub(r'([,.!?;:])([^\s"\'\)\]\}\n])', r'\1 \2', text)

        # Remove space after opening parens/brackets
        text = re.sub(r'([\(\[\{])\s+', r'\1', text)

        # Fix underscores (italics) - remove spaces around them but add space after closing underscore
        text = re.sub(r'_(\w+)_(\w)', r'_\1_ \2', text)

        # Collapse double spaces
        text = re.sub(r'\s{2,}', ' ', text)

        return text.strip()

    
    def _split_dialogue_attribution_merged_sentences(self, lines, normalized_char_names):
        """
        Post-process tagged lines to split cases where SpaCy merged dialogue + attribution.
        
        Examples to split:
          [Steve] "Why?" he went on in a monotone. [/]
            → [Steve] "Why?" [/]
            → [Narrator] he went on in a monotone. [/]
        
          [Washburn] "Kill them" said Hatfield. [/]
            → [Washburn] "Kill them" [/]
            → [Narrator] said Hatfield. [/]
        
        Strategy:
        1. Find lines with both quotes AND attribution verbs
        2. Locate the LAST closing quote in the text
        3. Split: everything before = quote, everything after = attribution
        4. Preserve original speaker for quote, use Narrator for attribution
        """
        import re
        
        # Common attribution verbs
        attrib_verbs = {
            'said', 'says', 'asked', 'replied', 'answered', 'whispered', 
            'shouted', 'muttered', 'cried', 'called', 'yelled', 'murmured',
            'hissed', 'breathed', 'snapped', 'growled', 'moaned', 'told',
            'explained', 'continued', 'went', 'remarked', 'noted', 'observed',
            'insisted', 'demanded', 'protested', 'announced', 'declared',
            'warned', 'begged', 'pleaded', 'laughed', 'sobbed', 'interjected',
            'interrupted', 'conceded', 'promised', 'rejoined', 'stated'
        }
        
        # Build regex pattern for attribution detection
        verb_pattern = '|'.join(sorted(attrib_verbs, key=len, reverse=True))
        # Pattern: verb + optional modifiers + optional name
        attrib_rx = re.compile(
            rf'\b(?:{verb_pattern})\b\s+(?:[a-z]+\s+)?(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)?',
            re.IGNORECASE
        )
        
        result = []
        for line in lines:
            # Parse the tagged line: [Speaker] text [/]
            match = re.match(r'^\[([^\]]+)\]\s*(.*?)\s*\[/\]$', line)
            if not match:
                result.append(line)
                continue
            
            speaker = match.group(1)
            text = match.group(2).strip()
            
            # Check if this line has both quotes AND attribution verbs
            # Include all quote variants: ASCII and smart quotes (opening and closing)
            # Use Unicode escapes to ensure correct characters
            has_quotes = any(q in text for q in [
                '"',          # ASCII double quote
                '\u201c',     # " left double quotation mark
                '\u201d',     # " right double quotation mark
                "'",          # ASCII single quote
                '\u2018',     # ' left single quotation mark
                '\u2019',     # ' right single quotation mark
            ])
            has_attrib = attrib_rx.search(text)
            
            if not (has_quotes and has_attrib):
                # No split needed
                result.append(line)
                continue
            
            # Strategy: Find where the quote ends and attribution begins
            # Look for patterns like:
            #   "Why?" he went on...  (closing quote + space + lowercase word + verb)
            #   "Kill them" said X.   (closing quote + space + verb)
            
            # Try to find a split point using multiple strategies
            split_pos = -1
            quote_part = ""
            attrib_part = ""
            
            # Strategy 1: Look for closing quote + space + attribution verb
            # Pattern: ["'"] + space + attribution_verb
            for i in range(len(text) - 1, -1, -1):
                if text[i] in ['"', '"', "'", "'"]:
                    # Found a potential closing quote
                    after_text = text[i + 1:].strip()
                    
                    # Check if what follows is attribution
                    if after_text and attrib_rx.search(after_text):
                        # Make sure it's reasonably short (not a whole paragraph)
                        if len(after_text) <= 200:
                            split_pos = i + 1
                            quote_part = text[:split_pos].strip()
                            attrib_part = after_text
                            break
            
            # Strategy 2: If no closing quote found, look for sentence-ending punctuation
            # followed by lowercase word + attribution verb (like: "Why? he went on...")
            # OR ending punctuation + opening quote + attribution (like: "Why?" he said...)
            if split_pos == -1:
                # Look for: [.!?] + optional_quote + space + lowercase_word + verb
                for i in range(len(text) - 5):  # Need at least a few chars after
                    if text[i] in '.!?':
                        # Check what comes after the punctuation
                        rest = text[i + 1:].lstrip()
                        
                        # Skip any opening/closing quote right after punctuation
                        skip_idx = 0
                        while skip_idx < len(rest) and rest[skip_idx] in ['"', "'", '\u201c', '\u201d', '"', '\u2018', '\u2019']:
                            skip_idx += 1
                        
                        after_text = rest[skip_idx:].lstrip() if skip_idx < len(rest) else rest
                        
                        # Must start with lowercase word followed by attribution verb
                        if after_text and len(after_text) >= 4:
                            # Check if it looks like attribution
                            if after_text[0].islower() and attrib_rx.search(after_text) and len(after_text) <= 200:
                                # Found it! Split after the punctuation mark
                                split_pos = i + 1
                                quote_part = text[:split_pos].strip()
                                attrib_part = rest  # Keep any quotes that were between
                                break
            
            if split_pos == -1:
                # No good split point found
                result.append(line)
                continue
            
            # Only split if both parts have substance
            if len(quote_part) >= 3 and len(attrib_part) >= 3:
                # Quote keeps original speaker
                result.append(f"[{speaker}] {quote_part} [/]")
                # Attribution becomes Narrator
                result.append(f"[Narrator] {attrib_part} [/]")
            else:
                # Parts too small, keep original
                result.append(line)
        
        return result
    
    def generate_book_with_character_tags(
    self,
    tokens,
    quotes,
    attributed_quotations,
    entities,
    assignments,
    genders,
    chardata,
    outFolder,
    idd
):
        """Generate a .book.txt per SENTENCE with dominant speaker, plus a plain copy for the UI."""

        # Build canonical/normalized names
        names = {}
        for idx, (start, end, cat, text) in enumerate(entities):
            coref = assignments[idx]
            if coref not in names:
                names[coref] = Counter()
            ner_prop = cat.split("_")[0]
            if ner_prop == "PROP":
                names[coref][text.lower()] += 10
            elif ner_prop == "NOM":
                names[coref][text.lower()] += 1
            else:
                names[coref][text.lower()] += 0.001

        char_names = {}
        normalized_char_names = {}
        for coref, cnt in names.items():
            if cnt:
                canon = cnt.most_common(1)[0][0].title()
                char_names[coref] = canon
                normalized_char_names[coref] = self.normalize_character_name(canon)
            else:
                char_names[coref] = f"Character{coref}"
                normalized_char_names[coref] = f"character{coref}"

        # Ensure Narrator maps cleanly
        char_names["Narrator"] = "Narrator"
        normalized_char_names["Narrator"] = "Narrator"
        char_names["Unknown"] = "Unknown"
        normalized_char_names["Unknown"] = "Unknown"

        # Map token indices inside quotes → speaker_id (BookNLP attribution)
        quote_ranges = {}
        for qidx, (qs, qe) in enumerate(quotes):
            mention_id = attributed_quotations[qidx]
            speaker_id = assignments[mention_id] if mention_id is not None else "Narrator"
            for t_id in range(qs, qe + 1):
                quote_ranges[t_id] = speaker_id

        # Group tokens by sentence
        sentences = {}
        for tok in tokens:
            sid = tok.sentence_id
            sentences.setdefault(sid, []).append(tok)

        # Build tagged lines (per sentence) using dominant-speaker logic
        result_lines = []
        last_speaker_id = None  # carry-forward for monologues

        for sid in sorted(sentences.keys()):
            sent_tokens = sentences[sid]
            sent_text = " ".join(t.text for t in sent_tokens)
            sent_text = self.fix_punctuation_spacing(sent_text).strip()

            # Count quote tokens per speaker in this sentence
            # Count quote tokens per speaker in this sentence
            sp_counts = {}
            quote_tok_total = 0
            for tok in sent_tokens:
                sid_ = quote_ranges.get(tok.token_id)
                if sid_ is not None:
                    quote_tok_total += 1
                    sp_counts[sid_] = sp_counts.get(sid_, 0) + 1

            # Choose speaker
            if quote_tok_total == 0:
                # No quotes → narrator line
                speaker_id = "Narrator"
            elif len(sp_counts) == 1:
                # Exactly one speaker in quoted portion
                speaker_id = next(iter(sp_counts.keys()))
            else:
                # Prefer dominant non-Narrator if it covers >=60% of quote tokens
                top_sid, top_cnt = max(sp_counts.items(), key=lambda kv: kv[1])
                top_ratio = top_cnt / max(1, quote_tok_total)
                non_narr = [sid_ for sid_ in sp_counts if sid_ != "Narrator"]

                if top_sid != "Narrator" and top_ratio >= 0.55:
                    speaker_id = top_sid
                elif len(non_narr) == 1:
                    speaker_id = non_narr[0]
                elif (sent_text.lstrip().startswith(('"', "“", "‘")) and last_speaker_id and last_speaker_id != "Narrator"):
                    # Carry-forward when the sentence opens with a quote (monologue continuation)
                    speaker_id = last_speaker_id
                else:
                    # IMPORTANT: sentence *has quotes* but no clear winner → mark Unknown (NOT Narrator)
                    speaker_id = "Unknown"


            speaker_name = normalized_char_names.get(speaker_id, f"character{speaker_id}")
            result_lines.append(f"[{speaker_name}] {sent_text} [/]")
            if speaker_id != "Narrator":
                last_speaker_id = speaker_id

        # POST-PROCESSING: Split merged dialogue+attribution patterns
        # This fixes cases where SpaCy treats '"Why?" he said.' as one sentence
        result_lines = self._split_dialogue_attribution_merged_sentences(result_lines, normalized_char_names)

        # Write the tagged file
        with open(join(outFolder, f"{idd}.book.txt"), "w", encoding="utf-8") as out:
            out.write("\n".join(result_lines))

        # Also write a plain file for the UI (no [Speaker] … [/])
        def _strip_tags(s: str) -> str:
            s = re.sub(r'^\s*\[[^\]]+\]\s*', '', s or '').strip()
            s = re.sub(r'\s*\[/\]\s*$', '', s).strip()
            return s

        with open(join(outFolder, f"{idd}.book.plain.txt"), "w", encoding="utf-8") as outp:
            outp.write("\n".join(_strip_tags(line) for line in result_lines))

        return result_lines



    def process(self, filename, outFolder, idd):        

        with torch.no_grad():

            start_time = time.time()
            originalTime=start_time

            with open(filename, encoding='utf-8') as file:
                data=file.read()

                if len(data) == 0:
                    print("Input file is empty: %s" % filename)
                    return 

                try:
                    os.makedirs(outFolder)
                except FileExistsError:
                    pass

                    
                tokens=self.tagger.tag(data)
                
                print("--- spacy: %.3f seconds ---" % (time.time() - start_time))
                start_time=time.time()

                if self.doEvent or self.doEntities or self.doSS:

                    entity_vals=self.entityTagger.tag(tokens, doEvent=self.doEvent, doEntities=self.doEntities, doSS=self.doSS)
                    entity_vals["entities"]=sorted(entity_vals["entities"])
                    if self.doSS:
                        supersense_entities=entity_vals["supersense"]
                        with open(join(outFolder, "%s.supersense" % (idd)), "w", encoding="utf-8") as out:
                            out.write("start_token\tend_token\tsupersense_category\ttext\n")
                            for start, end, cat, text in supersense_entities:
                                out.write("%s\t%s\t%s\t%s\n" % (start, end, cat, text))

                    if self.doEvent:
                        events=entity_vals["events"]
                        for token in tokens:
                            if token.token_id in events:
                                token.event="EVENT"

                    with open(join(outFolder, "%s.tokens" % (idd)), "w", encoding="utf-8") as out:
                        out.write("%s\n" % '\t'.join(["paragraph_ID", "sentence_ID", "token_ID_within_sentence", "token_ID_within_document", "word", "lemma", "byte_onset", "byte_offset", "POS_tag", "fine_POS_tag", "dependency_relation", "syntactic_head_ID", "event"]))
                        for token in tokens:
                            out.write("%s\n" % token)

                    print("--- entities: %.3f seconds ---" % (time.time() - start_time))
                    start_time=time.time()

                in_quotes=[]
                quotes=self.quoteTagger.tag(tokens)

                print("--- quotes: %.3f seconds ---" % (time.time() - start_time))
                start_time=time.time()

                if self.doQuoteAttrib:

                    entities = entity_vals["entities"]

                    # Ensure mention→cluster assignments are available BEFORE we use them
                    assignments = (
                        entity_vals.get("assignments")
                        or entity_vals.get("cluster_assignments")
                        or entity_vals.get("mention_to_cluster")
                    )
                    if assignments is None:
                        assignments = [-1] * len(entities)

                    # Run attribution
                    attributed_quotations = self.quote_attrib.tag(quotes, entities, tokens)
                    print("--- attribution: %.3f seconds ---" % (time.time() - start_time))

                    # DEBUG: measure merge impact
                    before_q = len(quotes)
                    before_a = len(attributed_quotations)

                    # Merge adjacent quote spans separated only by tiny punctuation gaps
                    quotes, attributed_quotations = _merge_quote_spans(
                        quotes,
                        attributed_quotations,
                        tokens,
                        max_token_gap=3  # 2–3 is safe; prevents over-splitting at em dashes/commas
                    )

                    # ---- Build zone counts (prefer strong file-based; fallback to in-memory) ----
                    narr_mentions, quote_mentions = {}, {}

                    # Try strong file-based counter once
                    try:
                        # Prefer explicit resolver if available
                        tokens_path = quotes_path = entities_path = None
                        try:
                            tokens_path, quotes_path, entities_path = _resolve_enlp_paths()
                        except Exception:
                            pass

                        if not (tokens_path and quotes_path and entities_path):
                            # fallback: build from ENLP_LAST_DIR/PREFIX
                            outdir = ENLP_LAST_DIR
                            pref   = ENLP_LAST_PREFIX
                            if not outdir or not pref:
                                raise RuntimeError("ENLP_LAST_DIR/PREFIX not set")

                            tokens_path = _pick_existing(
                                os.path.join(outdir, f"{pref}.tokens(edit).txt"),
                                os.path.join(outdir, f"{pref}.tokens.txt"),
                                os.path.join(outdir, f"{pref}.tokens"),
                            )
                            quotes_path = _pick_existing(
                                os.path.join(outdir, f"{pref}.quotes(edit).txt"),
                                os.path.join(outdir, f"{pref}.quotes.txt"),
                                os.path.join(outdir, f"{pref}.quotes"),
                            )
                            entities_path = _pick_existing(
                                os.path.join(outdir, f"{pref}.entities(edit).txt"),
                                os.path.join(outdir, f"{pref}.entities.txt"),
                                os.path.join(outdir, f"{pref}.entities"),
                            )

                        # Run strong counter
                        narr_mentions, quote_mentions = count_mentions_by_zone_strong(
                            entities_path, quotes_path, tokens_path
                        )

                        # Expose to others (optional)
                        try:
                            ENLP_CLUSTER_STATS["narr"]  = {int(k): int(v) for k, v in (narr_mentions or {}).items()}
                            ENLP_CLUSTER_STATS["quote"] = {int(k): int(v) for k, v in (quote_mentions or {}).items()}
                        except Exception:
                            pass

                        try:
                            _set_enlp_zone_counts(narr_mentions, quote_mentions)
                        except Exception:
                            pass

                        log(f"[mentions] zone counts: quote={sum((quote_mentions or {}).values())} narr={sum((narr_mentions or {}).values())}")

                    except Exception as e:
                        # Fallback: in-memory counter using current quotes/entities/assignments
                        log(f"[mentions] strong counter unavailable → falling back: {e}")
                        quote_ranges = _build_quote_token_ranges(quotes)
                        narr_mentions, quote_mentions = _count_mentions_by_zone(entities, assignments, quote_ranges)
                        try:
                            _set_enlp_zone_counts(narr_mentions, quote_mentions)
                        except Exception:
                            pass
                        log(f"[mentions] (fallback) zone counts: quote={sum((quote_mentions or {}).values())} narr={sum((narr_mentions or {}).values())}")

                    # --- Count speaker lines per cluster_id from attribution (int/dict safe) ----
                    speaker_lines = {}
                    for aq in (attributed_quotations or []):
                        cid = None

                        if isinstance(aq, int):
                            # BookNLP-style: aq is the mention index → map to cluster via assignments
                            m_idx = aq
                            if m_idx is not None and 0 <= m_idx < len(assignments):
                                cid = assignments[m_idx]

                        elif isinstance(aq, dict):
                            # Some pipelines return dicts; try common keys
                            cid = (
                                aq.get("speaker_id")
                                or aq.get("speaker")
                                or aq.get("cid")
                                or aq.get("speaker_cluster")
                            )
                            if cid is None:
                                # fallback: derive from mention index if provided
                                m = aq.get("mention") or aq.get("mention_index")
                                if isinstance(m, int) and 0 <= m < len(assignments):
                                    cid = assignments[m]

                        if cid is None:
                            continue
                        try:
                            cid = int(cid)
                        except Exception:
                            continue
                        if cid < 0:
                            continue

                        speaker_lines[cid] = speaker_lines.get(cid, 0) + 1

                    # Log merge result
                    after_q = len(quotes)
                    after_a = len(attributed_quotations)
                    print(f"--- merged quote spans: {before_q}->{after_q} quotes, {before_a}->{after_a} attrib entries ---")

                    # return time.time() - start_time
                    start_time = time.time()


                if self.doEntities:

                    entities = entity_vals["entities"]

                    # --- ensure mention→cluster assignments are available ---
                    assignments = (
                        entity_vals.get("assignments")
                        or entity_vals.get("cluster_assignments")
                        or entity_vals.get("mention_to_cluster")
                    )
                    if assignments is None:
                        assignments = [-1] * len(entities)
        
                    in_quotes=[]

                    for start, end, cat, text in entities:
    
                        if tokens[start].inQuote or tokens[end].inQuote:
                            in_quotes.append(1)
                        else:
                            in_quotes.append(0)


                    # Create entity for first-person narrator, if present
                    refs=self.name_resolver.cluster_narrator(entities, in_quotes, tokens)
                
                    # Cluster non-PER PROP mentions that are identical
                    refs=self.name_resolver.cluster_identical_propers(entities, refs)

                    # Cluster mentions of named people
                    refs=self.name_resolver.cluster_only_nouns(entities, refs, tokens)

                    print("--- name coref: %.3f seconds ---" % (time.time() - start_time))

                    start_time=time.time()

                    # Infer referential gender from he/she/they mentions around characters
                    
                    genderEM=GenderEM(tokens=tokens, entities=entities, refs=refs, genders=self.gender_cats, hyperparameterFile=self.gender_hyperparameterFile)
                    genders=genderEM.tag(entities, tokens, refs)
                
                assignments=None
                if self.doEntities:
                    assignments=copy.deepcopy(refs)

                if self.doCoref:
                    torch.cuda.empty_cache()
                    assignments=self.litbank_coref.tag(tokens, entities, refs, genders, attributed_quotations, quotes)

                    print("--- coref: %.3f seconds ---" % (time.time() - start_time))
                    start_time=time.time()

                    ent_names={}
                    for a, e in zip(assignments, entities):
                        if a not in ent_names:
                            ent_names[a]=Counter()
                        ent_names[a][e[3]]+=1
                
                    # Update gender estimates from coref data
                    genders=genderEM.update_gender_from_coref(genders, entities, assignments)

                    chardata=self.get_syntax(tokens, entities, assignments, genders)
                    with open(join(outFolder, "%s.book" % (idd)), "w", encoding="utf-8") as out:
                        json.dump(chardata, out)

                if self.doEntities:
                    # Write entities and coref            
                    with open(join(outFolder, "%s.entities" % (idd)), "w", encoding="utf-8") as out:
                        out.write("COREF\tstart_token\tend_token\tprop\tcat\ttext\n")
                        for idx, assignment in enumerate(assignments):
                            start, end, cat, text=entities[idx]
                            ner_prop=cat.split("_")[0]
                            ner_type=cat.split("_")[1]
                            out.write("%s\t%s\t%s\t%s\t%s\t%s\n" % (assignment, start, end, ner_prop, ner_type, text))


                if self.doQuoteAttrib:
                    with open(join(outFolder, "%s.quotes" % (idd)), "w", encoding="utf-8") as out:
                        out.write('\t'.join(["quote_start", "quote_end", "mention_start", "mention_end", "mention_phrase", "char_id", "quote"]) + "\n")

                        for idx, line in enumerate(attributed_quotations):
                            q_start, q_end=quotes[idx]
                            mention=attributed_quotations[idx]
                            if mention is not None:
                                entity=entities[mention]
                                speaker_id=assignments[mention]
                                e_start=entity[0]
                                e_end=entity[1]
                                cat=entity[3]
                                speak=speaker_id
                            else:
                                e_start=None
                                e_end=None
                                cat=None
                                speak=None
                            quote=[tok.text for tok in tokens[q_start:q_end+1]]
                            out.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (q_start, q_end, e_start, e_end, cat, speak, ' '.join(quote)))
                    
                        out.close()

                if self.doQuoteAttrib and self.doCoref:

                    # get canonical name for character
                    names={}
                    for idx, (start, end, cat, text) in enumerate(entities):
                        coref=assignments[idx]
                        if coref not in names:
                            names[coref]=Counter()
                        ner_prop=cat.split("_")[0]
                        ner_type=cat.split("_")[1]
                        if ner_prop == "PROP":
                            names[coref][text.lower()]+=10
                        elif ner_prop == "NOM":
                            names[coref][text.lower()]+=1
                        else:
                            names[coref][text.lower()]+=.001

                    # Generate character info JSON
                    print("--- generating character JSON: start ---")
                    char_start_time = time.time()
                    self.generate_character_json(entities, assignments, genders, chardata, outFolder, idd)
                    print("--- character JSON: %.3f seconds ---" % (time.time() - char_start_time))

                    # Generate simplified character info JSON
                    print("--- generating simplified character JSON: start ---")
                    simple_char_start_time = time.time()
                    self.write_characters_simple(entities, assignments, outFolder, idd)
                    print("--- simplified character JSON: %.3f seconds ---" % (time.time() - simple_char_start_time))

                    # Generate book with character tags
                    print("--- generating tagged book: start ---")
                    book_start_time = time.time()
                    self.generate_book_with_character_tags(tokens, quotes, attributed_quotations, 
                                                          entities, assignments, genders, chardata, 
                                                          outFolder, idd)
                    print("--- tagged book: %.3f seconds ---" % (time.time() - book_start_time))

                    with open(join(outFolder, "%s.book.html" % (idd)), "w", encoding="utf-8") as out:
                        out.write("<html>")
                        out.write("""<head>
          <meta charset="UTF-8">
        </head>""")
                        out.write("<h2>Named characters</h2>\n")
                        for character in chardata["characters"]:
                            char_id=character["id"]

                            proper_names=character["mentions"]["proper"]
                            if len(proper_names) > 0 or char_id == 0: # 0=narrator
                                proper_name_list="/".join(["%s (%s)" % (name["n"], name["c"]) for name in proper_names])

                                common_names=character["mentions"]["common"]
                                common_name_list="/".join(["%s (%s)" % (name["n"], name["c"]) for name in common_names])

                                char_count=character["count"]

                                if char_id == 0:
                                    if len(proper_name_list) == 0:
                                        proper_name_list="[NARRATOR]"
                                    else:
                                        proper_name_list+="/[NARRATOR]"
                                out.write("%s %s %s <br />\n" % (char_count, proper_name_list, common_name_list))

                
                        out.write("<p>\n")

                        out.write("<h2>Major entities (proper, common)</h2>")

                        major_places={}
                        for prop in ["PROP", "NOM"]:
                            major_places[prop]={}
                            for cat in ["FAC", "GPE", "LOC", "PER", "ORG", "VEH"]:
                                major_places[prop][cat]={}

                        for idx, (start, end, cat, text) in enumerate(entities):
                            coref=assignments[idx]
            
                            ner_prop=cat.split("_")[0]
                            ner_type=cat.split("_")[1]
                            if ner_prop != "PRON":
                                if coref not in major_places[ner_prop][ner_type]:
                                    major_places[ner_prop][ner_type][coref]=Counter()
                                major_places[ner_prop][ner_type][coref][text]+=1

                        max_entities_to_display=10
                        for cat in ["FAC", "GPE", "LOC", "PER", "ORG", "VEH"]:
                            out.write("<h3>%s</h3>" % cat)
                            for prop in ["PROP", "NOM"]:
                                freqs={}
                                for coref in major_places[prop][cat]:
                                    freqs[coref]=sum(major_places[prop][cat][coref].values())

                                sorted_freqs=sorted(freqs.items(), key=lambda x: x[1], reverse=True)
                                for k,v in sorted_freqs[:max_entities_to_display]:
                                    ent_names=[]
                                    for name, count in major_places[prop][cat][k].most_common():
                                        ent_names.append("%s" % (name))
                                    out.write("%s %s <br />"% (v, '/'.join(ent_names)))
                                out.write("<p>")



                        out.write("<h2>Text</h2>\n")
                        

                        beforeToks=[""]*len(tokens)
                        afterToks=[""]*len(tokens)

                        lastP=None

                        for idx, (start, end, cat, text) in enumerate(entities):
                            coref=assignments[idx]
                            name=names[coref].most_common(1)[0][0]
                            beforeToks[start]+="<font color=\"#D0D0D0\">[</font>"
                            afterToks[end]="<font color=\"#D0D0D0\">]</font><font color=\"#FF00FF\"><sub>%s-%s</sub></font>" % (coref, name) + afterToks[end]

                        for idx, (start, end) in enumerate(quotes):
                            mention_id=attributed_quotations[idx]
                            if mention_id is not None:
                                speaker_id=assignments[mention_id]
                                name=names[speaker_id].most_common(1)[0][0]
                            else:
                                speaker_id="None"
                                name="None"
                            beforeToks[start]+="<font color=\"#666699\">"
                            afterToks[end]+="</font><sub>[%s-%s]</sub>" % (speaker_id, name)

                        for idx in range(len(tokens)):
                            if tokens[idx].paragraph_id != lastP:
                                out.write("<p />")
                            out.write("%s%s%s " % (beforeToks[idx], escape(tokens[idx].text), afterToks[idx])) 
                            lastP=tokens[idx].paragraph_id    

                        
                        out.write("</html>")

                print("--- TOTAL (excl. startup): %.3f seconds ---, %s words" % (time.time() - originalTime, len(tokens)))
                return time.time() - originalTime