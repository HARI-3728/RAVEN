"""RAVEN ASCII/Unicode-compatible startup logo for the terminal."""

from __future__ import annotations

# Raw string to avoid escape sequence warnings
RAVEN_LOGO = r"""
  _     _              _ _       _     _ 
 | |   | |            | | |     | |   | |
 | |___| | __ _ _ __ | | | __ _| |__ | |
 | __/ | |/ _` | '_ \| | |/ _` | '_ \| |
 | |_| | | (_| | | | | | | (_| | | | |_|
  \___|_|\__,_|_| |_|_|_|\__,_|_|  \__/
"""

# Raven symbol using ASCII characters
RAVEN_SYMBOL = "RAVEN"

def print_logo():
    """Print the RAVEN logo to terminal."""
    for line in RAVEN_LOGO.split("\n"):
        if line.strip():
            print(line)


def print_logo_small():
    """Print a smaller RAVEN logo."""
    print("RAVEN")