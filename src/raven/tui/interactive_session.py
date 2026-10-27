"""Interactive Session - terminal-first coding agent REPL.

Implements the user interaction workflow specified in Sections 1, 5, and 6:
- Interactive natural language coding request prompt
- Readable stream of model thoughts, tool calls, and outputs
- Inline approval prompts for sensitive operations
- Task summaries with files changed and test results
- Follow-up conversation support
"""

from __future__ import annotations

import os
import sys
import asyncio
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from ..providers.registry import ProviderRegistry
from ..agents.coding_agent import CodingAgent, AgentTaskReport
from ..tools.coding_tools import ToolExecutionResult


class InteractiveCodingSession:
    """Terminal-based interactive coding session for RAVEN."""

    def __init__(
        self,
        project_root: Optional[str] = None,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.project_root = os.path.abspath(project_root or os.getcwd())
        self.console = Console()
        self.registry = ProviderRegistry(register_defaults=True)
        
        # Determine provider and model
        self.provider_name = provider_name or self._detect_default_provider()
        self.model_name = model_name or self.registry.get_default_model(self.provider_name) or "gpt-4o"
        
        # Instantiate provider
        self.provider_instance = self._create_provider_instance(self.provider_name)
        
        # Create coding agent
        self.agent = CodingAgent(
            provider=self.provider_instance,
            project_root=self.project_root,
            model=self.model_name,
            on_thought=self._display_thought,
            on_tool_call=self._display_tool_call,
            on_tool_result=self._display_tool_result,
            on_approval_required=self._prompt_approval,
        )

    def _detect_default_provider(self) -> str:
        """Detect best available provider based on environment variables."""
        if os.environ.get("OPENAI_API_KEY"):
            return "openai"
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        if os.environ.get("GEMINI_API_KEY"):
            return "gemini"
        if os.environ.get("OPENAI_COMPATIBLE_API_KEY"):
            return "openai_compatible"
        return "openai"

    def _create_provider_instance(self, name: str) -> Any:
        """Create provider instance safely."""
        try:
            return self.registry.create_instance(name)
        except Exception as e:
            # Fallback to Mock or Local if missing
            from ..providers.base import AIProvider, ProviderResult
            
            class SafeFallbackProvider(AIProvider):
                @property
                def default_model(self) -> str:
                    return "fallback-model"
                @property
                def supported_models(self) -> list:
                    return ["fallback-model"]
                async def _get_api_key(self) -> str:
                    return "fallback"
                def _validate_key_format(self, key: str) -> bool:
                    return True
                async def _generate_response_core(self, prompt: str, context: str, model_id: str) -> ProviderResult:
                    return ProviderResult(
                        content="No AI provider credentials are configured. Set your API key (e.g. `set OPENAI_API_KEY=...`) to interact with live models.",
                        model=model_id,
                        provider="fallback",
                    )
            return SafeFallbackProvider({})

    # -------------------------------------------------------------------------
    # UI Display Callbacks
    # -------------------------------------------------------------------------

    def _display_thought(self, text: str) -> None:
        """Render model thought or response text."""
        if not text or not text.strip():
            return
        self.console.print()
        self.console.print(Markdown(text))

    def _display_tool_call(self, name: str, args: Dict[str, Any]) -> None:
        """Display an executing tool invocation card."""
        arg_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        if len(arg_str) > 120:
            arg_str = arg_str[:117] + "..."
        
        icon = "🔧"
        if "test" in name:
            icon = "🧪"
        elif "git" in name:
            icon = "🌿"
        elif "command" in name:
            icon = "⚡"
        elif "write" in name or "edit" in name:
            icon = "✏️"

        self.console.print(f"\n[bold #168CFF]{icon} Tool Call:[/] [bold cyan]{name}[/]({arg_str})")

    def _display_tool_result(self, name: str, result: ToolExecutionResult) -> None:
        """Display the outcome of a tool execution."""
        if result.success:
            snippet = result.output.strip()
            lines = snippet.splitlines()
            if len(lines) > 6:
                display_snippet = "\n".join(lines[:6]) + f"\n... [{len(lines) - 6} more lines]"
            else:
                display_snippet = snippet or "(empty result)"
            self.console.print(f"[bold green]✓ Result:[/] [dim]{display_snippet}[/]")
        else:
            self.console.print(f"[bold red]✗ Failed:[/] [red]{result.error or result.output}[/]")

    def _prompt_approval(self, action: str, details: Dict[str, Any]) -> bool:
        """Ask user approval for sensitive operations."""
        self.console.print(f"\n[bold yellow]⚠️  Approval Required:[/] Action [bold]{action}[/] with {details}")
        try:
            choice = input("Authorize this operation? [y/N]: ").strip().lower()
            return choice in ("y", "yes")
        except (KeyboardInterrupt, EOFError):
            return False

    # -------------------------------------------------------------------------
    # Main Session Run Loop
    # -------------------------------------------------------------------------

    def run(self) -> None:
        """Launch synchronous entry point for the session."""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.console.print("\n[bold cyan]Session closed. Goodbye![/]")

    async def run_async(self) -> None:
        """Interactive REPL loop."""
        self._print_banner()
        self._check_and_print_readiness()

        while True:
            try:
                self.console.print()
                user_input = self.console.input("[bold #168CFF]raven[/][bold white]>[/] ").strip()
                if not user_input:
                    continue

                if user_input.startswith("/"):
                    handled = await self._handle_slash_command(user_input)
                    if handled == "exit":
                        break
                    continue

                # Run coding task
                with self.console.status("[bold cyan]● RAVEN is working on task...[/]", spinner="dots"):
                    report = await self.agent.execute_task(user_input)

                self._print_task_report(report)

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[bold cyan]Session closed. Goodbye![/]")
                break
            except Exception as e:
                self.console.print(f"\n[bold red]Error in session:[/] {e}")

    # -------------------------------------------------------------------------
    # Slash Commands
    # -------------------------------------------------------------------------

    async def _handle_slash_command(self, cmd: str) -> Optional[str]:
        """Process special slash commands."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("/exit", "/quit"):
            self.console.print("[bold cyan]Goodbye![/]")
            return "exit"

        elif command == "/help":
            table = Table(title="RAVEN Commands", box=box.ROUNDED)
            table.add_column("Command", style="cyan")
            table.add_column("Description")
            table.add_row("/help", "Show this help table")
            table.add_row("/status", "Inspect workspace git status")
            table.add_row("/diff", "Inspect uncommitted git diff")
            table.add_row("/doctor", "Check environment and provider health")
            table.add_row("/models", "List supported models")
            table.add_row("/provider <name>", "Switch active provider (e.g. openai, anthropic, gemini, local)")
            table.add_row("/clear", "Clear conversation history")
            table.add_row("/exit", "Exit RAVEN")
            self.console.print(table)

        elif command == "/clear":
            self.agent.reset_history()
            self.console.clear()
            self._print_banner()
            self.console.print("[green]Conversation history cleared.[/]")

        elif command == "/status":
            res = await self.agent.tools.tool_git_status()
            self.console.print(Panel(res.output, title="Git Status", border_style="cyan"))

        elif command == "/diff":
            res = await self.agent.tools.tool_git_diff()
            self.console.print(Panel(res.output, title="Git Diff", border_style="cyan"))

        elif command == "/doctor":
            self._run_doctor()

        elif command == "/models":
            self._list_models()

        elif command == "/provider":
            if not args:
                self.console.print(f"Current provider: [bold]{self.provider_name}[/] ({self.model_name})")
            else:
                new_prov = args.strip().lower()
                if new_prov in self.registry.list_providers():
                    self.provider_name = new_prov
                    self.model_name = self.registry.get_default_model(new_prov) or "default"
                    self.provider_instance = self._create_provider_instance(new_prov)
                    self.agent.provider = self.provider_instance
                    self.agent.model = self.model_name
                    self.console.print(f"[green]Switched provider to {new_prov} (model: {self.model_name})[/]")
                else:
                    self.console.print(f"[red]Unknown provider '{new_prov}'. Available: {self.registry.list_providers()}[/]")

        else:
            self.console.print(f"[yellow]Unknown command '{command}'. Type /help for available commands.[/]")

        return None

    # -------------------------------------------------------------------------
    # Banners and Reports
    # -------------------------------------------------------------------------

    def _print_banner(self) -> None:
        """Render stylish cyberpunk header."""
        header_text = Text()
        header_text.append("RAVEN ", style="bold #168CFF")
        header_text.append("— Terminal AI Coding Agent\n", style="bold white")
        header_text.append(f"Workspace: {self.project_root}\n", style="dim white")
        header_text.append(f"Provider: {self.provider_name} | Model: {self.model_name}\n", style="#842BFF")
        header_text.append("Type your task naturally or '/help' for options.", style="italic gray")

        self.console.print(
            Panel(
                header_text,
                border_style="#168CFF",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def _check_and_print_readiness(self) -> None:
        """Warn user if no API keys are found without crashing."""
        has_key = False
        for env_var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_COMPATIBLE_API_KEY"):
            if os.environ.get(env_var):
                has_key = True
                break

        if not has_key:
            self.console.print(
                Panel(
                    "[bold yellow]Notice: No provider API keys detected in your environment.[/]\n"
                    "To use online models, configure an API key:\n"
                    "  [cyan]$env:OPENAI_API_KEY = 'sk-...'[/]       (OpenAI)\n"
                    "  [cyan]$env:ANTHROPIC_API_KEY = 'sk-ant-...'[/] (Anthropic)\n"
                    "  [cyan]$env:GEMINI_API_KEY = '...'[/]          (Google Gemini)\n"
                    "Or use local models via Ollama with [cyan]/provider local[/].\n"
                    "You can still inspect files and explore tools in this session.",
                    title="Configuration Setup",
                    border_style="yellow",
                    box=box.MINIMAL,
                )
            )

    def _print_task_report(self, report: AgentTaskReport) -> None:
        """Render final outcome report."""
        self.console.print()
        status_style = "bold green" if report.success else "bold red"
        status_text = "Task Succeeded" if report.success else f"Task Ended with Issue"
        
        table = Table(box=box.SIMPLE)
        table.add_column("Metric", style="dim")
        table.add_column("Value")
        
        table.add_row("Status", f"[{status_style}]{status_text}[/]")
        table.add_row("Duration", f"{report.duration_seconds}s ({report.iterations} iterations, {report.tool_calls_count} tool calls)")
        
        if report.changed_files:
            table.add_row("Changed Files", "\n".join(f"[bold cyan]{f}[/]" for f in report.changed_files))
        else:
            table.add_row("Changed Files", "[dim](none)[/]")
            
        if report.tests_run:
            test_summaries = []
            for t in report.tests_run:
                sym = "[green]PASS[/]" if t.get("success") else "[red]FAIL[/]"
                test_summaries.append(f"{sym} {t.get('target')}: {t.get('summary')}")
            table.add_row("Tests Run", "\n".join(test_summaries))

        if report.error:
            table.add_row("Error", f"[red]{report.error}[/]")

        self.console.print(Panel(table, title="Task Summary", border_style="#168CFF", box=box.ROUNDED))

    def _run_doctor(self) -> None:
        """Run system and provider diagnosis."""
        table = Table(title="RAVEN Doctor — System & Provider Health", box=box.ROUNDED)
        table.add_column("Component", style="cyan")
        table.add_column("Status")
        table.add_column("Details")

        table.add_row("Python", "[green]OK[/]", sys.version.split()[0])
        table.add_row("Workspace", "[green]OK[/]", self.project_root)

        # Check Git
        is_git = os.path.isdir(os.path.join(self.project_root, ".git"))
        table.add_row("Git Repository", "[green]OK[/]" if is_git else "[yellow]NO[/]", "Active repo" if is_git else "Not a git repo")

        # Check Providers
        for p in self.registry.list_providers():
            env_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY",
                "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
                "local": None,
            }
            env_key = env_map.get(p)
            has_cred = bool(os.environ.get(env_key)) if env_key else True
            cred_str = "[green]Configured[/]" if has_cred else "[yellow]Missing API Key[/]"
            table.add_row(f"Provider: {p}", cred_str, f"Env: {env_key}" if env_key else "Local inference")

        self.console.print(table)

    def _list_models(self) -> None:
        """List models for current provider."""
        table = Table(title=f"Models for Provider: {self.provider_name}", box=box.ROUNDED)
        table.add_column("Model ID", style="cyan")
        table.add_column("Default")

        try:
            prov_class = self.registry.get(self.provider_name)
            models = getattr(prov_class({}), "supported_models", [self.model_name])
            for m in models:
                is_def = "[bold green]YES[/]" if m == self.model_name else ""
                table.add_row(m, is_def)
        except Exception:
            table.add_row(self.model_name, "[bold green]YES[/]")

        self.console.print(table)
