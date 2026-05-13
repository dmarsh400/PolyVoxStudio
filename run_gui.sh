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
PYTHON_CMD=""

use_conda_env() {
  if ! command -v conda >/dev/null 2>&1; then
    echo "❌ Requested conda environment '${CONDA_ENV}' but conda is not installed or not on PATH." >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  eval "$(conda shell.bash hook)"
  conda activate "${CONDA_ENV}"
}

find_missing_dependencies() {
  "${PYTHON_CMD}" - <<'PY'
import importlib.util

checks = {
    "Pillow (PIL)": "PIL",
    "spaCy": "spacy",
    "PyTorch": "torch",
    "CustomTkinter": "customtkinter",
}

missing = [name for name, module in checks.items() if importlib.util.find_spec(module) is None]
print(", ".join(missing))
PY
}

check_python_dependencies() {
  local missing
  missing="$(find_missing_dependencies)"

  if [ -z "${missing}" ]; then
    return
  fi

  echo "ℹ️ Missing required Python modules: ${missing}" >&2
  echo "   Attempting automatic repair from requirements_min.txt..." >&2
  if "${PYTHON_CMD}" -m pip install -r "${SCRIPT_DIR}/requirements_min.txt" --upgrade; then
    missing="$(find_missing_dependencies)"
  fi

  if [ -n "${missing}" ]; then
    echo "❌ Missing required Python modules: ${missing}" >&2
    echo "   Your environment looks incomplete." >&2
    echo "   Recommended fix: run './install_linux.sh' and let it finish." >&2
    echo "   Advanced fix: activate this environment and run 'python -m pip install -r requirements_min.txt --upgrade'." >&2
    exit 1
  fi
}

if [ -d "${ENV_DIR}" ]; then
  PYTHON_CMD="${ENV_DIR}/bin/python"
  if [ ! -x "${PYTHON_CMD}" ]; then
    echo "❌ Python executable not found at ${PYTHON_CMD}." >&2
    echo "   Re-run './install_linux.sh' to rebuild the default environment." >&2
    exit 1
  fi
elif [ -n "${CONDA_ENV}" ]; then
  use_conda_env
  PYTHON_CMD="python"
elif [ -n "${VIRTUAL_ENV:-}" ]; then
  echo "ℹ️ Using already active virtual environment at ${VIRTUAL_ENV}" >&2
  PYTHON_CMD="python"
elif [ -n "${CONDA_PREFIX:-}" ]; then
  echo "ℹ️ Using active conda environment ${CONDA_DEFAULT_ENV:-$(basename "${CONDA_PREFIX}")}" >&2
  PYTHON_CMD="python"
else
  echo "❌ PolyVox environment not found at ${ENV_DIR}." >&2
  echo "   Activate your environment first (e.g. 'conda activate epub') or set POLYVOX_ENV_DIR/POLYVOX_CONDA_ENV." >&2
  echo "   You can also run './install_linux.sh' to create the default PolyVox virtualenv." >&2
  exit 1
fi

echo "ℹ️ Using Python: $("${PYTHON_CMD}" -c 'import sys; print(sys.executable)')" >&2

check_python_dependencies

"${PYTHON_CMD}" -m app.main
