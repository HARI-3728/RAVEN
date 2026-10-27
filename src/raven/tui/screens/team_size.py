"""Team Size Screen - selects the number of agents (2, 3, 4, or 5)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Static, Button, Header, Footer
from textual.screen import Screen
from textual.binding import Binding


class TeamSizeScreen(Screen):
    """Team size selection screen."""

    BINDINGS = [
        Binding("1", "select_1", "2 Agents"),
        Binding("2", "select_2", "3 Agents"),
        Binding("3", "select_3", "4 Agents"),
        Binding("4", "select_4", "5 Agents"),
        Binding("q", "quit", "Quit"),
        Binding("b", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Static(id="team-size"):
            yield Static("Select the number of AI agents:", id="team-size-prompt")
            yield Static("─" * 60)
            yield Button("2 Agents", id="btn-2", classes="agent-btn")
            yield Button("3 Agents", id="btn-3", classes="agent-btn")
            yield Button("4 Agents", id="btn-4", classes="agent-btn")
            yield Button("5 Agents", id="btn-5", classes="agent-btn")
            yield Static("─" * 40)
            yield Static("Press the number key or button below", id="hint")

    def on_mount(self) -> None:
        """Focus the screen and apply keyboard focus to first button."""
        # Focus the 2 Agents button by default
        self.query_one("#btn-2", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-2":
            self.app.team_size = 2
            self.app.switch_screen("agent_setup")
        elif button_id == "btn-3":
            self.app.team_size = 3
            self.app.switch_screen("agent_setup")
        elif button_id == "btn-4":
            self.app.team_size = 4
            self.app.switch_screen("agent_setup")
        elif button_id == "btn-5":
            self.app.team_size = 5
            self.app.switch_screen("agent_setup")

    def action_select_1(self) -> None:
        """Select 2 agents (key '1')."""
        self.app.team_size = 2
        self.app.switch_screen("agent_setup")

    def action_select_2(self) -> None:
        """Select 3 agents (key '2')."""
        self.app.team_size = 3
        self.app.switch_screen("agent_setup")

    def action_select_3(self) -> None:
        """Select 4 agents (key '3')."""
        self.app.team_size = 4
        self.app.switch_screen("agent_setup")

    def action_select_4(self) -> None:
        """Select 5 agents (key '4')."""
        self.app.team_size = 5
        self.app.switch_screen("agent_setup")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_back(self) -> None:
        """Go back to project setup."""
        self.app.switch_screen("project_setup")