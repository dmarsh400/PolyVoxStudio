#!/bin/bash
# Launcher for VOX Audiobook Generator (Legacy GPU Environment)

# Activate the legacy GPU environment
source ~/miniconda/etc/profile.d/conda.sh 2>/dev/null || source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null

if ! conda activate vox_legacy 2>/dev/null; then
    echo "ERROR: vox_legacy environment not found!"
    echo "Please run ./install_legacy_gpu.sh first"
    exit 1
fi

echo "Starting VOX Audiobook Generator (Legacy GPU Mode)..."
echo "Using environment: vox_legacy"
echo ""

# Run the application
python app/main.py
