"""Diff Review Screen - reviews changes before applying sensitive operations."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import (
    Static,
    Input,
    Button,
    DataTable,
    ProgressBar,
    LoadingIndicator,
)
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.binding import Binding
from pathlib import Path
import re


class DiffReviewScreen(Screen):
    """Diff review screen for sensitive changes."""

    BINDINGS = [
        Binding("a", "apply", "Apply"),
        Binding("r", "reject", "Reject"),
        Binding("q", "quit", "Quit"),
        Binding("b", "back", "Back"),
    ]

    def __init__(self, diff_content: str = "", **kwargs):
        super().__init__(**kwargs)
        self.diff_content = diff_content

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="diff-review-container"):
            yield Static("Diff Review - Review Changes Before Applying", id="diff-title")
            yield Static("─" * 60)

            # Diff preview
            with Vertical(id="diff-preview"):
                yield Static(self.diff_content or "[diff content will appear here]",
                           title="Changes Preview",
                           border_style="cyan",
                           subtitle="Review the following changes before applying")

            yield Static("─" * 60)

            # Changed files summary
            with Vertical(id="changed-files"):
                if self.diff_content:
                    # Extract file names from diff
                    files = re.findall(r"diff --git a/(\S+) b/\S+", self.diff_content)
                    yield Static(f"Files changed: {len(files)}", id="files-count")
                    for f in files[:5]:  # Show first 5
                        yield Static(f"  - {f}", id="file-list")
                    if len(files) > 5:
                        yield Static(f"  ... and {len(files) - 5} more", id="file-more")
                else:
                    yield Static("No changes to review", id="no-changes")

            yield Static("─" * 60)

            # Action buttons
            with Horizontal(id="action-buttons"):
                yield Button("Apply Changes", id="apply-btn", variant="primary")
                yield Button("Reject", id="reject-btn")
                yield Button("← Back", id="back-btn")

    def on_mount(self) -> None:
        """Focus the screen."""
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "apply-btn":
            self._apply_changes()
        elif button_id == "reject-btn":
            self.app.pop_screen()
        elif button_id == "back-btn":
            self.app.pop_screen()
        elif button_id == "reject":
            self.app.pop_screen()

    def _apply_changes(self) -> None:
        """Apply the changes (with approval)."""
        self.app.notify("Changes would be applied here (approval required)", severity="information")
        self.app.pop_screen()