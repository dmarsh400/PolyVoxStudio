#!/bin/bash
# VOX Audiobook Generator - Legacy GPU Installation (K80, GTX 700/900 series, etc.)
# This script installs compatible versions for older NVIDIA GPUs with CUDA compute capability 3.5-5.2
# Supports: K80, GTX 780, GTX 980, GTX 1050, etc.

set -e

echo "========================================="
echo "VOX Audiobook Generator - Legacy GPU Setup"
echo "For NVIDIA K80 and older GPUs"
echo "========================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Check for conda/mamba
if command -v mamba &> /dev/null; then
    CONDA_CMD="mamba"
    echo "Using mamba for faster package management"
elif command -v conda &> /dev/null; then
    CONDA_CMD="conda"
    echo "Using conda for package management"
else
    echo "ERROR: Neither conda nor mamba found!"
    echo "Please install Miniconda or Anaconda first:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo ""
echo "Step 1: Creating conda environment 'vox_legacy'..."
echo "----------------------------------------------"
$CONDA_CMD create -n vox_legacy python=3.9 -y

echo ""
echo "Step 2: Installing PyTorch 1.13 with CUDA 11.6 (K80 compatible)..."
echo "----------------------------------------------------------------"
# PyTorch 1.13 is the last version with good CUDA 11.6 support for older GPUs
$CONDA_CMD install -n vox_legacy pytorch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 pytorch-cuda=11.6 -c pytorch -c nvidia -y

echo ""
echo "Step 3: Installing TTS (Coqui-ai) for legacy GPU..."
echo "---------------------------------------------------"
$CONDA_CMD run -n vox_legacy pip install TTS==0.17.0

echo ""
echo "Step 4: Installing core dependencies..."
echo "---------------------------------------"
$CONDA_CMD run -n vox_legacy pip install \
    numpy==1.23.5 \
    scipy==1.10.1 \
    librosa==0.10.0 \
    soundfile \
    pydub \
    matplotlib \
    customtkinter \
    pillow \
    sounddevice

echo ""
echo "Step 5: Installing NLP dependencies..."
echo "--------------------------------------"
$CONDA_CMD run -n vox_legacy pip install \
    spacy==3.5.0 \
    transformers==4.30.0 \
    sentencepiece

# Install spaCy English model
$CONDA_CMD run -n vox_legacy python -m spacy download en_core_web_sm

echo ""
echo "Step 6: Installing BookNLP (character detection)..."
echo "--------------------------------------------------"
$CONDA_CMD run -n vox_legacy pip install booknlp==1.0.7

echo ""
echo "Step 7: Installing additional utilities..."
echo "-----------------------------------------"
$CONDA_CMD run -n vox_legacy pip install \
    ebooklib \
    charset-normalizer \
    ffmpeg-python

echo ""
echo "Step 8: Verifying installation..."
echo "--------------------------------"

# Test PyTorch and CUDA
echo "Testing PyTorch and CUDA..."
$CONDA_CMD run -n vox_legacy python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU device: {torch.cuda.get_device_name(0)}')
    print(f'Compute capability: {torch.cuda.get_device_capability(0)}')
else:
    print('WARNING: CUDA not available. Will use CPU mode.')
"

# Test TTS
echo ""
echo "Testing TTS installation..."
$CONDA_CMD run -n vox_legacy python -c "
from TTS.api import TTS
print('TTS imported successfully')
print('Available models:')
print(TTS.list_models()[:5])  # Show first 5 models
"

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "To use the legacy GPU environment:"
echo ""
if [[ "$OS" == "windows" ]]; then
    echo "  conda activate vox_legacy"
    echo "  python app/main.py"
else
    echo "  conda activate vox_legacy"
    echo "  python app/main.py"
fi
echo ""
echo "Or use the launcher script:"
if [[ "$OS" == "windows" ]]; then
    echo "  run_gui_legacy.bat"
else
    echo "  ./run_gui_legacy.sh"
fi
echo ""
echo "NOTE: This environment uses:"
echo "  - PyTorch 1.13.1 with CUDA 11.6"
echo "  - TTS 0.17.0"
echo "  - Compatible with K80, GTX 700/900/1000 series"
echo ""
echo "If you still get GPU errors, you may need to:"
echo "  1. Update NVIDIA drivers to 450.80.02 or newer"
echo "  2. Or use CPU mode by disabling GPU in Settings"
echo ""
