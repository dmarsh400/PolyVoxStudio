"""
Audio post-processor for enhancing TTS output quality.
Applies normalization and quality improvements to generated audio.
"""
import os
import subprocess
import logging

logger = logging.getLogger(__name__)


class AudioPostProcessor:
    """Post-processes audio files to enhance quality."""
    
    def __init__(self):
        """Initialize the audio post-processor."""
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            logger.warning("[AudioPostProcessor] FFmpeg not found. Audio enhancement disabled.")
    
    def _check_ffmpeg(self):
        """Check if FFmpeg is available on the system."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def enhance_audio(self, input_path, output_path):
        """
        Enhance audio quality using FFmpeg filters.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save enhanced audio
        """
        if not os.path.exists(input_path):
            logger.error(f"[AudioPostProcessor] Input file not found: {input_path}")
            return
        
        # If FFmpeg is not available or input/output are the same, skip enhancement
        if not self.ffmpeg_available or input_path == output_path:
            logger.debug("[AudioPostProcessor] Skipping enhancement (FFmpeg unavailable or in-place edit)")
            return
        
        try:
            # Apply audio filters:
            # - highpass: Remove low-frequency rumble
            # - lowpass: Remove high-frequency noise
            # - dynaudnorm: Dynamic audio normalization
            # - loudnorm: EBU R128 loudness normalization
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-af", "highpass=f=80,lowpass=f=10000,dynaudnorm=f=150:g=15",
                "-ar", "22050",  # Resample to 22.05kHz (standard for TTS)
                "-ac", "1",      # Convert to mono
                "-y",            # Overwrite output
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"[AudioPostProcessor] Enhanced: {output_path}")
            else:
                logger.warning(f"[AudioPostProcessor] Enhancement failed: {result.stderr.decode()}")
                # If enhancement fails, copy original file
                if input_path != output_path:
                    import shutil
                    shutil.copy2(input_path, output_path)
                    
        except subprocess.TimeoutExpired:
            logger.error("[AudioPostProcessor] FFmpeg timeout - audio file may be too large")
        except Exception as e:
            logger.error(f"[AudioPostProcessor] Enhancement error: {e}")
            # On error, copy original file if needed
            if input_path != output_path and os.path.exists(input_path):
                import shutil
                shutil.copy2(input_path, output_path)
    
    def normalize_volume(self, input_path, output_path, target_db=-20.0):
        """
        Normalize audio volume to target dB level.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save normalized audio
            target_db: Target loudness in dB (default: -20.0)
        """
        if not self.ffmpeg_available:
            logger.warning("[AudioPostProcessor] FFmpeg not available for normalization")
            return
        
        try:
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-af", f"loudnorm=I={target_db}:TP=-1.5:LRA=11",
                "-ar", "22050",
                "-y",
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=30)
            logger.info(f"[AudioPostProcessor] Normalized volume: {output_path}")
            
        except Exception as e:
            logger.error(f"[AudioPostProcessor] Volume normalization error: {e}")
