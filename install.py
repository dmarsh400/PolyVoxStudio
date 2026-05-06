"""Deprecated installer placeholder.

PolyVox Studio now ships with dedicated platform-specific installers:

  • Linux: ./install_linux.sh
  • Windows: .\install_windows.ps1

This file remains only to point older documentation at the new workflow.
"""

import sys


def main() -> None:
    message = (
        "PolyVox Studio now uses dedicated installers.\n\n"
        "• Linux users: run ./install_linux.sh\n"
        "• Windows users: run .\\install_windows.ps1\n\n"
        "These scripts create the PolyVox virtual environment, install the\n"
        "correct PyTorch wheel for your GPU (including older CUDA runtimes),\n"
        "and fetch the remaining dependencies automatically.\n"
    )
    sys.stdout.write(message)


if __name__ == "__main__":
    main()
