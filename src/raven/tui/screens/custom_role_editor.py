"""Custom Role Editor - allows users to define custom roles for agents."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import (
    Input,
    Button,
    Select,
    Static,
)
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.binding import Binding


class CustomRoleEditor(Screen):
    """Custom role editor for defining new agent roles."""

    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("c", "cancel", "Cancel"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, existing_roles: list = None, **kwargs):
        super().__init__(**kwargs)
        self.existing_roles = existing_roles or []
        self.new_role_name = ""
        self.new_role_instructions = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="custom-role-editor-container"):
            yield Static("Custom Role Editor", id="editor-title")
            yield Static("─" * 60)

            # Role name input
            with Horizontal(id="role-name-row"):
                yield Static("Role Name:", id="role-name-label")
                yield Input(
                    "custom-role",
                    id="role-name-input",
                    placeholder="e.g. developer, reviewer, tester",
                    disabled=True,  # Could allow custom entry
                )

            # Custom instructions input
            with Horizontal(id="role-instructions-row"):
                yield Static("Instructions:", id="role-instructions-label")
                yield Input(
                    "",
                    id="role-instructions-input",
                    placeholder="Enter custom instructions for this role...",
                    expand=True,
                )

            # Role suggestions based on team size
            yield Static("Suggested roles for your team:", id="suggestions-label")
            with Vertical(id="suggestions-list"):
                for role_label, role_value in [
                    ("Developer", "developer"),
                    ("Reviewer", "reviewer"),
                    ("Tester", "tester"),
                    ("Analyst", "analyst"),
                    ("Architect", "architect"),
                ]:
                    yield Button(
                        role_label,
                        id=f"suggest-{role_value}",
                        classes="suggestion-btn",
                    )

            yield Static("─" * 60)

            # Action buttons
            with Horizontal(id="action-buttons"):
                yield Button("Use This Role", id="use-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus the role name input."""
        self.query_one("#role-name-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id.startswith("suggest-"):
            role_value = button_id.replace("suggest-", "")
            # Auto-fill the role name input
            try:
                role_input = self.query_one("#role-name-input", Input)
                role_input.value = role_value
                role_input.disabled = False
            except Exception:
                pass

        elif event.button.id == "use-btn":
            self._save_custom_role()

        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    def _save_custom_role(self) -> None:
        """Save the custom role and close the screen."""
        role_input = self.query_one("#role-name-input", Input)
        instructions_input = self.query_one(
            "#role-instructions-input", Input
        )

        role_name = role_input.value.strip() if role_input else ""
        instructions = instructions_input.value.strip() if instructions_input else ""

        if role_name:
            # Add to existing roles and notify
            if role_name not in self.existing_roles:
                self.existing_roles.append(role_name)
            self.app.notify(
                f"Custom role '{role_name}' saved", severity="information"
            )
            self.app.pop_screen()
        else:
            self.app.notify("Please enter a role name", severity="warning")