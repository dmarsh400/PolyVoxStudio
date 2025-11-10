"""
Text Preprocessing for Optimal TTS Generation
Cleans and optimizes text before sending to XTTS v2
"""

import re
import unicodedata
from typing import Dict, List, Optional


# --- Helpers (anchor: TEXT_HELPERS) ---
_TERMINAL_PUNCT_RX = re.compile(r"[\.!?]\s*$")


def safe_truncate_at_sentence(text: str, max_chars: int) -> str:
    """Truncate text while preferring natural sentence boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return text

    cut = text[:max_chars].rstrip()

    if _TERMINAL_PUNCT_RX.search(cut):
        return cut

    last_term = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    if last_term >= 0 and last_term >= len(cut) - 120:
        return cut[: last_term + 1].rstrip()

    last_space = cut.rfind(" ")
    if last_space > 0:
        return (cut[:last_space].rstrip()) + "..."
    return cut + "..."


def normalize_unicode_text(s: str, ascii_only: bool = True) -> str:
    """Normalize text; optionally preserve non-ASCII graphemes."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("\u00A0", " ")

    if ascii_only:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = s.encode("ascii", errors="ignore").decode("ascii", errors="ignore")

    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


class TextPreprocessor:
    """Optimize text for natural TTS generation"""

    def __init__(self):
        # Common abbreviation expansions for natural speech
        self.abbreviations = {
            r'\bMr\.': 'Mister',
            r'\bMrs\.': 'Missus',
            r'\bMs\.': 'Miss',
            r'\bDr\.': 'Doctor',
            r'\bProf\.': 'Professor',
            r'\bSt\.': 'Saint',
            r'\bAve\.': 'Avenue',
            r'\bRd\.': 'Road',
            r'\bBlvd\.': 'Boulevard',
            r'\bDept\.': 'Department',
            r'\bCo\.': 'Company',
            r'\bInc\.': 'Incorporated',
            r'\bLtd\.': 'Limited',
            r'\betc\.': 'et cetera',
            r'\bi\.e\.': 'that is',
            r'\be\.g\.': 'for example',
        }

        # (1) Quote normalization — map curly/guillemets to ASCII
        # Replaces the duplicate/invalid entries you had before. :contentReference[oaicite:1]{index=1}
        self.quote_replacements = {
            '“': '"',  # Left double
            '”': '"',  # Right double
            '‘': "'",  # Left single
            '’': "'",  # Right single / apostrophe
            '«': '"',  # Left guillemet
            '»': '"',  # Right guillemet
        }

    def infer_emotion(self, text: str) -> str:
        """Infer emotion from text content using heuristics."""
        text_lower = text.lower()
        
        # Punctuation-based heuristics
        if '!!!' in text or (text.count('!') > 2 and len(text.split()) < 10):
            return 'excited'
        if '?' in text and '...' in text:
            return 'hesitant'
        if '...' in text and len(text.split()) > 20:
            return 'calm'  # Long pauses for reflection
        
        # Keyword-based detection
        emotion_keywords = {
            'sob': ['sad', 'cry', 'weep', 'grief', 'sorrow', 'tears'],
            'angry': ['angry', 'furious', 'rage', 'hate', 'fury', 'snarl'],
            'fearful': ['fear', 'terrified', 'scared', 'tremble', 'afraid', 'panic'],
            'surprised': ['surprise', 'gasp', 'shock', 'amaze', 'astonish'],
            'excited': ['excited', 'thrilled', 'joy', 'cheer', 'delight'],
            'laugh': ['laugh', 'giggle', 'chuckle', 'funny']
        }
        
        for emotion, words in emotion_keywords.items():
            if any(word in text_lower for word in words):
                return emotion
        
        return 'none'

    def normalize_unicode(self, text: str, ascii_only: bool = True) -> str:
        """Normalize unicode characters with optional accent preservation."""
        return normalize_unicode_text(text, ascii_only=ascii_only)

    def normalize_quotes(self, text: str) -> str:
        """Normalize various quote characters to standard forms"""
        for old, new in self.quote_replacements.items():
            text = text.replace(old, new)
        return text

    def expand_abbreviations(self, text: str) -> str:
        """Expand abbreviations for natural speech"""
        for pattern, replacement in self.abbreviations.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    # (2) De-hyphenate compounds to reduce TTS stumbles on intra-word hyphens
    def dehyphenate_compounds(self, text: str, mode: str = "space") -> str:
        """
        Replace intra-word hyphens (letter-letter) to reduce TTS pauses.
        mode: "space" -> 'ex-ranger' -> 'ex ranger'  (recommended)
              "join"  -> 'ex-ranger' -> 'exranger'
        Only touches A–Z pairs; leaves A-10, -5 intact.
        """
        pattern = r'(?<=[A-Za-z])-(?=[A-Za-z])'
        if mode == "join":
            return re.sub(pattern, '', text)
        return re.sub(pattern, ' ', text)

    def fix_punctuation(self, text: str) -> str:
        """Fix common punctuation issues"""
        # (3A) Multiple periods -> three dots (plain '...'; engines often over-pause on U+2026)
        text = re.sub(r'\.{2,}', '...', text)

        # Multiple exclamations/questions to single
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)

        # Double hyphens / spaced hyphen to em-dash
        text = text.replace('--', '—')
        text = re.sub(r'\s+-\s+', '—', text)

        # Remove space before punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)

        # Add space after sentence-ending punctuation if followed by capital
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

        # Fix spacing around straight quotes
        text = re.sub(r'"\s+', '"', text)  # No space after opening quote
        text = re.sub(r'\s+"', '"', text)  # No space before closing quote

        return text

    def add_prosody_hints(self, text: str) -> str:
        """Add spacing for natural pauses and pacing"""
        # Ensure space after commas for micro-pause
        text = re.sub(r',([^\s])', r', \1', text)

        # Ensure space after periods (if any missed)
        text = re.sub(r'\.([A-Z])', r'. \1', text)

        # (3B) Make em-dash act like a comma-level pause (tight, not huge)
        text = re.sub(r'\s*—\s*', ' — ', text)

        # Space after three dots
        text = re.sub(r'\.\.\.([^\s])', r'... \1', text)

        # Space before !/? at end of quote
        text = re.sub(r'([!?])"', r'\1 "', text)

        return text

    def remove_excessive_whitespace(self, text: str) -> str:
        """Clean up spacing"""
        text = re.sub(r' +', ' ', text)      # collapse spaces
        text = re.sub(r'\n+', '\n', text)    # collapse newlines
        text = text.strip()
        return text

    def handle_numbers(self, text: str) -> str:
        """Convert numbers to words for natural speech (simple version)"""
        # NOTE: Your original basic numbers logic preserved. :contentReference[oaicite:2]{index=2}
        # Years (1990s style)
        text = re.sub(r'\b19(\d{2})\b', lambda m: f"nineteen {m.group(1)}", text)
        text = re.sub(r'\b20(\d{2})\b', lambda m: f"twenty {m.group(1)}", text)

        # Simple single digits -> words (standalone only)
        digit_words = {
            '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
            '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
        }
        for digit, word in digit_words.items():
            text = re.sub(rf'\b{digit}\b', word, text)
        return text

    def handle_currency(self, text: str) -> str:
        """Convert currency amounts to natural speech format"""
        # Handle dollar amounts like $6000 -> "six thousand dollars"
        def convert_dollar_amount(match):
            amount = match.group(1)
            # Remove commas and convert to words
            amount_clean = amount.replace(',', '')
            try:
                # Convert number to words
                num_words = self._number_to_words(int(amount_clean))
                return f"{num_words} dollars"
            except ValueError:
                # If conversion fails, return original
                return match.group(0)

        # Match $ followed by number (with optional commas)
        text = re.sub(r'\$([0-9,]+)', convert_dollar_amount, text)
        return text

    def handle_ammo_calibers(self, text: str) -> str:
        """Convert ammo calibers to natural speech format"""
        # Common ammo caliber mappings
        caliber_mappings = {
            # Metric calibers
            r'\b9mm\b': 'nine millimeter',
            r'\b10mm\b': 'ten millimeter',
            r'\b11mm\b': 'eleven millimeter',
            r'\b12mm\b': 'twelve millimeter',
            r'\b13mm\b': 'thirteen millimeter',
            r'\b14mm\b': 'fourteen millimeter',
            r'\b15mm\b': 'fifteen millimeter',
            r'\b16mm\b': 'sixteen millimeter',
            r'\b17mm\b': 'seventeen millimeter',
            r'\b18mm\b': 'eighteen millimeter',
            r'\b19mm\b': 'nineteen millimeter',
            r'\b20mm\b': 'twenty millimeter',
            r'\b21mm\b': 'twenty one millimeter',
            r'\b22mm\b': 'twenty two millimeter',

            # Decimal calibers (spoken as individual digits)
            r'\.22\b': 'twenty two',
            r'\.223\b': 'two two three',
            r'\.224\b': 'two two four',
            r'\.243\b': 'two forty three',
            r'\.270\b': 'two seventy',
            r'\.280\b': 'two eighty',
            r'\.308\b': 'three oh eight',
            r'\.30-06\b': 'thirty oh six',
            r'\.30-30\b': 'thirty thirty',
            r'\.300\b': 'three hundred',
            r'\.303\b': 'three oh three',
            r'\.308\b': 'three oh eight',
            r'\.310\b': 'three ten',
            r'\.32\b': 'three two',
            r'\.327\b': 'three two seven',
            r'\.338\b': 'three three eight',
            r'\.340\b': 'three forty',
            r'\.35\b': 'three five',
            r'\.350\b': 'three fifty',
            r'\.357\b': 'three five seven',
            r'\.360\b': 'three sixty',
            r'\.375\b': 'three seven five',
            r'\.38\b': 'three eight',
            r'\.380\b': 'three eighty',
            r'\.40\b': 'four oh',
            r'\.405\b': 'four oh five',
            r'\.408\b': 'four oh eight',
            r'\.410\b': 'four ten',
            r'\.416\b': 'four sixteen',
            r'\.44\b': 'four four',
            r'\.444\b': 'four forty four',
            r'\.45\b': 'four five',
            r'\.450\b': 'four fifty',
            r'\.454\b': 'four fifty four',
            r'\.460\b': 'four sixty',
            r'\.480\b': 'four eighty',
            r'\.50\b': 'fifty',
            r'\.500\b': 'five hundred',
            r'\.505\b': 'five oh five',

            # Additional calibers
            r'\b45-70\b': 'forty five seventy',

            # Shotgun gauges
            r'\b12 gauge\b': 'twelve gauge',
            r'\b16 gauge\b': 'sixteen gauge',
            r'\b20 gauge\b': 'twenty gauge',
            r'\b28 gauge\b': 'twenty eight gauge',
            r'\.410 gauge\b': 'four ten gauge',
        }

        # Apply mappings
        for pattern, replacement in caliber_mappings.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _number_to_words(self, num: int) -> str:
        """Convert number to words (basic implementation)"""
        if num == 0:
            return 'zero'

        # Handle negative numbers
        if num < 0:
            return 'negative ' + self._number_to_words(-num)

        # Define word mappings
        ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
        teens = ['', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
                'seventeen', 'eighteen', 'nineteen']
        tens = ['', 'ten', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        thousands = ['', 'thousand', 'million', 'billion']

        def _convert_hundreds(n):
            if n == 0:
                return ''
            elif n < 10:
                return ones[n]
            elif n < 20:
                return teens[n-10]
            elif n < 100:
                return tens[n//10] + ('' if n%10 == 0 else ' ' + ones[n%10])
            else:
                return ones[n//100] + ' hundred' + ('' if n%100 == 0 else ' ' + _convert_hundreds(n%100))

        if num == 0:
            return 'zero'

        result = ''
        i = 0
        while num > 0:
            if num % 1000 != 0:
                result = _convert_hundreds(num % 1000) + ' ' + thousands[i] + ' ' + result
            num //= 1000
            i += 1

        return result.strip()

    # (5) OPTIONAL: make “FBI” -> “F. B. I.” for clearer letter-by-letter reading
    def space_acronyms(self, text: str) -> str:
        return re.sub(r'\b([A-Z]{2,})\b', lambda m: '. '.join(m.group(1)) + '.', text)

    # (5) OPTIONAL: replace URLs/emails with placeholders (avoid letter soup)
    def shield_urls_emails(self, text: str) -> str:
        url_pat = r'(https?://\S+|www\.\S+)'
        email_pat = r'[\w\.-]+@[\w\.-]+\.\w+'
        text = re.sub(url_pat, '[link]', text)
        text = re.sub(email_pat, '[email]', text)
        return text
    
    # --- Dialogue/emotion segmentation ---------------------------------------
    # Detects patterns like:  "Get down!" whispered Chris.  |  “Leave!” yelled John.
    # Returns a list of segments: [{"text": "...", "style": "whisper"}, ...]
    def segment_by_emotion(self, raw_text: str):
        """
        Extract dialogue spans and map trailing attributions to style labels.
        Supports emotion tags like [yell]text[/yell] for manual override.
        Styles: whisper, yell, shout, scream, murmur, hiss, growl, laugh, sob, none
        """
        # Check for emotion tags in the entire text
        tag_pattern = r'^\[(\w+)\](.*)\[/\1\]$'
        match = re.match(tag_pattern, raw_text.strip())
        if match:
            style = match.group(1).lower()
            text = match.group(2)
            return [{"text": text, "style": style}]
        
        # Find quoted dialogue first
        # Supports "..." and '...' styles; keeps order through the text
        spans = []
        for m in re.finditer(r'(["“])(.*?)(["”])', raw_text, flags=re.DOTALL):
            spans.append({"span": m.span(), "quote": m.group(2)})
        if not spans:
            # No quotes → treat whole text as neutral narration
            return [{"text": raw_text, "style": "none"}]

        # Build segments with styles
        segments = []
        cursor = 0
        verbs = {
            "whisper": r"(whisper(?:ed|s|ing)?)",
            "yell": r"(yell(?:ed|s|ing)?|shout(?:ed|s|ing)?)",
            "scream": r"(scream(?:ed|s|ing)?)",
            "murmur": r"(murmur(?:ed|s|ing)?|mutter(?:ed|s|ing)?)",
            "hiss": r"(hiss(?:ed|es|ing)?)",
            "growl": r"(growl(?:ed|s|ing)?)",
            "laugh": r"(laugh(?:ed|s|ing)?|chuckle(?:d|s|ing)?)",
            "sob": r"(sob(?:bed|s|bing)?|cry(?:ied|ing|ies)?)",
            "excited": r"(exclaim(?:ed|s|ing)?|cheer(?:ed|s|ing)?|enthusiastically)",
            "hesitant": r"(hesitat(?:ed|e|ing)|stammer(?:ed|s|ing)?|uncertainly)",
            "calm": r"(calmly|softly|quietly)",
            "surprised": r"(gasp(?:ed|s|ing)?|surprisedly)",
            "angry": r"(snarl(?:ed|s|ing)?|furiou?sly|angrily)",
            "fearful": r"(trembl(?:ed|e|ing)|fearfully|terrifiedly)"
        }
        # Combined regex to sniff attribution verbs *after* the quote, e.g.
        #   "Hello," she whispered / "Hello." whispered Chris
        tail_pat = re.compile(
            r'^\s*(?:,|\.)?\s*(?:the\s+)?(?:\w+\s+){0,3}(' + '|'.join(verbs.values()) + r')\b',
            flags=re.IGNORECASE
        )

        for span in spans:
            start, end = span["span"]
            # Add any narrator text between quotes as neutral (keeps flow)
            if start > cursor:
                narrator = raw_text[cursor:start]
                if narrator.strip():
                    segments.append({"text": narrator, "style": self.infer_emotion(narrator.strip())})
            # The quoted speech
            quoted = span["quote"]

            # Check for emotion tags in the quoted text
            tag_match = re.match(tag_pattern, quoted.strip())
            if tag_match:
                style = tag_match.group(1).lower()
                quoted = tag_match.group(2)
            else:
                lookahead = raw_text[end:end+60]
                style = "none"
                m = tail_pat.search(lookahead)
                if m:
                    v = m.group(1).lower()
                    if "whisper" in v:
                        style = "whisper"
                    elif ("yell" in v) or ("shout" in v):
                        style = "yell"
                    elif "scream" in v:
                        style = "scream"
                    elif ("murmur" in v) or ("mutter" in v):
                        style = "murmur"
                    elif "hiss" in v:
                        style = "hiss"
                    elif "growl" in v:
                        style = "growl"
                    elif ("laugh" in v) or ("chuckle" in v):
                        style = "laugh"
                    elif ("sob" in v) or ("cry" in v):
                        style = "sob"
                    elif "excited" in v or "cheer" in v:
                        style = "excited"
                    elif "hesitant" in v or "stammer" in v:
                        style = "hesitant"
                    elif "calm" in v:
                        style = "calm"
                    elif "surprised" in v or "gasp" in v:
                        style = "surprised"
                    elif "angry" in v or "snarl" in v:
                        style = "angry"
                    elif "fearful" in v or "trembl" in v:
                        style = "fearful"

                if style == "none":
                    style = self.infer_emotion(quoted)

            segments.append({"text": quoted, "style": style})
            cursor = end
        # Trailing narrator text
        if cursor < len(raw_text):
            tail = raw_text[cursor:]
            if tail.strip():
                segments.append({"text": tail, "style": self.infer_emotion(tail.strip())})
        return segments

    def prepare_for_tts(
        self,
        text: str,
        ascii_only: bool = True,
        expand_abbrev: bool = True,
        add_prosody: bool = True,
        convert_numbers: bool = False,
        handle_currency: bool = True,
        handle_calibers: bool = True,
        dehyphen_mode: str = "space",          # "space" | "join" | "off"
        apply_acronyms: bool = False,          # (5) optional
        shield_links: bool = False             # (5) optional
    ) -> str:
        """
        Full preprocessing pipeline

        Args:
            text: Raw input text
            expand_abbrev: Expand abbreviations (Mr. -> Mister)
            add_prosody: Add spacing hints for natural pauses
            convert_numbers: Convert numbers to words
            handle_currency: Convert currency amounts to natural speech
            handle_calibers: Convert ammo calibers to natural speech
            dehyphen_mode: how to treat intra-word hyphens ("space", "join", "off")
            apply_acronyms: optional pass to spell out acronyms
            shield_links: optional pass to replace URLs/emails

        Returns:
            Cleaned and optimized text ready for TTS
        """
        # Step 1: Normalize quotes first so curly apostrophes survive ASCII cleanup
        text = self.normalize_quotes(text)

        # Step 2: Normalize unicode
        text = self.normalize_unicode(text, ascii_only=ascii_only)

        # Step 2.5: Remove spaces around hyphens in compound words (e.g., "wool - lined" → "wool lined")
        text = re.sub(r'\s+-\s+', ' ', text)

        # (4) Step 2.5: De-hyphenate compounds to reduce stumbles (ex-ranger -> ex ranger)
        if dehyphen_mode in ("space", "join"):
            text = self.dehyphenate_compounds(text, mode=dehyphen_mode)

        # Step 3: Handle currency (before abbreviations to avoid conflicts)
        if handle_currency:
            text = self.handle_currency(text)

        # Step 4: Handle ammo calibers
        if handle_calibers:
            text = self.handle_ammo_calibers(text)

        # Step 5: Expand abbreviations
        if expand_abbrev:
            text = self.expand_abbreviations(text)

        # Step 6: Convert numbers (optional)
        if convert_numbers:
            text = self.handle_numbers(text)

        # (7) Optional passes (disabled by default)
        if shield_links:
            text = self.shield_urls_emails(text)
        if apply_acronyms:
            text = self.space_acronyms(text)

        # Step 7: Fix punctuation
        text = self.fix_punctuation(text)

        # Step 8: Add prosody hints
        if add_prosody:
            text = self.add_prosody_hints(text)

        # Step 9: Clean whitespace
        text = self.remove_excessive_whitespace(text)

        # Step 10: Limit length (XTTS works best with shorter segments)
        text = safe_truncate_at_sentence(text, max_chars=500)

        return text

    def batch_prepare(self, texts: List[str], **kwargs) -> List[str]:
        """Prepare multiple texts in batch"""
        return [self.prepare_for_tts(text, **kwargs) for text in texts]


# Example usage and testing
if __name__ == "__main__":
    preprocessor = TextPreprocessor()

    # Quick sanity checks
    tests = [
        "He was an ex-ranger—back in 2005...",
        'He said,"Wait...did you hear that?"She replied,"No,I didn\'t."',
        'Mr. Smith went to St. James Ave. on 5th St.',
        'Wait--did you see that?!?!  I think...no, I\'m sure!!!',
        'Email me at dev@example.com or visit https://site.test/docs.',
        # Currency tests
        "The car costs $6000 and the house costs $250,000.",
        "He paid $1500 for the gun.",
        # Caliber tests
        "He used a 9mm pistol and .308 rifle.",
        "The .380 ACP is a common caliber.",
        "She shot the .22 target with her .30-06.",
        "The .357 Magnum is powerful.",
        "He loaded .45 ACP rounds into his pistol.",
    ]
    for i, t in enumerate(tests, 1):
        print(f"\nTest {i}\nIn : {t}")
        print("Out:", preprocessor.prepare_for_tts(t))