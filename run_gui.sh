#!/usr/bin/env bash
# Launch PolyVox Studio using the local PolyVox virtual environment.
set -euo pipefail

export TRANSFORMERS_NO_TF=1
export TRANSFORMERS_NO_JAX=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="${SCRIPT_DIR}/PolyVox"

if [ ! -d "${ENV_DIR}" ]; then
  echo "❌ PolyVox environment not found at ${ENV_DIR}. Run ./install_linux.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_DIR}/bin/activate"

python -m app.main
