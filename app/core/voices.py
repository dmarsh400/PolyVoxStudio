import os
from typing import Any, Dict

import numpy as np
import soundfile as sf
import torch
from TTS.api import TTS

from app.core.gpu_manager import get_device, release_device
from app.core.text_preprocessor import TextPreprocessor
from app.core.audio_postprocessor import AudioPostProcessor

# Global XTTS model instance (lazy loaded)
_tts_model = None
_preprocessor = None
_postprocessor = None


def _env_flag(var_name: str, default: bool) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_float(var_name: str, default: float) -> float:
    value = os.getenv(var_name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_string(var_name: str, default: str) -> str:
    value = os.getenv(var_name)
    if value is None or not value.strip():
        return default
    return value.strip()


SAFE_SENTENCE_ENDINGS_DEFAULT = _env_string("POLYVOX_SAFE_SENTENCE_ENDINGS", "none")

TAIL_TRIM_DEFAULTS: Dict[str, Any] = {
    "enabled": _env_flag("POLYVOX_TAIL_TRIM_ENABLED", False),
    "seconds_per_char": _env_float("POLYVOX_TAIL_TRIM_SECONDS_PER_CHAR", 0.052),
    "seconds_per_word": _env_float("POLYVOX_TAIL_TRIM_SECONDS_PER_WORD", 0.165),
    "base_padding": _env_float("POLYVOX_TAIL_TRIM_PADDING_SECONDS", 0.45),
    "cutoff_ratio": _env_float("POLYVOX_TAIL_TRIM_CUTOFF_RATIO", 1.08),
    "max_ratio": _env_float("POLYVOX_TAIL_TRIM_MAX_RATIO", 1.38),
    "max_extra_seconds": _env_float("POLYVOX_TAIL_TRIM_MAX_EXTRA_SECONDS", 2.4),
    "min_duration": _env_float("POLYVOX_TAIL_TRIM_MIN_DURATION", 0.95),
    "fade_out_ms": _env_float("POLYVOX_TAIL_TRIM_FADE_OUT_MS", 35.0),
}


def _resolve_safe_sentence_strategy(voice_entry: Dict[str, Any]) -> str | None:
    value = voice_entry.get("safe_sentence_endings") if isinstance(voice_entry, dict) else None
    if value is None:
        return SAFE_SENTENCE_ENDINGS_DEFAULT
    if isinstance(value, bool):
        return SAFE_SENTENCE_ENDINGS_DEFAULT if value else "none"
    normalized = str(value).strip().lower()
    if normalized in {"auto", "default"}:
        return SAFE_SENTENCE_ENDINGS_DEFAULT
    return str(value)


def _build_tail_trim_config(voice_entry: Dict[str, Any]) -> Dict[str, Any]:
    cfg = dict(TAIL_TRIM_DEFAULTS)
    if not isinstance(voice_entry, dict):
        return cfg

    entry_cfg = voice_entry.get("tail_trim")
    if isinstance(entry_cfg, dict):
        for key in cfg:
            if key in entry_cfg and entry_cfg[key] is not None:
                try:
                    if isinstance(cfg[key], bool):
                        cfg[key] = bool(entry_cfg[key])
                    else:
                        cfg[key] = float(entry_cfg[key])
                except (TypeError, ValueError):
                    pass

    if "tail_trim_enabled" in voice_entry:
        cfg["enabled"] = bool(voice_entry["tail_trim_enabled"])
    if "tail_trim_seconds_per_char" in voice_entry:
        try:
            cfg["seconds_per_char"] = float(voice_entry["tail_trim_seconds_per_char"])
        except (TypeError, ValueError):
            pass
    if "tail_trim_seconds_per_word" in voice_entry:
        try:
            cfg["seconds_per_word"] = float(voice_entry["tail_trim_seconds_per_word"])
        except (TypeError, ValueError):
            pass

    return cfg


def _load_duration_seconds(path: str | None) -> float:
    if not path or not os.path.exists(path):
        return 0.0
    try:
        data, sr = sf.read(path)
        if sr <= 0:
            return 0.0
        return float(len(data)) / float(sr)
    except Exception as exc:
        print(f"[voices.py] Failed to probe duration for {path}: {exc}")
        return 0.0


def _estimate_expected_duration_seconds(
    cleaned_text: str,
    seconds_per_char: float,
    seconds_per_word: float,
    base_padding: float,
    reference_duration: float = 0.0,
) -> float:
    text = cleaned_text.strip()
    char_count = max(len(text), 1)
    word_count = max(len(text.split()), 1)
    estimate = (
        base_padding
        + (char_count * max(seconds_per_char, 0.0))
        + (word_count * max(seconds_per_word, 0.0))
    )
    if reference_duration > 0.0:
        estimate = max(estimate, reference_duration * 0.6)
    return estimate


def _maybe_trim_tail_artifacts(
    audio_path: str,
    cleaned_text: str,
    tail_trim_config: Dict[str, Any],
    *,
    reference_path: str | None = None,
) -> None:
    if not tail_trim_config.get("enabled", True):
        return

    if not os.path.exists(audio_path):
        print(f"[voices.py] Tail trim skipped, file missing: {audio_path}")
        return

    try:
        audio, sr = sf.read(audio_path)
    except Exception as exc:
        print(f"[voices.py] Tail trim failed to read audio: {exc}")
        return

    if sr <= 0:
        return

    if isinstance(audio, np.ndarray) and audio.ndim > 1:
        samples = audio.shape[0]
    else:
        samples = len(audio)

    duration = samples / float(sr)
    ref_dur = _load_duration_seconds(reference_path)

    expected = _estimate_expected_duration_seconds(
        cleaned_text,
        seconds_per_char=float(tail_trim_config.get("seconds_per_char", 0.05)),
        seconds_per_word=float(tail_trim_config.get("seconds_per_word", 0.16)),
        base_padding=float(tail_trim_config.get("base_padding", 0.4)),
        reference_duration=ref_dur,
    )

    max_ratio = float(tail_trim_config.get("max_ratio", 1.4))
    max_extra = float(tail_trim_config.get("max_extra_seconds", 2.0))
    allowed_duration = min(expected * max_ratio, expected + max_extra)

    if duration <= allowed_duration:
        return

    cutoff_ratio = float(tail_trim_config.get("cutoff_ratio", 1.1))
    min_duration = float(tail_trim_config.get("min_duration", 0.9))
    fade_out_ms = float(tail_trim_config.get("fade_out_ms", 30.0))

    target_duration = max(
        min(duration, expected * cutoff_ratio),
        min_duration,
    )

    new_samples = min(samples, int(target_duration * sr))
    if new_samples >= samples:
        return

    trimmed = audio[:new_samples]

    if fade_out_ms > 0:
        fade_samples = min(int(sr * (fade_out_ms / 1000.0)), new_samples)
        if fade_samples > 0:
            fade_curve = np.linspace(1.0, 0.0, fade_samples, endpoint=True)
            if isinstance(trimmed, np.ndarray) and trimmed.ndim > 1:
                trimmed[-fade_samples:, :] *= fade_curve[:, None]
            else:
                trimmed[-fade_samples:] *= fade_curve

    try:
        sf.write(audio_path, trimmed, sr)
        print(
            f"[voices.py] Tail trim applied: was {duration:.2f}s → now {target_duration:.2f}s"
        )
    except Exception as exc:
        print(f"[voices.py] Tail trim failed to write audio: {exc}")


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
    ):
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

