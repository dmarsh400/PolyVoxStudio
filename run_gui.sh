#!/usr/bin/env bash
# Launch PolyVox Studio using the local PolyVox virtual environment.
set -euo pipefail

export TRANSFORMERS_NO_TF=1
export TRANSFORMERS_NO_JAX=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR_DEFAULT="${SCRIPT_DIR}/PolyVox"
ENV_DIR="${POLYVOX_ENV_DIR:-$ENV_DIR_DEFAULT}"
CONDA_ENV="${POLYVOX_CONDA_ENV:-}"

use_conda_env() {
  if ! command -v conda >/dev/null 2>&1; then
    echo "❌ Requested conda environment '${CONDA_ENV}' but conda is not installed or not on PATH." >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  eval "$(conda shell.bash hook)"
  conda activate "${CONDA_ENV}"
}

if [ -d "${ENV_DIR}" ]; then
  # shellcheck disable=SC1090
  source "${ENV_DIR}/bin/activate"
elif [ -n "${CONDA_ENV}" ]; then
  use_conda_env
elif [ -n "${VIRTUAL_ENV:-}" ]; then
  echo "ℹ️ Using already active virtual environment at ${VIRTUAL_ENV}" >&2
elif [ -n "${CONDA_PREFIX:-}" ]; then
  echo "ℹ️ Using active conda environment ${CONDA_DEFAULT_ENV:-$(basename "${CONDA_PREFIX}")}" >&2
else
  echo "❌ PolyVox environment not found at ${ENV_DIR}." >&2
  echo "   Activate your environment first (e.g. 'conda activate epub') or set POLYVOX_ENV_DIR/POLYVOX_CONDA_ENV." >&2
  echo "   You can also run './install_linux.sh' to create the default PolyVox virtualenv." >&2
  exit 1
fi

python -m app.main
