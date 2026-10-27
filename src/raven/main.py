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
        asyncio.run(_arun())
    except KeyboardInterrupt:
        print("\nRAVEN interrupted. Goodbye!")
        sys.exit(0)


async def _arun():
    """Async main entry point."""
    # Start the CLI application
    cli_app()


if __name__ == "__main__":
    main()