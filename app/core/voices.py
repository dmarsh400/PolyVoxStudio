import os
import torch
from TTS.api import TTS
from app.core.gpu_manager import get_device, release_device
from app.core.text_preprocessor import TextPreprocessor
from app.core.audio_postprocessor import AudioPostProcessor
import soundfile as sf
import numpy as np
from pathlib import Path

# --- Accent control (removed for simplicity) ---

def normalize_for_tts(text):
    """Normalize text to prevent TTS drift and artifacts."""
    import re
    
    # Expand common abbreviations
    abbr = {
        "Mr.": "Mister", "Mrs.": "Missus", "Ms.": "Miss", "Dr.": "Doctor",
        "Prof.": "Professor", "etc.": "et cetera", "vs.": "versus",
        "Jr.": "Junior", "Sr.": "Senior"
    }
    for k, v in abbr.items():
        text = text.replace(k, v)
    
    # Remove stray periods in mid-sentence (like A., B.)
    text = re.sub(r'\b([A-Za-z])\.(\s)', r'\1\2', text)
    
    # Handle domains (remove dot in .com etc.)
    text = re.sub(r'\b(\w+)\.(com|org|net|gov|edu)\b', r'\1 \2', text)
    
    # Ensure proper sentence-final punctuation
    if text and text.rstrip()[-1] not in ".!?":
        text += "."
    
    return text

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
        
        # Get preprocessor
        preprocessor = get_preprocessor()

        # 1) Segment by emotion so styles don't bleed across lines
        segments = preprocessor.segment_by_emotion(text)

        # 2) Resolve speaker reference + language
        speaker_wav = voice_entry.get("voice_file", voice_entry.get("speaker_wav"))
        if not speaker_wav or not os.path.exists(speaker_wav):
            raise ValueError(f"Speaker reference audio not found: {speaker_wav}")

        # Hardcode narrator to always be neutral
        if "narrator" in os.path.basename(speaker_wav).lower():
            for seg in segments:
                seg["style"] = "none"

        # Resolve language (simplified to English for natural synthesis)
        language = "en"

        print(f"[voices.py] Synthesizing with XTTS on device={device_str} → {out_path}")
        print(f"[voices.py] Using speaker: {os.path.basename(speaker_wav)}, language: {language}")
        print(f"[voices.py] Segments: {len(segments)}")

        # 3) Synthesize each segment with its own style cue, then glue audio
        audio_parts = []
        sr_used = None
        
        tmp_dir = Path(".polyvox_tmp")
        tmp_dir.mkdir(exist_ok=True)

        post = get_postprocessor()

        for idx, seg in enumerate(segments):
            raw_seg = seg["text"]
            style = (seg.get("style") or "none").lower()
            
            # Clean + inject a small textual cue (engine may respond),
            # then rely on post-style shaping to guarantee an audible change.
            cleaned = preprocessor.prepare_for_tts(raw_seg)
            
            # Normalize text to prevent drift
            cleaned = normalize_for_tts(cleaned)

            # Bias orthography + lexicon for the target accent (removed for simplicity)
            text_to_synth = cleaned

            tmp_wav = tmp_dir / f"seg_{job_idx}_{idx}.wav"
            print(f"[voices.py] Synthesizing segment {idx}: '{cleaned}' (len={len(cleaned)})")
            tts.tts_to_file(
                text=text_to_synth,
                file_path=str(tmp_wav),
                speaker_wav=speaker_wav,
                language=language,
                temperature=0.8,
                top_p=0.95,
                top_k=50
            )
            if os.path.exists(str(tmp_wav)):
                audio_check, _ = sf.read(str(tmp_wav))
                print(f"[voices.py] Generated audio length: {len(audio_check)} samples")
            else:
                print(f"[voices.py] Audio file not created: {tmp_wav}")

            audio, sr = sf.read(str(tmp_wav))
            if sr_used is None:
                sr_used = sr

            # Add trailing silence to prevent end-of-sequence drift
            silence_duration = 0.2  # 200ms
            silence_samples = int(silence_duration * sr)
            silence = np.zeros(silence_samples, dtype=audio.dtype)
            audio = np.concatenate([audio, silence])

            # Subtle post-style shading per segment
            audio = post.apply_style_preset(audio, style)
            # Normalize volume per segment for consistent levels
            audio = post.normalize_audio(audio)
            audio_parts.append(audio.astype(np.float32))

        # 4) Concatenate with improved crossfade and micro-pauses for style changes
        if not audio_parts:
            raise RuntimeError("No audio generated.")
        fade = int(0.1 * sr_used)  # 100 ms crossfade for smoother transitions
        glued = audio_parts[0]
        prev_style = None
        for part in audio_parts[1:]:
            # Add micro-pause if style changed
            current_style = segments[len(audio_parts) - len(audio_parts[1:]) - 1]['style']  # approximate
            if prev_style and prev_style != current_style:
                silence = np.zeros(int(0.05 * sr_used))  # 50ms pause
                glued = np.concatenate([glued, silence])
            prev_style = current_style
            
            if len(glued) >= fade and len(part) >= fade:
                # Use proper Hann window crossfade to prevent artifacts
                # Hann window: 0.5 * (1 - cos(2πt/T)) for smooth fade
                t = np.linspace(0, 1, fade)
                hann_fade_out = 0.5 * (1 - np.cos(2 * np.pi * t))  # Fade out: 1 → 0
                hann_fade_in = 0.5 * (1 + np.cos(2 * np.pi * t))   # Fade in: 0 → 1
                
                # Apply crossfade
                fade_out_section = glued[-fade:] * hann_fade_out
                fade_in_section = part[:fade] * hann_fade_in
                cross_section = fade_out_section + fade_in_section
                
                # Concatenate: [glued_without_fade] + [crossfaded_section] + [part_without_fade]
                glued = np.concatenate([glued[:-fade], cross_section, part[fade:]])
            else:
                glued = np.concatenate([glued, part])

        # 5) Write and run your normal enhancement
        sf.write(out_path, glued, sr_used)
        print(f"[voices.py] Wrote glued audio to {out_path}, length: {len(glued)} samples @ {sr_used}Hz, duration: {len(glued)/sr_used:.2f}s")
        post.enhance_audio(out_path, out_path)
        
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
