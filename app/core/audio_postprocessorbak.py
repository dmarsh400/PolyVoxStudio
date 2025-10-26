"""
Audio Post-Processing for Professional Quality
Enhances XTTS v2 output for natural, broadcast-quality sound
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
from scipy import signal


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
    
    def remove_silence_padding(self, 
                              audio: np.ndarray,
                              threshold: float = 0.01,
                              lead_in_ms: float = 100.0,
                              tail_ms: float = 100.0) -> np.ndarray:
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
        # Find non-silent regions
        is_silence = np.abs(audio) < threshold
        
        # Convert lead-in/tail to samples
        lead_samples = int((lead_in_ms / 1000.0) * self.sample_rate)
        tail_samples = int((tail_ms / 1000.0) * self.sample_rate)
        
        # Find first non-silent sample
        non_silent_indices = np.where(~is_silence)[0]
        
        if len(non_silent_indices) == 0:
            # All silence - return as is
            return audio
        
        start_idx = max(0, non_silent_indices[0] - lead_samples)
        end_idx = min(len(audio), non_silent_indices[-1] + tail_samples)
        
        return audio[start_idx:end_idx]
    
    def process_python(self, 
                      audio: np.ndarray,
                      enhance: bool = True) -> np.ndarray:
        """
        Python-based processing pipeline
        
        Args:
            audio: Input audio samples
            enhance: Apply enhancement filters
        
        Returns:
            Processed audio
        """
        # 1. Remove excessive silence
        audio = self.remove_silence_padding(audio)
        
        # 2. Normalize volume
        audio = self.normalize_audio(audio)
        
        if enhance:
            # 3. Gentle compression
            audio = self.apply_gentle_compression(audio)
            
            # 4. Enhance vocal presence
            audio = self.enhance_vocal_presence(audio)
            
            # 5. Add subtle reverb
            audio = self.add_subtle_reverb(audio)
            
            # 6. Final normalization
            audio = self.normalize_audio(audio)
        
        return audio
    
    def process_ffmpeg(self, input_path: str, output_path: str) -> str:
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
        filters = [
            # 1. Loudness normalization (EBU R128 standard)
            'loudnorm=I=-16:TP=-1.5:LRA=11',
            
            # 2. Dynamic range compression
            'acompressor=threshold=-20dB:ratio=3:attack=200:release=1000',
            
            # 3. Enhance vocal presence (3-5kHz boost)
            'equalizer=f=4000:width_type=h:width=1000:g=2',
            
            # 4. Subtle reverb for natural room tone
            'aecho=0.8:0.9:40:0.15',
            
            # 5. Remove silence from start/end
            'silenceremove=start_periods=1:start_silence=0.1:start_threshold=0.02:'
            'stop_periods=1:stop_silence=0.1:stop_threshold=0.02',
        ]
        
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-af', ','.join(filters),
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
    
    def process(self, 
               input_path: str,
               output_path: str,
               enhance: bool = True,
               method: str = 'auto') -> Tuple[str, dict]:
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
        
        # Get input info
        audio_in, sr_in = sf.read(input_path)
        duration_in = len(audio_in) / sr_in
        
        # Process based on method
        if method == 'ffmpeg':
            output_path = self.process_ffmpeg(input_path, output_path)
        else:
            # Python processing
            audio_out = self.process_python(audio_in, enhance=enhance)
            sf.write(output_path, audio_out, self.sample_rate)
        
        # Get output info
        audio_out, sr_out = sf.read(output_path)
        duration_out = len(audio_out) / sr_out
        
        # Calculate stats
        stats = {
            'method': method,
            'duration_in': duration_in,
            'duration_out': duration_out,
            'samples_in': len(audio_in),
            'samples_out': len(audio_out),
            'peak_in': float(np.abs(audio_in).max()),
            'peak_out': float(np.abs(audio_out).max()),
            'rms_in': float(np.sqrt(np.mean(audio_in**2))),
            'rms_out': float(np.sqrt(np.mean(audio_out**2))),
        }
        
        return output_path, stats


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
