import os
import torch
from TTS.api import TTS
from app.core.gpu_manager import get_device, release_device
from app.core.text_preprocessor import TextPreprocessor
from app.core.audio_postprocessor import AudioPostProcessor
import soundfile as sf
import numpy as np
import librosa
from pathlib import Path
from typing import Any, Dict

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


# --- XTTS Generation Presets (anchor: XTTS_PRESETS) ---
XTTS_GENERATION_PRESETS = {
    "stable_no_sample": {
        "do_sample": False,
        "num_beams": 1,
        "temperature": 0.1,
        "top_p": 1.0,
        "top_k": 0,
        "repetition_penalty": 2.0,
        "length_penalty": 1.0,
    },
    "expressive": {
        "do_sample": True,
        "num_beams": 1,
        "temperature": 0.7,
        "top_p": 0.85,
        "top_k": 50,
        "repetition_penalty": 2.0,
        "length_penalty": 1.0,
    },
}

# Map character/speaker names to presets
SPEAKER_PRESET_MAP = {
    "Narrator": "stable_no_sample",
}


def _get_generation_kwargs(speaker_name: str | None, fallback: str = "expressive") -> tuple[str, Dict[str, Any]]:
    """Resolve the XTTS generation preset for the given speaker."""
    preset_name = SPEAKER_PRESET_MAP.get((speaker_name or "").strip(), fallback)
    preset = XTTS_GENERATION_PRESETS.get(preset_name)
    if preset is None:
        preset_name = "stable_no_sample"
        preset = XTTS_GENERATION_PRESETS[preset_name]
    # Return a copy so downstream code can tweak without mutating the preset
    preset_copy = dict(preset)
    if not preset_copy.get("do_sample", True):
        preset_copy["temperature"] = None
        preset_copy["top_p"] = None
        preset_copy["top_k"] = None
    return preset_name, preset_copy


# --- Crossfade Utility (anchor: SAFE_CROSSFADE) ---
def apply_linear_crossfade(prev: np.ndarray, next_: np.ndarray, sr: int, fade_ms: int = 100) -> np.ndarray:
    """Concatenate two clips with a linear crossfade to avoid comb-filter buzz."""
    if prev.size == 0:
        return next_.copy()
    if next_.size == 0:
        return prev.copy()

    fade = max(1, int(sr * (fade_ms / 1000.0)))
    if prev.size < fade or next_.size < fade:
        fade = max(1, min(prev.size, next_.size, fade))

    fade_out = np.linspace(1.0, 0.0, fade, dtype=prev.dtype)
    fade_in = np.linspace(0.0, 1.0, fade, dtype=next_.dtype)

    cross = prev[-fade:] * fade_out + next_[:fade] * fade_in
    glued = np.concatenate([prev[:-fade], cross, next_[fade:]])
    return glued


def _patch_xtts_generation():
    """Monkey patch XTTS GPT inference to support newer transformers."""
    try:
        from TTS.tts.layers.xtts.gpt_inference import GPT2InferenceModel
    except ImportError:
        return

    prepare_fn = getattr(GPT2InferenceModel, "prepare_inputs_for_generation", None)
    code_obj = getattr(prepare_fn, "__code__", None)
    if not code_obj:
        return

    # Detect the stub that only raises NotImplementedError
    if not any(
        isinstance(const, str) and "prepare_inputs_for_generation" in const and ".generate()" in const
        for const in code_obj.co_consts
    ):
        return

    def _patched_prepare_inputs(
        self,
        input_ids,
        past_key_values=None,
        inputs_embeds=None,
        **kwargs,
    ) -> Dict[str, Any]:
        token_type_ids = kwargs.get("token_type_ids")

        if past_key_values:
            past_length = past_key_values[0][0].shape[2]
            if input_ids.shape[1] > past_length:
                remove_prefix_length = past_length
            else:
                remove_prefix_length = max(input_ids.shape[1] - 1, 0)

            input_ids = input_ids[:, remove_prefix_length:]

            if token_type_ids is not None and token_type_ids.shape[1] != input_ids.shape[1]:
                token_type_ids = token_type_ids[:, -input_ids.shape[1]:]

        attention_mask = kwargs.get("attention_mask")
        position_ids = kwargs.get("position_ids")

        if attention_mask is not None and position_ids is None:
            position_ids = attention_mask.long().cumsum(-1) - 1
            position_ids.masked_fill_(attention_mask == 0, 1)
            if past_key_values:
                position_ids = position_ids[:, -input_ids.shape[1]:]
        else:
            position_ids = None

        if inputs_embeds is not None and past_key_values is None:
            model_inputs = {"inputs_embeds": inputs_embeds}
        else:
            model_inputs = {"input_ids": input_ids}

        model_inputs.update(
            {
                "past_key_values": past_key_values,
                "use_cache": kwargs.get("use_cache"),
                "position_ids": position_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            }
        )

        return model_inputs

    GPT2InferenceModel.prepare_inputs_for_generation = _patched_prepare_inputs

