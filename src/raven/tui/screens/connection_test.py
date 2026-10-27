"""Connection Test Screen - tests API connections for all agents with demo data labeling."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import (
    Static,
    Input,
    Button,
    ProgressBar,
    LoadingIndicator,
)
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.binding import Binding
from pathlib import Path


class ConnectionTestScreen(Screen):
    """Connection test screen - tests API connections for all agents with demo data."""

    BINDINGS = [
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, agent_configs: list = None, **kwargs):
        super().__init__(**kwargs)
        self.agent_configs = agent_configs or []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="connection-test-container"):
            yield Static("Connection Test", id="connection-title")
            yield Static("─" * 60)

            # Status for each agent
            with Vertical(id="agent-statuses"):
                for i, config in enumerate(self.agent_configs[:5]):
                    provider = config.get("provider", "unknown")
                    model = config.get("model", "unknown")
                    with Horizontal(id=f"agent-{i + 1}-status"):
                        yield Static(f"Agent {i + 1}:", style="bold")
                        yield Static(
                            f" {provider}/{model}",
                            id=f"agent-{i + 1}-info",
                        )

            yield Static("─" * 60)

            # Progress bar
            yield ProgressBar(id="progress-bar", total=len(self.agent_configs))
            yield Static("0/0 tested", id="progress-text")

            yield Static("─" * 60)

            # Results summary
            with Vertical(id="results-summary"):
                yield Static("Results:", id="results-label")
                yield Static(id="results-details")

            yield Static("─" * 60)

            # Action buttons
            with Horizontal(id="action-buttons"):
                yield Button("← Configure", id="back-btn")
                yield Button("Finish", id="finish-btn")

    def on_mount(self) -> None:
        """Run connection tests for all agents."""
        import asyncio

        total = len(self.agent_configs)
        self.query_one("#progress-bar", ProgressBar).total = total

        async def run_tests():
            from textual.containers import Vertical

            results = []

            for i, config in enumerate(self.agent_configs):
                # Update progress
                self.query_one("#progress-text", Static).update(
                    f"{i + 1}/{total} tested"
                )

                provider = config.get("provider", "")
                model = config.get("model", "")

                # Simulate test - in foundation step, always "success" with demo labeling
                await asyncio.sleep(0.5)  # Simulate network delay

                # Demo result - always success for foundation, clearly labeled
                result = {
                    "agent": i + 1,
                    "provider": provider,
                    "model": model,
                    "status": "connected",
                    "message": f"Demo: {provider}/{model} connection successful (no real API tested)",
                }
                results.append(result)

                # Update UI
                agent_box = self.query_one(f"#agent-{i + 1}-status", Vertical)
                # Replace the info static with demo-connected version
                for child in list(agent_box.children):
                    if hasattr(child, "id") and child.id == f"agent-{i + 1}-info":
                        agent_box.remove_child(child)
                        agent_box.append_static(
                            Static(
                                f" {provider}/{model} ✓ Demo",
                                id=f"agent-{i + 1}-info",
                            )
                        )

                # Add result to summary
                self.query_one("#results-details").append(
                    f"Agent {i + 1}: {provider}/{model} - connected (demo)\\n"
                )

            # Complete
            self.query_one("#progress-text", Static).update(
                f"{total}/{total} tested"
            )
            self.query_one("#results-details").append(
                f"\nAll {total} agents connection test complete. (demo data only)\\n"
            )

        asyncio.get_event_loop().create_task(run_tests())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "back-btn":
            self.app.switch_screen("agent_setup")
        elif button_id == "finish-btn":
            self.app.switch_screen("live_workspace")