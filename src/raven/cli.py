#!/usr/bin/env python3
"""RAVEN CLI commands using Typer."""

import os
import sys
from typing import Optional
from typer import Typer, Option, Argument, Context, Exit

app = Typer(name="raven", help="RAVEN - Terminal AI Coding Agent & Multi-Model Workspace", no_args_is_help=False)


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
    """RAVEN - Terminal AI Coding Agent.

    Run without arguments to start the interactive coding session.
    """
    if ctx.invoked_subcommand is None:
        start_interactive()


def start_interactive(provider: Optional[str] = None, model: Optional[str] = None):
    """Start the interactive coding agent session."""
    from .tui.interactive_session import InteractiveCodingSession
    try:
        session = InteractiveCodingSession(
            project_root=os.getcwd(),
            provider_name=provider,
            model_name=model,
        )
        session.run()
    except KeyboardInterrupt:
        print("\nSession ended. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting RAVEN session: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise Exit(1)


@app.command("start", help="Start the interactive RAVEN coding session")
def start(
    provider: Optional[str] = Option(None, "--provider", "-p", help="Provider to use (e.g. openai, anthropic, gemini, local)"),
    model: Optional[str] = Option(None, "--model", "-m", help="Model identifier to use"),
    tui: bool = Option(False, "--tui", help="Launch the multi-pane Textual dashboard interface instead"),
):
    """Start RAVEN in the current workspace."""
    if tui:
        from .tui.app import RavenApp
        try:
            raven_tui = RavenApp()
            raven_tui.run()
        except Exception as e:
            print(f"Error starting RAVEN TUI: {e}", file=sys.stderr)
            raise Exit(1)
    else:
        start_interactive(provider=provider, model=model)


@app.command("run", help="Run a single non-interactive coding task and exit")
def run_task(
    task: str = Argument(..., help="The natural-language coding task to execute"),
    provider: Optional[str] = Option(None, "--provider", "-p", help="Provider to use"),
    model: Optional[str] = Option(None, "--model", "-m", help="Model identifier to use"),
    yes: bool = Option(False, "--yes", "-y", help="Automatically approve safe file modifications"),
):
    """Execute a single coding task from the command line."""
    import asyncio
    from rich.console import Console
    from .tui.interactive_session import InteractiveCodingSession
    from .agents.coding_agent import CodingAgent

    console = Console()
    session = InteractiveCodingSession(
        project_root=os.getcwd(),
        provider_name=provider,
        model_name=model,
    )

    if yes:
        # Auto-approve actions
        session.agent.on_approval_required = lambda act, det: True

    console.print(f"[bold cyan]RAVEN executing task:[/] {task}")
    console.print(f"[dim]Provider: {session.provider_name} | Model: {session.model_name}[/]\n")

    async def _execute():
        with console.status("[bold cyan]● Working on task...[/]", spinner="dots"):
            return await session.agent.execute_task(task)

    report = asyncio.run(_execute())
    session._print_task_report(report)

    if not report.success:
        raise Exit(1)


@app.command("doctor", help="Diagnose installation, configuration, and provider readiness")
def doctor():
    """Run diagnostics to verify installation and provider readiness."""
    import platform
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from .providers.registry import ProviderRegistry

    console = Console()
    console.print(Panel.fit("[bold #168CFF]RAVEN Diagnostic Health Check[/]", border_style="cyan"))

    # System table
    sys_table = Table(title="Environment & System", box=box.ROUNDED)
    sys_table.add_column("Check", style="cyan")
    sys_table.add_column("Status")
    sys_table.add_column("Details", style="dim")

    # Python version
    py_ver = platform.python_version()
    sys_table.add_row("Python Version", "[green]✓ PASS[/]" if sys.version_info >= (3, 10) else "[red]✗ FAIL[/]", py_ver)

    # Workspace
    cwd = os.getcwd()
    is_writable = os.access(cwd, os.W_OK)
    sys_table.add_row("Workspace Writable", "[green]✓ PASS[/]" if is_writable else "[red]✗ FAIL[/]", cwd)

    # Git repository
    git_dir = os.path.join(cwd, ".git")
    has_git = os.path.exists(git_dir)
    sys_table.add_row("Git Repository", "[green]✓ PASS[/]" if has_git else "[yellow]! NOT DETECTED[/]", "Initialized" if has_git else "Run `git init`")

    console.print(sys_table)

    # Providers table
    prov_table = Table(title="AI Providers & Credentials", box=box.ROUNDED)
    prov_table.add_column("Provider", style="cyan")
    prov_table.add_column("API Key / Env Var", style="magenta")
    prov_table.add_column("Status")
    prov_table.add_column("Default Model", style="dim")

    registry = ProviderRegistry(register_defaults=True)
    providers = [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("openai_compatible", "OPENAI_COMPATIBLE_API_KEY"),
        ("local", "OLLAMA_HOST (optional)"),
    ]

    any_active = False
    for prov_name, env_var in providers:
        default_model = registry.get_default_model(prov_name) or "default"
        if prov_name == "local":
            prov_table.add_row(prov_name, env_var, "[green]✓ AVAILABLE (Local)[/]", default_model)
            any_active = True
        else:
            has_key = bool(os.environ.get(env_var))
            if has_key:
                any_active = True
                status = "[green]✓ CONFIGURED[/]"
            else:
                status = "[yellow]! NOT SET[/]"
            prov_table.add_row(prov_name, env_var, status, default_model)

    console.print(prov_table)

    if not any_active:
        console.print("\n[bold yellow]Notice:[/] No AI provider API keys detected in your environment.")
        console.print("To use RAVEN with cloud models, export one of the keys:")
        console.print("  [cyan]$env:OPENAI_API_KEY=\"sk-...\"[/]        (PowerShell)")
        console.print("  [cyan]$env:ANTHROPIC_API_KEY=\"sk-ant-...\"[/] (PowerShell)")
        console.print("  [cyan]$env:GEMINI_API_KEY=\"AIza...\"[/]       (PowerShell)")
        console.print("Or use a local model via Ollama with [cyan]raven --provider local[/].\n")
    else:
        console.print("\n[bold green]✓ RAVEN is ready for coding tasks![/]\n")


@app.command("models", help="List available providers and models")
def models():
    """List configured providers and available models."""
    from rich.console import Console
    from rich.table import Table
    from rich import box
    from .providers.registry import ProviderRegistry

    console = Console()
    registry = ProviderRegistry(register_defaults=True)

    table = Table(title="Supported Providers and Models", box=box.ROUNDED)
    table.add_column("Provider", style="bold cyan")
    table.add_column("Default Model", style="green")
    table.add_column("Available Models", style="dim")
    table.add_column("Credentials Set", style="magenta")

    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
        "local": "None required (Ollama)",
    }

    for prov in registry.list_providers():
        default_m = registry.get_default_model(prov) or "default"
        supported_m = ", ".join(registry.get_supported_models(prov)[:4])
        env_var = env_map.get(prov, "N/A")
        is_set = "✓ Yes" if prov == "local" or (env_var in os.environ and os.environ[env_var]) else "✗ No"
        table.add_row(prov, default_m, supported_m, is_set)

    console.print(table)


