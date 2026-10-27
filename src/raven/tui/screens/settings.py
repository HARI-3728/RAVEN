"""Settings Screen - application settings and preferences (foundation step)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import (
    Static,
    Input,
    Select,
    Switch,
    Button,
    Horizontal,
    Vertical,
)
from textual.screen import Screen
from textual.binding import Binding


class SettingsScreen(Screen):
    """Settings screen for application preferences and configuration."""

    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("c", "close", "Close"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="settings-container"):
            yield Static("Settings", id="settings-title")
            yield Static("─" * 60)

            # Appearance section
            with Vertical(id="appearance-settings"):
                yield Static("Theme Color:", id="theme-label")
                yield Select(
                    [("Electric Blue", "electric_blue"), ("Purple", "purple"), ("Dark", "dark")],
                    value="electric_blue",
                    id="theme-select",
                )
                yield Static("Terminal Font:", id="font-label")
                yield Input("Fira Code", id="font-input", placeholder="Font family name")

            # Behavior section
            with Vertical(id="behavior-settings"):
                yield Static("Auto-save configurations:", id="autosave-label")
                yield Switch(value=True, id="autosave-switch")
                yield Static("Confirm destructive operations:", id="confirm-label")
                yield Switch(value=True, id="confirm-switch")

            # AI Provider section
            with Vertical(id="providers-settings"):
                yield Static("Default provider timeout (seconds):", id="timeout-label")
                yield Input("60", id="timeout-input", placeholder="timeout in seconds")
                yield Static("Max retries:", id="retries-label")
                yield Input("2", id="retries-input", placeholder="max retry attempts")

            yield Static("─" * 60)

            # Action buttons
            with Horizontal(id="action-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Reset", id="reset-btn")
                yield Button("Close", id="close-btn")

    def on_mount(self) -> None:
        """Focus the screen."""
        self.query_one("#save-btn", Button).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "save-btn":
            self._save_settings()
        elif button_id == "reset-btn":
            self._reset_settings()
        elif button_id == "close-btn":
            self.app.pop_screen()

    def _save_settings(self) -> None:
        """Save settings."""
        self.app.notify("Settings saved", severity="information")
        self.app.pop_screen()

    def _reset_settings(self) -> None:
        """Reset settings to defaults."""
        self.app.notify("Settings reset to defaults", severity="information")