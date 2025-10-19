# Legacy GPU Installation Guide

## For Older NVIDIA GPUs (K80, GTX 700/900/1000 series)

If you're getting errors about your GPU being too old or unsupported compute capability, use this alternative installation method.

## Supported GPUs

This installation works with older NVIDIA GPUs that have CUDA compute capability 3.5 - 5.2:

- **Tesla K-series**: K80, K40, K20
- **GeForce GTX 700**: GTX 780 Ti, GTX 780, GTX 770, GTX 760
- **GeForce GTX 900**: GTX 980 Ti, GTX 980, GTX 970, GTX 960
- **GeForce GTX 1000**: GTX 1050, GTX 1050 Ti (partial support)

## What's Different?

The legacy installation uses:
- **PyTorch 1.13.1** (instead of 2.x) - Last version with good support for older GPUs
- **CUDA 11.6** (instead of 12.x) - Compatible with Kepler/Maxwell architecture
- **TTS 0.17.0** (instead of latest) - Stable version that works with older PyTorch

## Installation

### Linux/macOS

```bash
# Run the legacy installation script
./install_legacy_gpu.sh

# After installation, launch with:
./run_gui_legacy.sh
```

### Windows

```batch
REM Run the legacy installation script
install_legacy_gpu.bat

REM After installation, launch with:
run_gui_legacy.bat
```

## Installation Time

- With fast internet: 5-10 minutes
- First time setup includes downloading:
  - PyTorch with CUDA 11.6 (~2GB)
  - TTS models
  - NLP libraries

## Requirements

### Minimum System Requirements
- **NVIDIA GPU**: Compute capability 3.5 or higher
- **NVIDIA Driver**: 450.80.02 or newer (Linux) / 452.39 or newer (Windows)
- **CUDA**: Will be installed automatically via conda
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space for environment and models

### Check Your GPU

To verify your GPU compute capability:

**Linux:**
```bash
nvidia-smi --query-gpu=compute_cap --format=csv
```

**Windows:**
```batch
nvidia-smi --query-gpu=compute_cap --format=csv
```

## Driver Updates

If you get "driver too old" errors:

### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nvidia-driver-470

# Or use the graphics-drivers PPA for newer versions
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update
sudo apt install nvidia-driver-470
```

### Windows
Download from: https://www.nvidia.com/Download/index.aspx

Look for **Game Ready Driver 452.39 or newer** for your GPU model.

## Troubleshooting

### "CUDA out of memory" errors
The K80 has 12GB VRAM, but if you get memory errors:
1. In the GUI, go to Settings
2. Reduce "GPU Batch Size" to 1 or 2
3. Close other GPU-intensive applications

### Still not working?
If CUDA still doesn't work after driver update:
1. Open the app
2. Go to Settings tab
3. Disable "Use GPU" toggle
4. The app will use CPU mode (slower but works everywhere)

## Performance Expectations

### K80 Performance (approximate)
- Character detection: ~2-5 minutes per chapter
- Voice generation: ~1-2 minutes per minute of audio
- Real-time factor: 0.5-1.0x (2 minutes to generate 1 minute of audio)

### CPU Mode Performance
- Character detection: ~5-10 minutes per chapter  
- Voice generation: ~5-10 minutes per minute of audio
- Real-time factor: 0.1-0.2x (10 minutes to generate 1 minute of audio)

## Switching Between Environments

You can have both the modern and legacy environments installed:

```bash
# Use modern environment (RTX 2000+)
conda activate epub
python app/main.py

# Use legacy environment (K80, GTX 900, etc.)
conda activate vox_legacy
python app/main.py
```

## Uninstalling

To remove the legacy environment:

```bash
conda env remove -n vox_legacy
```

## Need Help?

If you're still having issues:
1. Check the Debug tab in the app for error messages
2. Run with verbose output:
   ```bash
   conda activate vox_legacy
   python app/main.py --verbose
   ```
3. Open an issue on GitHub with:
   - Your GPU model
   - NVIDIA driver version (`nvidia-smi`)
   - Python version
   - Error messages from the Debug tab

## Advanced: JIT Compilation

The legacy installation uses standard PyTorch JIT compilation which works automatically. For K80 specifically, PyTorch will compile kernels for compute capability 3.7 the first time they're used. This adds a small delay (1-2 minutes) on first run but subsequent runs will be faster.

To pre-compile for your GPU:
```python
import torch
torch.cuda.set_device(0)  # Use first GPU
torch.backends.cudnn.benchmark = True  # Enable auto-tuning
```

This is already enabled in the VOX application code.