@app.command("config", help="Inspect active RAVEN configuration")
def config():
    """Display active workspace and agent configuration."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()
    table = Table(title="Active Configuration", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Project Root", os.getcwd())
    table.add_row("Default Provider", os.environ.get("RAVEN_DEFAULT_PROVIDER", "openai"))
    table.add_row("Default Model", os.environ.get("RAVEN_DEFAULT_MODEL", "gpt-4o"))
    table.add_row("Max Loop Iterations", os.environ.get("RAVEN_MAX_ITERATIONS", "15"))
    table.add_row("Loop Timeout (sec)", os.environ.get("RAVEN_TIMEOUT", "300"))
    table.add_row("Safety Approvals Required", "True (destructive edits & commands)")

    console.print(table)


@app.command("init", help="Initialize a new RAVEN workspace")
def init(
    project_dir: str = Option(".", help="Project directory path"),
):
    """Initialize a new RAVEN workspace with sample configuration."""
    from pathlib import Path
    
    project_path = Path(project_dir).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    
    raven_dir = project_path / ".raven"
    raven_dir.mkdir(exist_ok=True)
    
    config_file = raven_dir / "config.json"
    if not config_file.exists():
        import json
        default_cfg = {
            "version": "0.1.0",
            "provider": "openai",
            "model": "gpt-4o",
            "max_iterations": 15,
            "security": {
                "require_approval_for_commands": True,
                "require_approval_for_writes": False,
            }
        }
        config_file.write_text(json.dumps(default_cfg, indent=2), encoding="utf-8")
        print(f"Created configuration at: {config_file}")
    
    print(f"RAVEN workspace initialized at: {project_path}")
    print("Run `raven` to start an interactive coding session.")


@app.command("version", help="Show RAVEN version")
def version():
    """Show the RAVEN version."""
    from .version import __version__
    print(f"RAVEN version {__version__}")


if __name__ == "__main__":
    app()