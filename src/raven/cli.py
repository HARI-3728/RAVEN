#!/usr/bin/env python3
"""RAVEN CLI commands using Typer."""

from typer import Typer, Option, Argument, Context, Exit

app = Typer(name="raven", help="RAVEN multi-AI development workspace")


def version_callback(value: bool):
    if value:
        from .version import __version__
        print(f"RAVEN version {__version__}")
        raise Exit()


@app.callback(invoke_without_command=True)
def default_callback(
    ctx: Context,
    version: bool = Option(
        False,
        "--version",
        "-v",
        help="Show RAVEN version and exit",
        callback=version_callback,
        is_eager=True,
    ),
):
    """RAVEN multi-AI development workspace."""
    if ctx.invoked_subcommand is None:
        start()

@app.command("init", help="Initialize a new RAVEN workspace")
def init(
    project_dir: str = Option(".", help="Project directory path"),
    num_agents: int = Option(2, help="Number of agents (2-5)"),
):
    """Initialize a new RAVEN workspace with the given configuration."""
    import os
    from pathlib import Path
    
    project_path = Path(project_dir).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Initializing RAVEN workspace at: {project_path}")
    print(f"Number of agents: {num_agents}")
    
    # TODO: Create initial configuration files
    # TODO: Set up SQLite database
    # TODO: Show welcome screen
    
    print("Workspace initialization complete.")
    print("Use 'raven configure' to set up agents and providers.")


@app.command("configure", help="Configure RAVEN workspace agents and providers")
def configure():
    """Configure agents, providers, and roles."""
    print("Configuration interface coming soon...")
    print("Use the TUI or follow interactive prompts.")


@app.command("start", help="Start the RAVEN TUI application")
def start():
    """Start the RAVEN Textual terminal application."""
    from .tui.app import RavenApp
    import asyncio
    
    app = RavenApp()
    app.run()


@app.command("version", help="Show RAVEN version")
def version():
    """Show the RAVEN version."""
    from .version import __version__
    print(f"RAVEN version {__version__}")


if __name__ == "__main__":
    app()