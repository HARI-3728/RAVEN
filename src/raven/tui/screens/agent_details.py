"""Agent Details Screen - inspects selected agent's status and output."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import (
    Static,
    Input,
    Button,
    Select,
    Header,
    Footer,
)
from textual.screen import Screen
from textual.binding import Binding


class AgentDetailsScreen(Screen):
    """Agent details and output inspection screen."""

    BINDINGS = [
        Binding("c", "close", "Close"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, agent_id: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.agent_id = agent_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="agent-details-container"):
            # Agent header
            with Horizontal(id="agent-header"):
                yield Static(f"Agent {self.agent_id}", id="agent-title", style="bold")
                yield Button("← Close", id="close-btn")

            # Agent info panel
            with Panel(
                Static(
                    "Provider: OpenAI\n"
                    "Model: gpt-4o\n"
                    "Role: Developer\n"
                    "Status: Online\n"
                    "Tasks Completed: 3\n"
                    "Last Activity: 2 minutes ago",
                    id="agent-info",
                ),
                title=f"Agent {self.agent_id} Details",
                border_style="cyan",
            ):
                pass

            # Divider
            yield Static("─" * 60)

            # Output/Logs section
            with Static("Agent Output Log", id="output-label"):
                yield Static(
                    "[dim]No output yet. Start execution to see agent activity.[/]",
                    id="output-content",
                )

            # Divider
            yield Static("─" * 60)

            # Action buttons
            with Horizontal(id="detail-action-buttons"):
                yield Button("Refresh", id="refresh-btn")
                yield Button("Close", id="close-detail-btn")

    def on_mount(self) -> None:
        """Focus the screen."""
        self.query_one("#close-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id in ("close-btn", "close-detail-btn"):
            self.app.pop_screen()
        elif button_id == "refresh-btn":
            self._refresh_output()

    def _refresh_output(self) -> None:
        """Refresh the agent output display."""
        # In foundation, just show placeholder with demo label
        self.query_one("#output-content", Static).update(
            "[dim]Output will appear here when agent executes tasks. (demo data)[/]"
        )