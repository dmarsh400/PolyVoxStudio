#!/usr/bin/env bash
# PolyVox Studio Linux installer
# Creates a dedicated virtual environment named "PolyVox" and installs
# dependencies, including the appropriate PyTorch wheel for legacy GPUs.

set -euo pipefail

ENV_NAME="PolyVox"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="${PROJECT_ROOT}/${ENV_NAME}"
PYTHON_BIN="${PYTHON:-python3}"

choose_torch_runtime() {
  cat <<'EOT'
Select the PyTorch runtime for your GPU:
  [1] CUDA 11.8  (legacy NVIDIA cards / driver >= 520)
  [2] CUDA 12.1  (recent NVIDIA cards / driver >= 535)
  [3] CUDA 12.8  (RTX 50-series Blackwell / driver >= 570)
  [4] CPU only   (no NVIDIA GPU)
EOT
  local choice
  read -rp "Enter choice [1-4] (default 1): " choice || choice=""
  case "${choice}" in
    2)
      TORCH_SUFFIX="cu121"
      TORCH_VERSION="2.1.0"
      TORCHVISION_VERSION="0.16.0"
      TORCHAUDIO_VERSION="2.1.0"
      TORCH_INDEX="https://download.pytorch.org/whl/cu121"
      ;;
    3)
      TORCH_SUFFIX="cu128"
      TORCH_VERSION="2.7.0"
      TORCHVISION_VERSION="0.22.0"
      TORCHAUDIO_VERSION="2.7.0"
      TORCH_INDEX="https://download.pytorch.org/whl/cu128"
      ;;
    4)
      TORCH_SUFFIX="cpu"
      TORCH_VERSION="2.1.0"
      TORCHVISION_VERSION="0.16.0"
      TORCHAUDIO_VERSION="2.1.0"
      TORCH_INDEX="https://download.pytorch.org/whl/cpu"
      ;;
    *)
      TORCH_SUFFIX="cu118"
      TORCH_VERSION="2.1.0"
      TORCHVISION_VERSION="0.16.0"
      TORCHAUDIO_VERSION="2.1.0"
      TORCH_INDEX="https://download.pytorch.org/whl/cu118"
      ;;
  esac
}

ensure_python() {
  if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "❌ Python executable '${PYTHON_BIN}' not found. Set PYTHON=/path/to/python3 and re-run." >&2
    exit 1
  fi
  local version
  version="$("${PYTHON_BIN}" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  local major minor
  major="${version%%.*}"
  minor="${version##*.}"
  if (( major < 3 || (major == 3 && minor < 9) )); then
    echo "❌ Python 3.9 or higher is required (found ${version})." >&2
    exit 1
  fi
}

create_env() {
  if [ -d "${ENV_DIR}" ]; then
    echo "⚠️  Existing environment detected at ${ENV_DIR}."
    read -rp "Recreate it? This will delete the current environment. [y/N]: " reply || reply=""
    if [[ "${reply}" =~ ^[Yy]$ ]]; then
      rm -rf "${ENV_DIR}"
    else
      echo "Using existing environment." >&2
      return
    fi
  fi
  "${PYTHON_BIN}" -m venv "${ENV_DIR}"
}

activate_env() {
  # shellcheck disable=SC1090
  source "${ENV_DIR}/bin/activate"
  python -m pip install --upgrade pip setuptools wheel
}

install_torch() {
  echo "\n📦 Installing PyTorch ${TORCH_VERSION} (${TORCH_SUFFIX})"
  python -m pip install \
    "torch==${TORCH_VERSION}+${TORCH_SUFFIX}" \
    "torchvision==${TORCHVISION_VERSION}+${TORCH_SUFFIX}" \
    "torchaudio==${TORCHAUDIO_VERSION}+${TORCH_SUFFIX}" \
    --index-url "${TORCH_INDEX}"
}

install_requirements() {
  echo "\n📦 Installing core PolyVox dependencies"
  python -m pip install -r "${PROJECT_ROOT}/requirements_min.txt"
  echo "\n📚 Downloading spaCy language model (en_core_web_md)"
  python -m spacy download en_core_web_md
}

post_install_notes() {
  cat <<EOT

✅ PolyVox environment ready!

Activate manually with:
  source "${ENV_DIR}/bin/activate"

Launch the UI with:
  ./run_gui.sh

If you haven't installed system packages yet, make sure ffmpeg and tesseract
are available (Debian/Ubuntu example):
  sudo apt-get install ffmpeg tesseract-ocr
EOT
}

main() {
  echo "==========================================="
  echo " PolyVox Studio Linux Installer"
  echo "==========================================="

  ensure_python
  choose_torch_runtime
  create_env
  activate_env
  install_torch
  install_requirements
  post_install_notes
}

main "$@"
