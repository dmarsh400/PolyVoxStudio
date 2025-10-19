# GPU Compatibility Guide

## Which Installation Should I Use?

| GPU Series | Compute Capability | Installation | CUDA Version | PyTorch Version |
|------------|-------------------|--------------|--------------|-----------------|
| **RTX 40 series** (4090, 4080, 4070) | 8.9 | Standard | 12.1 | 2.1+ |
| **RTX 30 series** (3090, 3080, 3070) | 8.6 | Standard | 12.1 | 2.1+ |
| **RTX 20 series** (2080 Ti, 2080, 2070) | 7.5 | Standard | 12.1 | 2.1+ |
| **GTX 16 series** (1660 Ti, 1650) | 7.5 | Standard | 12.1 | 2.1+ |
| **GTX 10 series** (1080 Ti, 1070, 1060) | 6.1 | **Legacy** | 11.6 | 1.13 |
| **GTX 900 series** (980 Ti, 980, 970) | 5.2 | **Legacy** | 11.6 | 1.13 |
| **GTX 700 series** (780 Ti, 780, 770) | 3.5 | **Legacy** | 11.6 | 1.13 |
| **Tesla K80** | 3.7 | **Legacy** | 11.6 | 1.13 |
| **Tesla K40** | 3.5 | **Legacy** | 11.6 | 1.13 |
| **Quadro K6000** | 3.5 | **Legacy** | 11.6 | 1.13 |

## Quick Decision Tree

```
Do you have an NVIDIA GPU?
├─ Yes
│  ├─ Is it RTX 20xx or newer?
│  │  ├─ Yes → Use STANDARD installation
│  │  └─ No → Continue
│  │
│  ├─ Is it GTX 16xx series?
│  │  ├─ Yes → Use STANDARD installation
│  │  └─ No → Continue
│  │
│  └─ Is it GTX 10xx or older?
│     └─ Yes → Use LEGACY installation
│
└─ No GPU or AMD GPU → Use STANDARD installation (CPU mode)
```

## Check Your GPU

### Linux
```bash
nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader
```

### Windows
```batch
nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader
```

### Python
```python
import torch
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Compute Capability: {torch.cuda.get_device_capability(0)}")
```

## Installation Commands

### Standard Installation
```bash
# Linux/Mac
./install.sh  # or python install.py

# Windows
install.bat  # or python install.py
```

### Legacy GPU Installation
```bash
# Linux/Mac
./install_legacy_gpu.sh

# Windows
install_legacy_gpu.bat
```

## Performance Comparison

### Character Detection (per chapter)
| Environment | RTX 3080 | GTX 1080 | K80 | CPU |
|------------|----------|----------|-----|-----|
| Time | 30-60s | 1-2 min | 2-5 min | 5-10 min |

### Voice Generation (per minute of audio)
| Environment | RTX 3080 | GTX 1080 | K80 | CPU |
|------------|----------|----------|-----|-----|
| Time | 15-30s | 30-60s | 1-2 min | 5-10 min |
| Real-time Factor | 2-4x | 1-2x | 0.5-1x | 0.1-0.2x |

*Real-time Factor: 1x means it takes 1 minute to generate 1 minute of audio*

## Known Limitations

### Legacy Installation
- **Cannot use latest TTS features** - Stuck on TTS 0.17.0
- **No PyTorch 2.x optimizations** - Missing performance improvements
- **Limited model support** - Some newer models won't work
- **Older dependencies** - May have unpatched bugs

### When to Use CPU Mode Instead
Consider CPU mode if:
- You have a very old GPU (pre-Kepler, compute capability < 3.5)
- GPU drivers cannot be updated
- You're getting persistent CUDA errors
- You don't mind slower processing

Enable CPU mode:
1. Open Settings tab
2. Toggle off "Use GPU"
3. Restart the application

## Mixing Environments

You can install both and switch between them:

```bash
# Use modern environment
conda activate epub
python app/main.py

# Use legacy environment  
conda activate vox_legacy
python app/main.py
```

Both environments share the same project files and settings!

## Driver Requirements

| GPU Series | Minimum Driver | Recommended |
|------------|----------------|-------------|
| RTX 40xx | 522.06 | Latest |
| RTX 30xx | 465.19 | Latest |
| RTX 20xx | 418.96 | Latest |
| GTX 16xx | 418.96 | Latest |
| GTX 10xx | 450.80.02 | 470.x |
| GTX 900 | 450.80.02 | 470.x |
| GTX 700 | 450.80.02 | 470.x |
| K80/K40 | 450.80.02 | 470.x |

## Still Having Issues?

1. **Check the Debug tab** in the app for error messages
2. **Review installation logs** - saved in the installation directory
3. **Try CPU mode** as a fallback
4. **Open an issue on GitHub** with:
   - GPU model and compute capability
   - Driver version (`nvidia-smi`)
   - Full error message from Debug tab
   - Installation method used (standard or legacy)
