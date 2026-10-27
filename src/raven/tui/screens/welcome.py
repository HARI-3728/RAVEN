"""Welcome Screen - displays RAVEN name, ASCII logo, and startup options."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Static, Button, Header, Footer
from textual.screen import Screen
from textual.binding import Binding


class WelcomeScreen(Screen):
    """Welcome screen shown at application start."""

    BINDINGS = [
        Binding("c", "configure", "Configure"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Static(id="welcome-content", classes="welcome-content"):
            pass

    def on_mount(self) -> None:
        """Display welcome content with RAVEN logo and theme."""
        content = self.query_one("#welcome-content", Static)

        # Build the welcome message with RAVEN logo and theme colors
        logo_lines = [
            "  _     _              _ _       _     _ ",
            " | |   | |            | | |     | |   | |",
            " | |___| | __ _ _ __ | | | __ _| |__ | |",
            " | __/ | |/ _` | '_ \\| | |/ _` | '_ \\| |",
            " | |_| | | (_| | | | | | | (_| | | | |_|",
            "  \\___|_|\\__,_|_| |_|_|_|\\__,_|_|  \\__/",
        ]

        lines = [
            "[bold #168CFF]RAVEN[/]",
            "",
            "[italic Multi-AI Development Workspace]",
            "",
            "[bold #842BFF]🖤💙💜[/]",
            "",
            "[dim Press 'c' to configure agents or 'q' to quit / 홈 화면]",
        ]

        # Combine logo and message
        full_render = "\n".join(lines)

        # Add the ASCII logo as a preview (truncated for foundation step)
        content.update(
            f"{full_render}\\n\\n"
            f"[dim]{'\\n'.join(logo_lines[:4])}[/]\\n"
            f"[dim  dim](RAVEN - Multi-AI Development Workspace for terminal)[/]"
        )

        # Trigger a re-render to show the updated content
        self.refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "configure":
            self.app.switch_screen("project_setup")
        elif button_id == "quit":
            self.app.exit()