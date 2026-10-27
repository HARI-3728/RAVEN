"""Project Setup Screen - selects the project directory."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Button, Header, Footer
from textual.screen import Screen
from textual.binding import Binding
from pathlib import Path


class ProjectSetupScreen(Screen):
    """Project directory selection screen."""

    BINDINGS = [
        Binding("c", "continue", "Continue"),
        Binding("q", "quit", "Quit"),
        Binding("b", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Static(id="project-setup"):
            yield Static("Select your project directory:", id="project-prompt")
            yield Input(".", id="project-path", placeholder="/path/to/project")
            yield Horizontal(
                Button("Browse", id="browse-btn"),
                Button("Skip", id="skip-btn"),
            )

    def on_mount(self) -> None:
        """Focus the path input."""
        self.query_one("#project-path", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "browse-btn":
            self.app.notify("Browse not implemented in foundation step", severity="information")
        elif button_id == "skip-btn":
            self.app.screen.continue_action()

    def action_continue(self) -> None:
        """Continue to team size selection."""
        project_path = self.query_one("#project-path", Input).value.strip()
        if not project_path:
            self.app.notify("Please enter a project path", severity="warning")
            return

        # Validate path exists
        path = Path(project_path).resolve()
        if not path.exists():
            self.app.notify(f"Path does not exist: {project_path}", severity="error")
            return

        # Save project root and move to team size
        self.app.project_root = str(path)
        self.app.switch_screen("team_size")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_back(self) -> None:
        """Go back to welcome screen."""
        self.app.switch_screen("welcome")