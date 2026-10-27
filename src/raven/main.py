#!/usr/bin/env python3
"""RAVEN main entry point."""

import sys
import os

# Configure UTF-8 encoding for Windows terminals to avoid cp1252 UnicodeEncodeError
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from .cli import app as cli_app


def main():
    """Main entry point for RAVEN."""
    try:
        cli_app()
    except KeyboardInterrupt:
        print("\nRAVEN interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"RAVEN fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()