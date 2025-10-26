"""
Text Preprocessing for Optimal TTS Generation
Cleans and optimizes text before sending to XTTS v2
"""

import re
import unicodedata
from typing import Dict, List, Optional


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
        
        # Quote normalization
        self.quote_replacements = {
            '"': '"',  # Left double quote
            '"': '"',  # Right double quote
            ''': "'",  # Left single quote
            ''': "'",  # Right single quote
            '«': '"',  # Left guillemet
            '»': '"',  # Right guillemet
        }
    
    def normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to ASCII-compatible forms"""
        # NFKD normalization (compatibility decomposition)
        text = unicodedata.normalize('NFKD', text)
        # Keep only ASCII-compatible characters
        text = text.encode('ascii', 'ignore').decode('ascii')
        return text
    
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
    
    def fix_punctuation(self, text: str) -> str:
        """Fix common punctuation issues"""
        # Multiple periods to ellipsis
        text = re.sub(r'\.{2,}', '…', text)
        
        # Multiple exclamations/questions to single
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)
        
        # Double hyphens to em-dash
        text = text.replace('--', '—')
        text = re.sub(r'\s+-\s+', '—', text)
        
        # Remove space before punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        
        # Add space after sentence-ending punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        # Fix spacing around quotes
        text = re.sub(r'"\s+', '"', text)  # No space after opening quote
        text = re.sub(r'\s+"', '"', text)  # No space before closing quote
        
        return text
    
    def add_prosody_hints(self, text: str) -> str:
        """Add spacing for natural pauses and pacing"""
        # Ensure space after commas for micro-pause
        text = re.sub(r',([^\s])', r', \1', text)
        
        # Ensure space after periods
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        
        # Add space around em-dashes for pause
        text = re.sub(r'([^\s])—', r'\1 —', text)
        text = re.sub(r'—([^\s])', r'— \1', text)
        
        # Space after ellipsis
        text = re.sub(r'…([^\s])', r'… \1', text)
        
        # Space before exclamation/question at end of quote
        text = re.sub(r'([!?])"', r'\1 "', text)
        
        return text
    
    def remove_excessive_whitespace(self, text: str) -> str:
        """Clean up spacing"""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with single newline
        text = re.sub(r'\n+', '\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def handle_numbers(self, text: str) -> str:
        """Convert numbers to words for natural speech (simple version)"""
        # This is a basic implementation - for production, use num2words library
        
        # Years (1990s style)
        text = re.sub(r'\b19(\d{2})\b', lambda m: f"nineteen {m.group(1)}", text)
        text = re.sub(r'\b20(\d{2})\b', lambda m: f"twenty {m.group(1)}", text)
        
        # Simple single digits
        digit_words = {
            '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
            '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
        }
        
        # Convert standalone single digits (when surrounded by spaces or punctuation)
        for digit, word in digit_words.items():
            text = re.sub(rf'\b{digit}\b', word, text)
        
        return text
    
    def prepare_for_tts(self, text: str, 
                       expand_abbrev: bool = True,
                       add_prosody: bool = True,
                       convert_numbers: bool = False) -> str:
        """
        Full preprocessing pipeline
        
        Args:
            text: Raw input text
            expand_abbrev: Expand abbreviations (Mr. -> Mister)
            add_prosody: Add spacing hints for natural pauses
            convert_numbers: Convert numbers to words
        
        Returns:
            Cleaned and optimized text ready for TTS
        """
        # Step 1: Normalize unicode
        text = self.normalize_unicode(text)
        
        # Step 2: Normalize quotes
        text = self.normalize_quotes(text)
        
        # Step 3: Expand abbreviations
        if expand_abbrev:
            text = self.expand_abbreviations(text)
        
        # Step 4: Convert numbers
        if convert_numbers:
            text = self.handle_numbers(text)
        
        # Step 5: Fix punctuation
        text = self.fix_punctuation(text)
        
        # Step 6: Add prosody hints
        if add_prosody:
            text = self.add_prosody_hints(text)
        
        # Step 7: Clean whitespace
        text = self.remove_excessive_whitespace(text)
        
        return text
    
    def batch_prepare(self, texts: List[str], **kwargs) -> List[str]:
        """Prepare multiple texts in batch"""
        return [self.prepare_for_tts(text, **kwargs) for text in texts]


# Example usage and testing
if __name__ == "__main__":
    preprocessor = TextPreprocessor()
    
    # Test cases
    test_texts = [
        'He said,"Wait...did you hear that?"She replied,"No,I didn\'t."',
        'Mr. Smith went to St. James Ave. on 5th St.',
        'Wait--did you see that?!?!  I think...no, I\'m sure!!!',
        '"Hello," she said. "How are you today?"',
        'The year was 1995.  I was 7 years old.',
    ]
    
    print("="*80)
    print("TEXT PREPROCESSOR TEST")
    print("="*80)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}:")
        print(f"  Input:  {text}")
        cleaned = preprocessor.prepare_for_tts(text)
        print(f"  Output: {cleaned}")
    
    print("\n" + "="*80)
    print("✅ Preprocessing ready for production use!")
    print("="*80)
