#!/usr/bin/env python3
"""RAVEN main entry point."""

import sys
import asyncio

from typer import Typer, run

from .cli import app as cli_app

cli_app.add_typer(
    Typer(name="raven"),
    name="",
    help="RAVEN multi-AI development workspace",
)


def main():
    """Main entry point for RAVEN."""
    try:
        cli_app()
    except KeyboardInterrupt:
        print("\nRAVEN interrupted. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()