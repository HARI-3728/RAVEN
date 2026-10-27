#!/usr/bin/env python3
"""RAVEN Textual application - main terminal UI."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Dict, Any, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    Header,
    Footer,
    Static,
)
from textual.containers import Vertical
from textual.screen import Screen
from textual.reactive import reactive

from .screens import (
    WelcomeScreen,
    ProjectSetupScreen,
    TeamSizeScreen,
    AgentSetupScreen,
    ConnectionTestScreen,
    LiveExecutionScreen,
    AgentDetailsScreen,
    CustomRoleEditorScreen,
    DiffReviewScreen,
    SettingsScreen,
)


class RavenApp(App):
    """Main RAVEN Textual application."""

    # Screen bindings - global across all screens
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "configure", "Configure"),
        Binding("s", "start", "Start Agents"),
        Binding("p", "pause", "Pause"),
        Binding("r", "resume", "Resume"),
        Binding("t", "tasks", "View Tasks"),
        Binding("h", "help", "Help"),
    ]

    # Reactive state
    team_size = reactive(2)
    agent_configs = reactive([])
    agents_running = reactive(False)
    selected_agent = reactive(None)
    project_root = reactive("")
    show_help = reactive(False)

    def __init__(self, **kwargs):
        """Initialize the RAVEN application."""
        super().__init__(**kwargs)
        self.db = None
        self.orchestrator = None
        self.event_bus = None
        self.current_screen = "welcome"
        self.showing_loader = False
        self.help_text = self._get_help_text()

    def _get_help_text(self) -> str:
        """Get help overlay text."""
        return (
            "[bold]Keyboard Shortcuts[/]\n"
            "  q: Quit          c: Configure    s: Start    p: Pause    r: Resume\n"
            "  h: Help        ↑/↓: Navigate   Enter: Submit\\n"
            "  ?: Toggle help overlay"
        )

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield Footer()

        with Vertical(id="main-container"):
            # Left panel - Agent status
            with Vertical(id="left-panel"):
                yield Static("Agents", id="agent-header")
                yield Static("No team configured", id="agent-list")
                yield Static("", id="status-bar")

            # Right panel - Main content area
            with Vertical(id="right-panel"):
                yield Static(
                    "[bold #168CFF]RAVEN[/]\n"
                    "[italic Multi-AI Development Workspace][/]\n"
                    "\n"
                    "[bold #842BFF]🖤💙💜[/]\n"
                    "\n"
                    "[dim Press 'c' to configure agents or 'q' to quit][/]",
                    id="welcome-content",
                    classes="welcome-content",
                )

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Push the welcome screen
        self.push_screen(WelcomeScreen())

        # Initialize event bus
        from ..core.event_bus import EventBus
        self.event_bus = EventBus()

        # Apply initial updates
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """Update the status bar text."""
        try:
            status = self.query_one("#status-bar", Static)
            status.update(
                f"RAVEN v0.1.0 | Team: {self.team_size} agents | Status: {'Running' if self.agents_running else 'Ready'}"
            )
        except Exception:
            pass

    def switch_screen(self, screen_name: str) -> None:
        """Switch to a different named screen by pushing it."""
        screen_map = {
            "welcome": WelcomeScreen(),
            "project_setup": ProjectSetupScreen(),
            "team_size": TeamSizeScreen(),
            "agent_setup": AgentSetupScreen(team_size=self.team_size),
            "connection_test": ConnectionTestScreen(
                agent_configs=self.agent_configs or []
            ),
            "live_execution": LiveExecutionScreen(
                agent_configs=self.agent_configs or []
            ),
            "agent_details": AgentDetailsScreen(),
            "custom_role_editor": CustomRoleEditorScreen(),
            "diff_review": DiffReviewScreen(),
            "settings": SettingsScreen(),
        }
        screen = screen_map.get(screen_name)
        if screen:
            self.push_screen(screen)
            self.current_screen = screen_name
            self._update_status_bar()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_configure(self) -> None:
        """Switch to configuration flow."""
        if self.team_size >= 2:
            self.switch_screen("project_setup")
        else:
            self.notify("Please set team size to 2-5 agents first", severity="warning")

    def action_start(self) -> None:
        """Start agent execution."""
        if self.team_size >= 2 and self.agent_configs:
            self.switch_screen("connection_test")
        elif not self.agent_configs:
            self.notify("Please configure agents first", severity="warning")
        else:
            self.switch_screen("connection_test")

    def action_pause(self) -> None:
        """Pause agent execution."""
        if self.agents_running:
            self.agents_running = False
            self.notify("Execution paused", severity="info")

    def action_resume(self) -> None:
        """Resume agent execution."""
        if not self.agents_running:
            self.agents_running = True
            self.notify("Execution resumed", severity="info")

    def action_tasks(self) -> None:
        """View tasks."""
        self.switch_screen("live_execution")

    def action_help(self) -> None:
        """Toggle help overlay."""
        self.show_help = not self.show_help
        self.notify(
            "Help: q=quit, c=configure, s=start, p=pause, r=resume, t=tasks",
            severity="information",
        )
