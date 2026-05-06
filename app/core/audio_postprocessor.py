"""
Audio Post-Processing for Professional Quality
Enhances XTTS v2 output for natural, broadcast-quality sound
"""

import os
import subprocess
import tempfile
import importlib
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf
import torch
from scipy import signal


# --- Config flags (anchor: AUDIO_POST_CONFIG) ---
def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


ENABLE_REVERB_BY_DEFAULT = False
REVERB_FILTER = "aecho=0.7:0.6:25:0.2"
_SILENCE_TRIM_LEAD = (
    "silenceremove="
    "start_periods=1:"
    "start_duration=0.06:"
    "start_threshold=-60dB:"
    "stop_periods=0"
)
_SILENCE_TRIM_TAIL = (
    "silenceremove="
    "start_periods=1:"
    "start_duration=0.18:"
    "start_threshold=-62dB:"
    "stop_periods=0"
)
SILENCE_TRIM_FILTER = f"{_SILENCE_TRIM_LEAD},areverse,{_SILENCE_TRIM_TAIL},areverse"
MIN_TAIL_SILENCE_SECONDS = max(0.0, _env_float("POLYVOX_MIN_TAIL_SILENCE", 0.38))
TAIL_SILENCE_THRESHOLD = max(1e-5, _env_float("POLYVOX_TAIL_SILENCE_THRESHOLD", 0.0025))
MIN_LEAD_SILENCE_SECONDS = max(0.0, _env_float("POLYVOX_MIN_LEAD_SILENCE", 0.18))
LEAD_SILENCE_THRESHOLD = max(1e-5, _env_float("POLYVOX_LEAD_SILENCE_THRESHOLD", 0.0025))
ENABLE_VAD_TRIM = _env_flag("POLYVOX_VAD_TRIM_ENABLED", True)
VAD_THRESHOLD = _env_float("POLYVOX_VAD_THRESHOLD", 0.5)
VAD_MIN_SPEECH_MS = int(_env_float("POLYVOX_VAD_MIN_SPEECH_MS", 120.0))
VAD_MIN_SILENCE_MS = int(_env_float("POLYVOX_VAD_MIN_SILENCE_MS", 260.0))
VAD_PAD_LEAD_MS = _env_float("POLYVOX_VAD_PAD_LEAD_MS", 160.0)
VAD_PAD_TAIL_MS = _env_float("POLYVOX_VAD_PAD_TAIL_MS", 260.0)
VAD_TARGET_SR = 16000
VAD_LONG_GAP_SECONDS = _env_float("POLYVOX_VAD_LONG_GAP_SECONDS", 1.5)
VAD_TAIL_EXTENSION_MS = max(0.0, _env_float("POLYVOX_VAD_TAIL_EXTENSION_MS", 140.0))
VAD_TAIL_THRESHOLD_FACTOR = max(0.1, _env_float("POLYVOX_VAD_TAIL_THRESHOLD_FACTOR", 0.6))
VAD_TAIL_RELEASE_MS = max(0.0, _env_float("POLYVOX_VAD_TAIL_RELEASE_MS", 60.0))
VAD_RELEASE_EXTENSION_MS = max(0.0, _env_float("POLYVOX_VAD_RELEASE_EXTENSION_MS", 120.0))


def build_filter_chain(
    *,
    purpose: str = "narration",
    enable_reverb: Optional[bool] = None,
    trim_silence: bool = True,
) -> str:
    """Construct an FFmpeg filter graph tailored for Polyvox output."""

    filters: list[str] = []

    if trim_silence:
        filters.append(SILENCE_TRIM_FILTER)

    filters.extend(
        [
            "highpass=f=70",
            "lowpass=f=12000",
            "acompressor=threshold=-21dB:ratio=2.6:attack=12:release=160",
            "dynaudnorm=f=250:g=12:p=1:n=1",
            "loudnorm=I=-16:LRA=9:TP=-1.2",
        ]
    )

    if enable_reverb is None:
        enable_reverb = ENABLE_REVERB_BY_DEFAULT and purpose.lower() == "narration"

    if enable_reverb:
        filters.append(REVERB_FILTER)

    return ",".join(filters)