def get_tts_model():
    """Lazy load and return the XTTS model."""
    global _tts_model
    if _tts_model is None:
        _patch_xtts_generation()
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

def synthesize_text(voice_entry, text, out_path, job_idx=0, speaker_name=None):
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

        resolved_speaker = speaker_name or voice_entry.get("character") or voice_entry.get("label") or voice_entry.get("name") or Path(speaker_wav).stem
        preset_name, preset_kwargs = _get_generation_kwargs(resolved_speaker)

        print(f"[voices.py] Synthesizing with XTTS on device={device_str} → {out_path}")
        print(
            f"[voices.py] Using speaker: {os.path.basename(speaker_wav)}, language: {language}, preset: {preset_name}"
        )
        print(f"[voices.py] Segments: {len(segments)}")

        # 3) Synthesize each segment with its own style cue, then glue audio
        audio_parts = []
        sr_used = None
        
        tmp_dir = Path(".polyvox_tmp")
        tmp_dir.mkdir(exist_ok=True)

        post = get_postprocessor()

        voice_language = (voice_entry.get("language") or language or "en").lower()
        preserve_accents = voice_entry.get("preserve_accents")
        if preserve_accents is None:
            preserve_accents = not voice_language.startswith("en")
        ascii_only = not preserve_accents

        for idx, seg in enumerate(segments):
            raw_seg = seg["text"]
            style = (seg.get("style") or "none").lower()
            
            # Clean + inject a small textual cue (engine may respond),
            # then rely on post-style shaping to guarantee an audible change.
            cleaned = preprocessor.prepare_for_tts(raw_seg, ascii_only=ascii_only)
            
            # Normalize text to prevent drift
            cleaned = normalize_for_tts(cleaned)

            # Bias orthography + lexicon for the target accent (removed for simplicity)
            text_to_synth = cleaned

            tmp_wav = tmp_dir / f"seg_{job_idx}_{idx}.wav"
            print(f"[voices.py] Synthesizing segment {idx}: '{cleaned}' (len={len(cleaned)})")
            tts_kwargs = {
                "text": text_to_synth,
                "file_path": str(tmp_wav),
                "speaker_wav": speaker_wav,
                "language": language,
            }
            tts_kwargs.update(preset_kwargs)
            tts.tts_to_file(**tts_kwargs)
            if os.path.exists(str(tmp_wav)):
                audio_check, _ = sf.read(str(tmp_wav))
                print(f"[voices.py] Generated audio length: {len(audio_check)} samples")
            else:
                print(f"[voices.py] Audio file not created: {tmp_wav}")

            audio, sr = sf.read(str(tmp_wav))
            if sr_used is None:
                sr_used = sr
            elif sr != sr_used:
                try:
                    orig_sr = sr
                    audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=sr_used)
                    sr = sr_used
                    print(
                        f"[voices.py] Resampled segment {idx} from {orig_sr}Hz to {sr_used}Hz for consistency"
                    )
                except Exception as resample_err:
                    print(f"[voices.py] Warning: resample failed ({resample_err}); using {sr}Hz for this segment")
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

        # 4) Concatenate with clean crossfades and optional style pauses
        if not audio_parts:
            raise RuntimeError("No audio generated.")

        if sr_used is None:
            sr_used = 24000

        glued = audio_parts[0]
        prev_style = segments[0].get("style", "none") if segments else "none"

        for idx_part, part in enumerate(audio_parts[1:], start=1):
            current_style = segments[idx_part].get("style", "none") if idx_part < len(segments) else "none"

            if prev_style and current_style and prev_style != current_style:
                pause_samples = int(0.05 * sr_used)
                if pause_samples > 0:
                    glued = np.concatenate([glued, np.zeros(pause_samples, dtype=glued.dtype)])

            glued = apply_linear_crossfade(glued, part, sr_used, fade_ms=100)
            prev_style = current_style

        glued = glued.astype(np.float32, copy=False)

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
