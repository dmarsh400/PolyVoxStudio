#!/usr/bin/env python3
import json
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

# Expect input JSON with a list of quotes (BookNLP-like). We'll normalize into a clean schema.

@dataclass
class CleanQuote:
    idx: int
    text: str
    speaker: str
    method: str = "booknlp"
    score: float = 1.0

SPEECH_VERBS = r"(said|asked|replied|shouted|whispered|cried|muttered|yelled|called|told|answered)"
ATTRIB_REGEX = [
    (re.compile(rf'\b{SPEECH_VERBS}\s+([A-Z][a-zA-Z\-\']+)'), "postverb"),
    (re.compile(rf'([A-Z][a-zA-Z\-\']+)\s+{SPEECH_VERBS}\b'), "preverb"),
]

def normalize_name(name: str) -> str:
    if not name:
        return "UNKNOWN"
    return name.strip().title()

def guess_from_context(text_block: str) -> str:
    for pattern, _verb in ATTRIB_REGEX:
        m = pattern.search(text_block)
        if m:
            return normalize_name(m.group(1))
    return "UNKNOWN"

def clean_quotes(raw: List[Dict[str, Any]]) -> List[CleanQuote]:
    cleaned: List[CleanQuote] = []
    for i, q in enumerate(raw):
        text = q.get("text") or q.get("quote") or ""
        speaker = q.get("speaker") or guess_from_context(q.get("context", text))
        cleaned.append(CleanQuote(idx=i, text=text, speaker=normalize_name(speaker)))
    return cleaned

def main(in_path: str, out_path: str):
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "quotes" in data:
        quotes = data["quotes"]
    elif isinstance(data, list):
        quotes = data
    else:
        raise ValueError("Unrecognized input JSON structure. Expect a list or an object with 'quotes'.")

    cleaned = clean_quotes(quotes)
    out = [asdict(c) for c in cleaned]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(out)} cleaned quotes to {out_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python booknlp_cleaner.py <input.json> <output.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