if TYPE_CHECKING:  # pragma: no cover - typing helper only
    from silero_vad import get_speech_timestamps as _GetSpeechTimestampsType
    from silero_vad import load_silero_vad as _LoadSileroVadType



silero_spec = importlib.util.find_spec("silero_vad")
if silero_spec is not None:  # pragma: no cover - optional dependency
    silero_module = importlib.import_module("silero_vad")
    load_silero_vad = getattr(silero_module, "load_silero_vad", None)
    get_speech_timestamps = getattr(silero_module, "get_speech_timestamps", None)
    _VAD_AVAILABLE = bool(load_silero_vad and get_speech_timestamps)
else:
    load_silero_vad = None
    get_speech_timestamps = None
    _VAD_AVAILABLE = False


_VAD_MODEL = None
_VAD_MODEL_LOCK = threading.Lock()
_VAD_WARNING_EMITTED = False


class AudioPostProcessor:
    """Backend audio enhancement for natural, professional sound"""
    
    def __init__(self, target_sample_rate: int = 24000):
        self.sample_rate = target_sample_rate
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, 
                         check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  FFmpeg not found. Install for better performance: apt-get install ffmpeg")
            return False

    def _get_vad_model(self):
        """Lazy-load and cache the Silero VAD model if available."""
        if not ENABLE_VAD_TRIM or not _VAD_AVAILABLE:
            return None
        global _VAD_MODEL
        if _VAD_MODEL is not None:
            return _VAD_MODEL
        if load_silero_vad is None:  # safety guard
            return None
        with _VAD_MODEL_LOCK:
            if _VAD_MODEL is None:
                model = load_silero_vad()
                if model is None:
                    return None
                model.to("cpu")
                model.eval()
                _VAD_MODEL = model
        return _VAD_MODEL

    # --- VAD assisted trimming -------------------------------------------------
    def _run_vad_trim(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Use Silero VAD to detect speech bounds and return a trimmed clip plus stats.
        Returns None if VAD is disabled/unavailable or on failure.
        """

        global _VAD_WARNING_EMITTED

        if sample_rate <= 0 or not ENABLE_VAD_TRIM:
            return None

        if not _VAD_AVAILABLE or get_speech_timestamps is None:
            if not _VAD_WARNING_EMITTED:
                print(
                    "[AudioPostProcessor] Silero VAD trim requested but 'silero-vad' "
                    "package is not installed; falling back to amplitude-based trims."
                )
                _VAD_WARNING_EMITTED = True
            return None

        model = self._get_vad_model()
        if model is None:
            return None

        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            mono = audio.astype(np.float32, copy=False).mean(axis=1)
        else:
            mono = np.asarray(audio, dtype=np.float32)

        if mono.size == 0:
            return {
                "applied": False,
                "audio": audio,
                "stats": {
                    "status": "empty",
                    "speech_seconds": 0.0,
                    "speech_ratio": 0.0,
                    "num_segments": 0,
                },
                "segments": [],
            }

        mono = np.clip(mono, -1.0, 1.0)

        if sample_rate != VAD_TARGET_SR:
            mono_resampled = librosa.resample(
                mono,
                orig_sr=sample_rate,
                target_sr=VAD_TARGET_SR,
                res_type="soxr_hq",
            )
        else:
            mono_resampled = mono

        wav_tensor = torch.from_numpy(mono_resampled.astype(np.float32, copy=False))

        if wav_tensor.ndim != 1:
            wav_tensor = wav_tensor.flatten()

        with torch.no_grad():
            speech_segments = get_speech_timestamps(
                wav_tensor,
                model,
                sampling_rate=VAD_TARGET_SR,
                threshold=VAD_THRESHOLD,
                min_speech_duration_ms=VAD_MIN_SPEECH_MS,
                min_silence_duration_ms=VAD_MIN_SILENCE_MS,
                return_seconds=True,
            )

        raw_duration = float(len(audio)) / float(sample_rate)
        stats: Dict[str, Any] = {
            "status": "ok" if speech_segments else "no_speech",
            "num_segments": len(speech_segments),
            "speech_seconds": 0.0,
            "speech_ratio": 0.0,
            "max_gap_seconds": 0.0,
            "segments": speech_segments,
        }

        if not speech_segments:
            stats["speech_seconds"] = 0.0
            stats["speech_ratio"] = 0.0
            print(
                "[AudioPostProcessor] VAD detected no speech; skipping trim for this clip."
            )
            return {
                "applied": False,
                "audio": audio,
                "stats": stats,
                "segments": speech_segments,
            }

        # compute aggregate metrics
        speech_total = 0.0
        max_gap = 0.0
        prev_end = None
        for seg in speech_segments:
            start_s = float(seg.get("start", 0.0))
            end_s = float(seg.get("end", 0.0))
            speech_total += max(end_s - start_s, 0.0)
            if prev_end is not None:
                gap = max(0.0, start_s - prev_end)
                max_gap = max(max_gap, gap)
            prev_end = end_s

        stats["speech_seconds"] = speech_total
        stats["speech_ratio"] = (
            speech_total / raw_duration if raw_duration > 0.0 else 0.0
        )
        stats["max_gap_seconds"] = max_gap
        stats["long_gap_detected"] = max_gap > VAD_LONG_GAP_SECONDS

        pad_lead = VAD_PAD_LEAD_MS / 1000.0
        pad_tail = VAD_PAD_TAIL_MS / 1000.0

        first_start = float(speech_segments[0]["start"])
        last_end = float(speech_segments[-1]["end"])
        base_last_end = last_end

        start_sec = max(first_start - pad_lead, 0.0)
        end_sec = min(last_end + pad_tail, raw_duration)

        start_idx = int(round(start_sec * sample_rate))
        end_idx = int(round(end_sec * sample_rate))

        tail_extension_seconds = 0.0
        tail_silence_run_seconds = 0.0
        release_extension_seconds = 0.0

        if isinstance(audio, np.ndarray) and audio.size > 0:
            if audio.ndim > 1:
                envelope = np.max(np.abs(audio), axis=1)
            else:
                envelope = np.abs(audio)

            base_speech_end_idx = int(round(base_last_end * sample_rate))
            tail_guard_samples = int(round((VAD_TAIL_EXTENSION_MS / 1000.0) * sample_rate))
            release_silence_samples = int(round((VAD_TAIL_RELEASE_MS / 1000.0) * sample_rate))
            release_extension_samples = int(round((VAD_RELEASE_EXTENSION_MS / 1000.0) * sample_rate))

            tail_threshold = max(1e-7, TAIL_SILENCE_THRESHOLD * VAD_TAIL_THRESHOLD_FACTOR)
            release_silence_samples = max(1, release_silence_samples)
            release_extension_samples = max(0, release_extension_samples)

            energy_end_idx = base_speech_end_idx
            silence_run = 0

            if tail_guard_samples > 0 and base_speech_end_idx < len(envelope):
                search_end = min(len(envelope), base_speech_end_idx + tail_guard_samples)
                for idx in range(base_speech_end_idx, search_end):
                    level = envelope[idx]
                    candidate = idx + 1
                    if level < tail_threshold:
                        silence_run += 1
                        if silence_run >= release_silence_samples:
                            break
                    else:
                        silence_run = 0
                        energy_end_idx = max(energy_end_idx, candidate)
                else:
                    energy_end_idx = max(energy_end_idx, search_end)

            if silence_run > 0:
                tail_silence_run_seconds = silence_run / sample_rate

            effective_speech_end_idx = min(
                len(envelope),
                max(energy_end_idx, base_speech_end_idx) + release_extension_samples,
            )

            if effective_speech_end_idx > base_speech_end_idx:
                new_last_end = min(raw_duration, effective_speech_end_idx / sample_rate)
                tail_extension_seconds = max(0.0, new_last_end - base_last_end)
                release_extension_seconds = max(
                    0.0,
                    (effective_speech_end_idx - energy_end_idx) / sample_rate,
                )
                last_end = new_last_end
                end_sec = min(last_end + pad_tail, raw_duration)
                end_idx = int(round(end_sec * sample_rate))

        end_idx = max(start_idx + 1, min(end_idx, len(audio)))
        end_sec = min(end_idx / sample_rate, raw_duration)

        trimmed_audio = audio[start_idx:end_idx]

        stats["trim_start_seconds"] = start_sec
        stats["trim_end_seconds"] = end_sec
        stats["pad_lead_seconds"] = max(0.0, first_start - start_sec)
        stats["pad_tail_seconds"] = max(0.0, end_sec - last_end)
        stats["tail_extension_seconds"] = tail_extension_seconds
        stats["tail_silence_run_seconds"] = tail_silence_run_seconds
        stats["release_extension_seconds"] = release_extension_seconds
        stats["speech_end_seconds"] = last_end

        applied = start_idx > 0 or end_idx < len(audio)

        if applied:
            print(
                "[AudioPostProcessor] VAD trim applied: "
                f"{raw_duration:.2f}s → {len(trimmed_audio) / sample_rate:.2f}s"
                f" (segments={len(speech_segments)})"
            )
        elif stats["long_gap_detected"]:
            print(
                "[AudioPostProcessor] VAD detected long internal silence "
                f"({stats['max_gap_seconds']:.2f}s) but trims not applied"
            )

        return {
            "applied": applied,
            "audio": trimmed_audio if applied else audio,
            "stats": stats,
            "segments": speech_segments,
            "trim_indices": (start_idx, end_idx),
        }
    # --- Style presets (subtle post synthesis prosody shading) ----------------
    def apply_style_preset(self, audio: np.ndarray, preset: str) -> np.ndarray:
        """
        Apply style preset - currently disabled for cleaner audio.
        """
        # Return audio unchanged to avoid artificial effects
        return audio

    def normalize_audio(self, audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
        """
        Normalize audio to consistent peak level
        
        Args:
            audio: Audio samples
            target_peak: Target peak amplitude (0.0-1.0)
        
        Returns:
            Normalized audio
        """
        peak = np.abs(audio).max()
        if peak > 0:
            audio = audio * (target_peak / peak)
        return audio
    
    def apply_gentle_compression(self, 
                                 audio: np.ndarray,
                                 threshold_db: float = -20.0,
                                 ratio: float = 3.0) -> np.ndarray:
        """
        Apply gentle dynamic range compression
        Makes quiet parts more audible without making loud parts too loud
        
        Args:
            audio: Audio samples
            threshold_db: Compression threshold in dB
            ratio: Compression ratio
        
        Returns:
            Compressed audio
        """
        # Convert to dB
        epsilon = 1e-8
        audio_db = 20 * np.log10(np.abs(audio) + epsilon)
        
        # Apply compression above threshold
        compressed_db = np.where(
            audio_db > threshold_db,
            threshold_db + (audio_db - threshold_db) / ratio,
            audio_db
        )
        
        # Convert back to linear
        compressed = np.sign(audio) * (10 ** (compressed_db / 20))
        
        return compressed
    
    def add_subtle_reverb(self, 
                         audio: np.ndarray,
                         delay_ms: float = 30.0,
                         decay: float = 0.15) -> np.ndarray:
        """
        Add subtle room reverb for less 'studio clean' sound
        
        Args:
            audio: Audio samples
            delay_ms: Delay in milliseconds
            decay: Reverb decay amount (0.0-1.0)
        
        Returns:
            Audio with reverb
        """
        # Calculate delay in samples
        delay_samples = int((delay_ms / 1000.0) * self.sample_rate)
        
        # Create delayed version
        delayed = np.concatenate([
            np.zeros(delay_samples),
            audio
        ])[:len(audio)]
        
        # Mix with original
        return audio + (decay * delayed)
    
    def enhance_vocal_presence(self, 
                              audio: np.ndarray,
                              center_freq: float = 4000.0,
                              bandwidth: float = 1000.0,
                              gain_db: float = 2.0) -> np.ndarray:
        """
        Boost 3-5kHz range for clearer speech
        
        Args:
            audio: Audio samples
            center_freq: Center frequency for boost
            bandwidth: Bandwidth of boost
            gain_db: Gain in dB
        
        Returns:
            Audio with enhanced presence
        """
        # Calculate frequency range
        low_freq = center_freq - (bandwidth / 2)
        high_freq = center_freq + (bandwidth / 2)
        
        # Create bandpass filter
        sos = signal.butter(4, [low_freq, high_freq], 
                          'bandpass', 
                          fs=self.sample_rate, 
                          output='sos')
        
        # Apply filter
        filtered = signal.sosfilt(sos, audio)
        
        # Convert gain from dB to linear
        gain_linear = 10 ** (gain_db / 20)
        
        # Mix back with original
        return audio + ((gain_linear - 1.0) * filtered)
    
    def remove_silence_padding(
        self,
        audio: np.ndarray,
        *,
        lead_threshold: float = LEAD_SILENCE_THRESHOLD,
        tail_threshold: float = TAIL_SILENCE_THRESHOLD,
        lead_in_ms: float = 150.0,
        tail_ms: float = 160.0,
    ) -> np.ndarray:
        """
        Trim excessive silence from start/end
        
        Args:
            audio: Audio samples
            threshold: Silence threshold
            lead_in_ms: Lead-in to keep (ms)
            tail_ms: Tail to keep (ms)
        
        Returns:
            Trimmed audio
        """
        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            envelope = np.max(np.abs(audio), axis=1)
        else:
            envelope = np.abs(audio)
        
        # Convert lead-in/tail to samples
        lead_samples = int((lead_in_ms / 1000.0) * self.sample_rate)
        tail_samples = int((tail_ms / 1000.0) * self.sample_rate)
        
        lead_indices = np.where(envelope >= lead_threshold)[0]
        tail_indices = np.where(envelope >= tail_threshold)[0]
        
        if len(lead_indices) == 0 or len(tail_indices) == 0:
            # All silence - return as is
            return audio
        
        start_idx = max(0, lead_indices[0] - lead_samples)
        end_idx = min(len(envelope), tail_indices[-1] + tail_samples)
        
        return audio[start_idx:end_idx]

    def _ensure_minimum_leading_silence(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        min_silence_s: float = MIN_LEAD_SILENCE_SECONDS,
        threshold: float = LEAD_SILENCE_THRESHOLD,
    ) -> tuple[np.ndarray, int]:
        """Ensure there's a small pre-roll so first phonemes aren't clipped."""
        if min_silence_s <= 0 or sr <= 0:
            return audio, 0

        required_samples = int(min_silence_s * sr)
        if required_samples <= 0:
            return audio, 0

        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            envelope = np.max(np.abs(audio), axis=1)
        else:
            envelope = np.abs(audio)

        if envelope.size == 0:
            pad_shape = (required_samples,) if audio.ndim == 1 else (required_samples, audio.shape[1])
            pad = np.zeros(pad_shape, dtype=audio.dtype if isinstance(audio, np.ndarray) else np.float32)
            return pad, required_samples

        leading_samples = 0
        for value in envelope:
            if value < threshold:
                leading_samples += 1
            else:
                break

        if leading_samples >= required_samples:
            return audio, 0

        pad_needed = required_samples - leading_samples
        if pad_needed <= 0:
            return audio, 0

        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            pad = np.zeros((pad_needed, audio.shape[1]), dtype=audio.dtype)
            padded = np.concatenate([pad, audio], axis=0)
        else:
            pad = np.zeros(pad_needed, dtype=getattr(audio, 'dtype', np.float32))
            padded = np.concatenate([pad, audio])

        return padded, pad_needed

    def _ensure_minimum_trailing_silence(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        min_silence_s: float = MIN_TAIL_SILENCE_SECONDS,
        threshold: float = TAIL_SILENCE_THRESHOLD,
    ) -> tuple[np.ndarray, int]:
        """Guarantee a small trailing pause so glued segments retain breathing room."""
        if min_silence_s <= 0 or sr <= 0:
            return audio, 0

        required_samples = int(min_silence_s * sr)
        if required_samples <= 0:
            return audio, 0

        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            envelope = np.max(np.abs(audio), axis=1)
        else:
            envelope = np.abs(audio)

        if envelope.size == 0:
            pad_shape = (required_samples,) if audio.ndim == 1 else (required_samples, audio.shape[1])
            pad = np.zeros(pad_shape, dtype=audio.dtype if isinstance(audio, np.ndarray) else np.float32)
            return pad, required_samples

        silence_samples = 0
        for value in envelope[::-1]:
            if value < threshold:
                silence_samples += 1
            else:
                break

        if silence_samples >= required_samples:
            return audio, 0

        pad_needed = required_samples - silence_samples
        if pad_needed <= 0:
            return audio, 0

        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            pad = np.zeros((pad_needed, audio.shape[1]), dtype=audio.dtype)
            padded = np.concatenate([audio, pad], axis=0)
        else:
            pad = np.zeros(pad_needed, dtype=getattr(audio, 'dtype', np.float32))
            padded = np.concatenate([audio, pad])

        return padded, pad_needed

    def apply_highpass(self, audio: np.ndarray, cutoff: float = 80.0, order: int = 2) -> np.ndarray:
        """Apply a gentle high-pass filter to remove low-frequency rumble."""
        if cutoff <= 0 or self.sample_rate <= 0:
            return audio
        sos = signal.butter(order, cutoff, btype="highpass", fs=self.sample_rate, output="sos")
        return signal.sosfilt(sos, audio)
    
    def process_python(
        self,
        audio: np.ndarray,
        enhance: bool = True,
        *,
        trim_silence: bool = True,
    ) -> np.ndarray:
        """
        Python-based processing pipeline
        
        Args:
            audio: Input audio samples
            enhance: Apply enhancement filters
        
        Returns:
            Processed audio
        """
        # 1. Remove excessive silence
        if trim_silence:
            audio = self.remove_silence_padding(audio)

        if enhance:
            # 2. Clean low-end rumble
            audio = self.apply_highpass(audio)

            # 3. Gentle compression
            audio = self.apply_gentle_compression(audio)

        # Final normalization
        audio = self.normalize_audio(audio)

        return audio
    
    def process_ffmpeg(
        self,
        input_path: str,
        output_path: str,
        *,
        purpose: str = "narration",
        enable_reverb: bool | None = None,
        trim_silence: bool = True,
    ) -> str:
        """
        FFmpeg-based processing (faster, recommended)
        
        Args:
            input_path: Path to input audio file
            output_path: Path to output audio file
        
        Returns:
            Path to processed file
        """
        if not self.ffmpeg_available:
            raise RuntimeError("FFmpeg not available")
        
        # Build filter chain
        filters = build_filter_chain(
            purpose=purpose,
            enable_reverb=enable_reverb,
            trim_silence=trim_silence,
        )
        
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-af', filters,
            '-ar', str(self.sample_rate),
            '-y',  # Overwrite output
            output_path
        ]
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        return output_path
    
    def process(
        self,
        input_path: str,
        output_path: str,
        enhance: bool = True,
        method: str = 'auto',
        *,
        enable_reverb: bool | None = None,
        purpose: str = "narration",
    ) -> Tuple[str, dict]:
        """
        Process audio file with optimal method
        
        Args:
            input_path: Path to input audio
            output_path: Path to output audio
            enhance: Apply enhancement filters
            method: 'ffmpeg', 'python', or 'auto'
        
        Returns:
            Tuple of (output_path, stats)
        """
        # Choose method
        if method == 'auto':
            method = 'ffmpeg' if self.ffmpeg_available else 'python'
        
        # Get input info (raw audio as produced by TTS)
        raw_audio, sr_in = sf.read(input_path)
        raw_duration = len(raw_audio) / sr_in if sr_in else 0.0

        vad_info = self._run_vad_trim(raw_audio, sr_in)
        vad_stats = vad_info.get("stats") if vad_info else None
        vad_applied = bool(vad_info and vad_info.get("applied"))

        proc_audio = vad_info["audio"] if vad_applied else raw_audio
        duration_in = len(proc_audio) / sr_in if sr_in else raw_duration

        source_path = input_path
        vad_temp_path: Optional[str] = None
        if method == 'ffmpeg' and vad_applied:
            fd, vad_temp_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            sf.write(vad_temp_path, proc_audio, sr_in)
            source_path = vad_temp_path

        # Process based on method
        if method == 'ffmpeg':
            output_path = self.process_ffmpeg(
                source_path,
                output_path,
                purpose=purpose,
                enable_reverb=enable_reverb,
                trim_silence=not vad_applied,
            )
        else:
            # Python processing (operate on numpy array directly)
            audio_out = self.process_python(
                proc_audio,
                enhance=enhance,
                trim_silence=not vad_applied,
            )
            sf.write(output_path, audio_out, self.sample_rate)

        # Get output info
        audio_out, sr_out = sf.read(output_path)

        if method.startswith('ffmpeg'):
            normalized = self.normalize_audio(np.asarray(audio_out, dtype=np.float32))
            if not np.allclose(normalized, audio_out, atol=1e-6):
                sf.write(output_path, normalized, sr_out)
                audio_out = normalized

        duration_out = len(audio_out) / sr_out

        duration_ratio = (duration_out / duration_in) if duration_in > 0 else 1.0
        duration_delta = duration_in - duration_out
        fallback_applied = False
        fallback_reason: Optional[str] = None

        suspicious_trim = (
            duration_in >= 4.0
            and duration_ratio < 0.45
            and duration_delta > 3.0
        )

        if suspicious_trim:
            fallback_reason = (
                f"duration shrank from {duration_in:.2f}s to {duration_out:.2f}s"
            )
            print(
                "[AudioPostProcessor] ⚠ Detected aggressive trim ("
                f"{fallback_reason}); retrying without silence removal."
            )

            try:
                if method == 'ffmpeg':
                    self.process_ffmpeg(
                        source_path,
                        output_path,
                        purpose=purpose,
                        enable_reverb=enable_reverb,
                        trim_silence=False,
                    )
                    method = 'ffmpeg-no-trim'
                else:
                    audio_out = self.process_python(
                        proc_audio,
                        enhance=enhance,
                        trim_silence=False,
                    )
                    sf.write(output_path, audio_out, self.sample_rate)
                    method = f"{method}-no-trim"
                fallback_applied = True
            except Exception as exc:
                print(
                    "[AudioPostProcessor] ⚠ Fallback processing failed ("
                    f"{exc}); applying python pipeline without trimming."
                )
                audio_out = self.process_python(
                    proc_audio,
                    enhance=enhance,
                    trim_silence=False,
                )
                sf.write(output_path, audio_out, self.sample_rate)
                method = 'python-no-trim'
                fallback_applied = True

            audio_out, sr_out = sf.read(output_path)

            if method.startswith('ffmpeg'):
                normalized = self.normalize_audio(np.asarray(audio_out, dtype=np.float32))
                if not np.allclose(normalized, audio_out, atol=1e-6):
                    sf.write(output_path, normalized, sr_out)
                    audio_out = normalized

            duration_out = len(audio_out) / sr_out

        if vad_temp_path and os.path.exists(vad_temp_path):
            os.unlink(vad_temp_path)

        lead_pad_seconds = 0.0
        tail_pad_seconds = 0.0
        modified_audio = audio_out

        modified_audio, lead_pad_samples = self._ensure_minimum_leading_silence(
            modified_audio,
            sr_out,
        )
        if lead_pad_samples > 0:
            lead_pad_seconds = lead_pad_samples / sr_out

        modified_audio, tail_pad_samples = self._ensure_minimum_trailing_silence(
            modified_audio,
            sr_out,
        )
        if tail_pad_samples > 0:
            tail_pad_seconds = tail_pad_samples / sr_out

        if lead_pad_samples > 0 or tail_pad_samples > 0:
            sf.write(output_path, modified_audio, sr_out)
            audio_out = modified_audio
            duration_out = len(audio_out) / sr_out
        
        # Calculate stats
        stats = {
            'method': method,
            'duration_in': duration_in,
            'duration_out': duration_out,
            'samples_in': len(proc_audio),
            'samples_out': len(audio_out),
            'peak_in': float(np.abs(proc_audio).max()),
            'peak_out': float(np.abs(audio_out).max()),
            'rms_in': float(np.sqrt(np.mean(proc_audio**2))),
            'rms_out': float(np.sqrt(np.mean(audio_out**2))),
        }

        stats['fallback_applied'] = fallback_applied
        if fallback_reason:
            stats['fallback_reason'] = fallback_reason
        stats['lead_silence_pad_seconds'] = lead_pad_seconds
        stats['tail_silence_pad_seconds'] = tail_pad_seconds
        stats['duration_raw'] = raw_duration
        stats['samples_raw'] = len(raw_audio)
        stats['vad_applied'] = vad_applied
        if vad_stats is not None:
            stats['vad'] = vad_stats
            stats['vad_long_gap_detected'] = bool(vad_stats.get('long_gap_detected'))
        if vad_info and vad_info.get('trim_indices'):
            stats['vad_trim_indices'] = vad_info['trim_indices']
        
        return output_path, stats
    
    def enhance_audio(
        self,
        input_path,
        output_path,
        *,
        enable_reverb: bool | None = None,
        purpose: str = "narration",
    ):
        """
        Enhance audio quality using FFmpeg filters or Python processing.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save enhanced audio
        """
        try:
            # Check input duration
            if os.path.exists(input_path):
                audio_in, sr_in = sf.read(input_path)
                dur_in = len(audio_in) / sr_in
                print(f"[AudioPostProcessor] Input audio duration: {dur_in:.2f}s ({len(audio_in)} samples @ {sr_in}Hz)")
            else:
                print(f"[AudioPostProcessor] Input file does not exist: {input_path}")
                return
            
            if input_path == output_path:
                # In-place enhancement: use temp file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    temp_path = tmp.name
                try:
                    self.process(
                        input_path,
                        temp_path,
                        enhance=True,
                        method='auto',
                        enable_reverb=enable_reverb,
                        purpose=purpose,
                    )
                    # Check temp duration
                    if os.path.exists(temp_path):
                        audio_temp, sr_temp = sf.read(temp_path)
                        dur_temp = len(audio_temp) / sr_temp
                        print(f"[AudioPostProcessor] Temp audio duration: {dur_temp:.2f}s")
                    # Move temp to output
                    import shutil
                    shutil.move(temp_path, output_path)
                finally:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                self.process(
                    input_path,
                    output_path,
                    enhance=True,
                    method='auto',
                    enable_reverb=enable_reverb,
                    purpose=purpose,
                )
            
            # Check output duration
            if os.path.exists(output_path):
                audio_out, sr_out = sf.read(output_path)
                dur_out = len(audio_out) / sr_out
                print(f"[AudioPostProcessor] Output audio duration: {dur_out:.2f}s ({len(audio_out)} samples @ {sr_out}Hz)")
            else:
                print(f"[AudioPostProcessor] Output file not created: {output_path}")
                
        except Exception as e:
            print(f"[AudioPostProcessor] Enhancement failed: {e}")
            # If enhancement fails, copy original file if needed
            if input_path != output_path:
                import shutil
                shutil.copy2(input_path, output_path)


# Example usage and testing
if __name__ == "__main__":
    import os
    
    print("="*80)
    print("AUDIO POST-PROCESSOR TEST")
    print("="*80)
    
    # Create test audio
    test_sr = 24000
    duration = 3.0
    t = np.linspace(0, duration, int(duration * test_sr))
    
    # Generate test tone (440 Hz with some harmonics)
    audio = (
        0.5 * np.sin(2 * np.pi * 440 * t) +
        0.3 * np.sin(2 * np.pi * 880 * t) +
        0.2 * np.sin(2 * np.pi * 1320 * t)
    )
    
    # Add some silence padding
    silence_padding = np.zeros(int(0.5 * test_sr))
    audio = np.concatenate([silence_padding, audio, silence_padding])
    
    # Save test file
    test_dir = Path('audio_test_temp')
    test_dir.mkdir(exist_ok=True)
    
    input_file = test_dir / 'test_input.wav'
    output_file = test_dir / 'test_output.wav'
    
    sf.write(str(input_file), audio, test_sr)
    
    # Process
    processor = AudioPostProcessor()
    
    print(f"\n📥 Input file: {input_file}")
    print(f"📤 Output file: {output_file}\n")
    
    output_path, stats = processor.process(
        str(input_file),
        str(output_file),
        enhance=True,
        method='auto'
    )
    
    print(f"✅ Processing complete!\n")
    print(f"📊 Statistics:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.4f}")
        else:
            print(f"   {key}: {value}")
    
    print(f"\n💡 Method used: {stats['method']}")
    
    # Cleanup
    if input_file.exists():
        input_file.unlink()
    print(f"\n🧹 Test file cleaned up")
    print(f"📁 Enhanced test file: {output_file}")
    
    print("\n" + "="*80)
    print("✅ Post-processor ready for production use!")
    print("="*80)
