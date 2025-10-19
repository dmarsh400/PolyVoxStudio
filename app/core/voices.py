import os
import torch
from TTS.api import TTS
from app.core.gpu_manager import get_device, release_device
from app.engine.text_preprocessor import TextPreprocessor
from app.engine.audio_postprocessor import AudioPostProcessor

# Global XTTS model instance (lazy loaded)
_tts_model = None
_preprocessor = None
_postprocessor = None

def get_tts_model():
    """Lazy load and return the XTTS model."""
    global _tts_model
    if _tts_model is None:
        print("[voices.py] Loading XTTS v2 model...")
        _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        # Move to CUDA if available
        if torch.cuda.is_available():
            _tts_model.to("cuda")
            print("[voices.py] XTTS model loaded on CUDA")
        else:
            print("[voices.py] XTTS model loaded on CPU")
    return _tts_model

def get_preprocessor():
    """Get text preprocessor instance."""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = TextPreprocessor()
    return _preprocessor

def get_postprocessor():
    """Get audio postprocessor instance."""
    global _postprocessor
    if _postprocessor is None:
        _postprocessor = AudioPostProcessor()
    return _postprocessor

def synthesize_text(voice_entry, text, out_path, job_idx=0):
    """
    Generate speech audio from text using XTTS v2.
    Auto-distributes jobs across available GPUs with automatic CPU fallback.
    Uses GPU manager for intelligent multi-GPU load balancing.
    """
    device_str = None
    try:
        # Get device from GPU manager (handles multi-GPU and CPU fallback)
        device_str = get_device(task_id=job_idx)
        
        # Get TTS model
        tts = get_tts_model()
        
        # Get preprocessor and clean text
        preprocessor = get_preprocessor()
        cleaned_text = preprocessor.prepare_for_tts(text)
        
        # Get speaker reference audio
        speaker_wav = voice_entry.get("voice_file", voice_entry.get("speaker_wav"))
        if not speaker_wav or not os.path.exists(speaker_wav):
            raise ValueError(f"Speaker reference audio not found: {speaker_wav}")
        
        # Get language (default to English)
        language = voice_entry.get("language", "en")
        
        print(f"[voices.py] Synthesizing with XTTS on device={device_str} → {out_path}")
        print(f"[voices.py] Using speaker: {os.path.basename(speaker_wav)}, language: {language}")
        print(f"[voices.py] Text: {cleaned_text[:100]}...")
        
        # Generate audio with XTTS
        tts.tts_to_file(
            text=cleaned_text,
            file_path=out_path,
            speaker_wav=speaker_wav,
            language=language
        )
        
        # Post-process audio for quality enhancement
        postprocessor = get_postprocessor()
        postprocessor.enhance_audio(out_path, out_path)
        
        # Release device back to pool
        if device_str:
            release_device(device_str)
        
        return out_path
    except Exception as e:
        print(f"[voices.py] Error in XTTS synthesis: {e}")
        # Release device even on error
        if device_str:
            release_device(device_str)
        raise
