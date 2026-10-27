#!/usr/bin/env python3
"""RAVEN main entry point."""

import sys
from .cli import app as cli_app


def main():
    """Main entry point for RAVEN."""
    try:
        cli_app()
    except KeyboardInterrupt:
        print("\nRAVEN interrupted. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()