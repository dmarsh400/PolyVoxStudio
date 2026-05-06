"""
Text preprocessor for TTS quality enhancement.
Cleans and normalizes text before sending to TTS engine.
"""
import re


class TextPreprocessor:
    """Preprocesses text for better TTS quality."""
    
    def __init__(self):
        """Initialize the text preprocessor."""
        pass
    
    def prepare_for_tts(self, text):
        """
        Prepare text for TTS synthesis.
        
        Args:
            text: Raw text to process
            
        Returns:
            Cleaned text ready for TTS
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Remove multiple punctuation (e.g., "!!!" -> "!")
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        
        # Ensure proper spacing after punctuation
        text = re.sub(r'([.!?,:;])([A-Za-z])', r'\1 \2', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Limit length (XTTS works best with shorter segments)
        # If text is very long, just use first part
        # (In production, you'd want to split this properly)
        max_length = 500
        if len(text) > max_length:
            # Find last sentence boundary before max_length
            truncated = text[:max_length]
            last_period = max(
                truncated.rfind('.'),
                truncated.rfind('!'),
                truncated.rfind('?')
            )
            if last_period > 0:
                text = text[:last_period + 1]
            else:
                text = truncated
        
        return text