def synthesize_text(voice_entry, text, out_path, job_idx=0, speaker_name=None, **_ignored):
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
        safe_strategy = _resolve_safe_sentence_strategy(voice_entry)
        cleaned_text = preprocessor.prepare_for_tts(
            text,
            safe_sentence_endings=safe_strategy,
        )
        
        # Get speaker reference audio
        speaker_wav = voice_entry.get("voice_file", voice_entry.get("speaker_wav"))
        if not speaker_wav or not os.path.exists(speaker_wav):
            raise ValueError(f"Speaker reference audio not found: {speaker_wav}")
        
        # Get language (default to English)
        language = voice_entry.get("language", "en")
        
        resolved_speaker = speaker_name or voice_entry.get("character") or voice_entry.get("label")
        if not resolved_speaker:
            resolved_speaker = voice_entry.get("name") or os.path.splitext(os.path.basename(speaker_wav))[0]

        print(f"[voices.py] Synthesizing with XTTS on device={device_str} → {out_path}")
        print(
            f"[voices.py] Using speaker: {os.path.basename(speaker_wav)}"
            f", resolved name: {resolved_speaker}, language: {language}"
        )
        print(f"[voices.py] Text: {cleaned_text[:100]}...")
        
        tail_trim_config = _build_tail_trim_config(voice_entry)

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

        # Tail trimming fallback to reduce end-of-line artifacts
        _maybe_trim_tail_artifacts(
            out_path,
            cleaned_text,
            tail_trim_config,
            reference_path=speaker_wav,
        )
        
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
