#!/bin/bash
# Try to activate conda if available; tolerate missing conda.sh
if [ -f "$HOME/miniconda/etc/profile.d/conda.sh" ]; then
  source "$HOME/miniconda/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
fi

# Activate env if possible
if command -v conda >/dev/null 2>&1; then
  conda activate epub_adv 2>/dev/null || true
fi

# Run the GUI with splash screen
python -m app.main
