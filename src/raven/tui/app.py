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
    Input,
    Button,
    LoadingIndicator,
    TabbedContent,
    TabPane,
    Static,
)
from textual.containers import Vertical, Horizontal, Container
from textual.screen import Screen
from textual.reactive import reactive

from raven.cli import app as cli_app


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
    is_running = reactive(False)
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

        with Horizontal():
            # Left panel - Agent panel / help overlay
            with Vertical(id="left-panel"):
                yield Static(id="agent-header", renderable="Agents")
                yield Static(id="agent-list", renderable="No team configured")
                yield Static(id="status-bar", renderable="")

                # Help overlay (initially hidden)
                if self.show_help:
                    yield Static(
                        self.help_text,
                        id="help-overlay",
                        classes="help-overlay",
                    )

            # Right panel - Main content area with tabs
            with Vertical(id="right-panel"):
                yield TabbedContent(
                    (
                        "Welcome",
                        WelcomeScreen(),
                    ),
                    (
                        "Project Setup",
                        ProjectSetupScreen(),
                    ),
                    (
                        "Team Size",
                        TeamSizeScreen(),
                    ),
                    (
                        "Agent Setup",
                        AgentSetupScreen(team_size=self.team_size),
                    ),
                    (
                        "Connection Test",
                        ConnectionTestScreen(
                            agent_configs=self.agent_configs or []
                        ),
                    ),
                    (
                        "Live Execution",
                        LiveExecutionScreen(
                            agent_configs=self.agent_configs or []
                        ),
                    ),
                    (
                        "Task Input",
                        TaskInputScreen(),
                    ),
                    (
                        "Agent Details",
                        AgentDetailsScreen(),
                    ),
                    (
                        "Diff Review",
                        DiffReviewScreen(),
                    ),
                    (
                        "Settings",
                        SettingsScreen(),
                    ),
                )

        # Bottom status bar
        yield Static(
            f"RAVEN v0.1.0 | Background: #080A12 | Electric Blue: #168CFF | Purple: #842BFF",
            id="bottom-status-bar",
        )

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Set up initial screen
        self.switch_screen("welcome")

        # Initialize event bus
        from .event_bus import TUIEventBus
        self.event_bus = TUIEventBus()

        # Apply theme and initial updates
        self.query_one("#bottom-status-bar", Static).update(
            f"RAVEN v0.1.0 | Team: {self.team_size} agents | Status: Ready"
        )

    def switch_screen(self, screen_name: str) -> None:
        """Switch to a different screen tab."""
        tabbed = self.query_one(TabbedContent)
        if tabbed:
            tabbed.active = screen_name
            self.current_screen = screen_name

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
        if self.is_running:
            self.is_running = False
            self.notify("Execution paused", severity="info")

    def action_resume(self) -> None:
        """Resume agent execution."""
        if not self.is_running:
            self.is_running = True
            self.notify("Execution resumed", severity="info")

    def action_tasks(self) -> None:
        """View tasks."""
        self.switch_screen("task_input")

    def action_help(self) -> None:
        """Toggle help overlay."""
        self.show_help = not self.show_help
        # Refresh the compose to show/hide help
        self.refresh()

    def show_loader(self, show: bool = True) -> None:
        """Show or hide the loading indicator."""
        self.showing_loader = show
        for widget in self.query():
            if type(widget).__name__ == "LoadingIndicator":
                widget.display = show

    def on_screen_change(self) -> None:
        """Called when screen tab changes."""
        # Refresh the current panel content
        tabbed = self.query_one(TabbedContent)
        screen_name = tabbed.active
        panel = tabbed.get_panel(screen_name)
        if panel and hasattr(panel, "on_mount"):
            try:
                panel.on_mount()
            except Exception:
                pass


# Screen classes - simplified for foundation


class WelcomeScreen(Static):
    """Welcome screen shown at application start."""

    def on_mount(self) -> None:
        """Display welcome content."""
        self.update(
            "[bold #168CFF]RAVEN[/]\n"
            "[italic Multi-AI Development Workspace]\n"
            "\n"
            "[bold #842BFF]🖤💙💜[/]\n"
            "\n"
            "[dim Press 'c' to configure agents or 'q' to quit][/]"
        )


class ProjectSetupScreen(Static):
    """Project setup screen."""

    def on_mount(self) -> None:
        self.update(
            "[bold]Project Setup[/]\n\n"
            "Please select your project directory:\n"
            "[input]Project path[/] "
            '<input id="project-path" placeholder="/path/to/project">\n\n'
            "[button]Browse[/]  [button]Skip[/]"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "browse-btn":
            self.app.notify("Browse not implemented in foundation step", severity="information")
        elif button_id == "skip-btn":
            self.app.screen.continue_action()

    def action_continue(self) -> None:
        project_path = self.query_one("#project-path", Input).value.strip()
        if not project_path:
            self.app.notify("Please enter a project path", severity="warning")
            return
        path = __import__("pathlib").Path(project_path).resolve()
        if not path.exists():
            self.app.notify(f"Path does not exist: {project_path}", severity="error")
            return
        self.app.project_root = str(path)
        self.app.switch_screen("team_size")

    def action_quit(self) -> None:
        self.app.exit()

    def action_back(self) -> None:
        self.app.switch_screen("welcome")


class TeamSizeScreen(Static):
    """Team size selection screen."""

    def on_mount(self) -> None:
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
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
        self.app.team_size = 2
        self.app.switch_screen("agent_setup")

    def action_select_2(self) -> None:
        self.app.team_size = 3
        self.app.switch_screen("agent_setup")

    def action_select_3(self) -> None:
        self.app.team_size = 4
        self.app.switch_screen("agent_setup")

    def action_select_4(self) -> None:
        self.app.team_size = 5
        self.app.switch_screen("agent_setup")

    def action_quit(self) -> None:
        self.app.exit()

    def action_back(self) -> None:
        self.app.switch_screen("project_setup")


class AgentSetupScreen(Static):
    """Agent configuration screen."""

    def __init__(self, team_size: int = 2, **kwargs):
        super().__init__(**kwargs)
        self.team_size = team_size
        self.agent_configs = []

    def on_mount(self) -> None:
        """Initialize agent configurations and focus."""
        self.agent_configs = []
        for i in range(self.team_size):
            self.agent_configs.append(
                {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "role": "developer",
                    "instructions": "Write clean, maintainable code.",
                }
            )
        # Re-compose with agent cards
        self._recompose_cards()

    def _recompose_cards(self) -> None:
        """Re-compose the agent cards based on current team_size."""
        # Get the container and rebuild
        container = self.query_one("#agent-setup-container", Vertical)
        # Clear existing children (except header and title)
        # For foundation, just update the status bar
        try:
            status_bar = self.query_one("#status-bar", Static)
            status_bar.update(
                f"Team size: {self.team_size} agents | Configure below"
            )
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for agent configuration."""
        input_id = event.input.id
        parts = input_id.split("-")
        if len(parts) >= 2 and parts[0].startswith("agent"):
            agent_num = int(parts[0].replace("agent", ""))
            field = parts[1]

            if 1 <= agent_num <= self.team_size:
                agent_idx = agent_num - 1
                if field == "provider":
                    self.agent_configs[agent_idx]["provider"] = event.value
                elif field == "model":
                    self.agent_configs[agent_idx]["model"] = event.value
                elif field == "role":
                    try:
                        select_widget = self.query_one(f"#agent{agent_num}-role", Select)
                        self.agent_configs[agent_idx]["role"] = select_widget.value
                    except Exception:
                        pass
                elif field == "instructions":
                    self.agent_configs[agent_idx]["instructions"] = event.value

                # Enable test button if provider is set
                test_btn_id = f"test-btn-agent-{agent_num}"
                try:
                    test_btn = self.query_one(f"#{test_btn_id}", Button)
                    test_btn.disabled = self.agent_configs[agent_idx]["provider"] == ""
                except Exception:
                    pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle role selection changes."""
        select_id = event.select.id
        parts = select_id.split("-")
        if len(parts) >= 2 and parts[0].startswith("agent"):
            agent_num = int(parts[0].replace("agent", ""))
            if 1 <= agent_num <= self.team_size:
                agent_idx = agent_num - 1
                self.agent_configs[agent_idx]["role"] = event.value
                test_btn_id = f"test-btn-agent-{agent_num}"
                try:
                    test_btn = self.query_one(f"#{test_btn_id}", Button)
                    test_btn.disabled = self.agent_configs[agent_idx]["provider"] == ""
                except Exception:
                    pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id.startswith("test-btn-"):
            agent_num = int(button_id.replace("test-btn-", ""))
            if 1 <= agent_num <= self.team_size:
                config = self.agent_configs[agent_num - 1]
                self._test_agent_connection(agent_num, config)

        elif event.button.id == "save-btn":
            self._save_agent_configs()

        elif event.button.id == "prev-btn":
            self.app.switch_screen("team_size")

        elif event.button.id == "quit-btn":
            self.app.exit()

    def _test_agent_connection(self, agent_num: int, config: dict) -> None:
        """Test the AI provider connection for an agent."""
        provider = config.get("provider", "")
        self.app.show_loader(True)
        import asyncio
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
        self.app.show_loader(False)
        self.app.notify(
            f"Connection test for Agent {agent_num} ({provider}): Demo mode - no real API tested",
            severity="information",
        )

    def _save_agent_configs(self) -> None:
        """Save all agent configurations and move to next screen."""
        all_valid = True
        for i, config in enumerate(self.agent_configs):
            if not config.get("provider") or not config.get("model"):
                all_valid = False
                self.app.notify(
                    f"Agent {i + 1} missing provider or model",
                    severity="error",
                )
        if all_valid:
            self.app.agent_configs = self.agent_configs
            self.app.switch_screen("connection_test")

    def action_save(self) -> None:
        self._save_agent_configs()

    def action_quit(self) -> None:
        self.app.exit()

    def action_back(self) -> None:
        self.app.switch_screen("team_size")


class LiveExecutionScreen(Static):
    """Live workspace screen with agent panels, activity feed, task board, and command input."""

    def __init__(self, agent_configs: list = None, **kwargs):
        super().__init__(**kwargs)
        self.agent_configs = agent_configs or []
        self.is_running = True
        self.current_agent_index = 0

    def on_mount(self) -> None:
        """Focus the command input."""
        self.query_one("#command-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        self.action_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "execute-btn":
            self.action_submit()

    def action_submit(self) -> None:
        """Submit the command from the input field."""
        command_input = self.query_one("#command-input", Input)
        command = command_input.value.strip()
        if not command:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.query_one("#bottom-status", Static).update(
            f"[{timestamp}] Command: {command}"
        )
        self._simulate_agent_activity(command)
        command_input.value = ""
        command_input.focus()

    def _simulate_agent_activity(self, command: str) -> None:
        """Simulate agent activity for demonstration."""
        async def activity_loop():
            try:
                status_text = self.query_one("#status-text", Static)
                status_text.update("Processing")
            except Exception:
                pass
            import asyncio
            await asyncio.sleep(1)
            try:
                status_text = self.query_one("#status-text", Static)
                status_text.update("Idle")
                status_dot = self.query_one("#status-dot", Static)
                status_dot.renderable = "●"
                status_dot.styles = {"style": "green"}
            except Exception:
                pass
            try:
                activity_log = self.query_one("#activity-log-scroll", VerticalScroll)
                timestamp = datetime.now().strftime("%H:%M:%S")
                agent_num = (self.current_agent_index % len(self.agent_configs)) + 1 if self.agent_configs else 1
                activity_log.append(
                    f"[{timestamp}] Agent {agent_num} processing: {command[:50]}..."
                )
            except Exception:
                pass
            self.current_agent_index = (self.current_agent_index + 1) % len(self.agent_configs) if self.agent_configs else 0
        asyncio.get_event_loop().create_task(activity_loop())

    def action_pause(self) -> None:
        """Pause execution."""
        self.is_running = False
        try:
            status_dot = self.query_one("#status-dot", Static)
            status_dot.renderable = "⏸️"
            status_text = self.query_one("#status-text", Static)
            status_text.update("Paused")
        except Exception:
            pass

    def action_resume(self) -> None:
        """Resume execution."""
        self.is_running = True
        try:
            status_dot = self.query_one("#status-dot", Static)
            status_dot.renderable = "●"
            status_dot.styles = {"style": "green"}
            status_text = self.query_one("#status-text", Static)
            status_text.update("Running")
        except Exception:
            pass

    def action_stop(self) -> None:
        """Stop execution."""
        self.is_running = False
        try:
            status_dot = self.query_one("#status-dot", Static)
            status_dot.renderable = "●"
            status_dot.styles = {"style": "red"}
            status_text = self.query_one("#status-text", Static)
            status_text.update("Stopped")
            self.app.notify("Execution stopped (demo mode)", severity="warning")
        except Exception:
            pass

    def action_inspect(self) -> None:
        """Inspect selected agent."""
        self.app.notify("Agent inspection - select agent in UI", severity="information")

    def action_tasks(self) -> None:
        """Show task board (already visible in tab)."""
        pass

    def action_logs(self) -> None:
        """Show logs tab (already visible in tabs)."""
        pass


class TaskInputScreen(Static):
    """Task input and monitoring screen."""

    def on_mount(self) -> None:
        self.update(
            "[bold]Task Input[/]\n\n"
            "Enter tasks for the agents to execute:\n"
            '[input]Task description[/] '
            '<input id="task-desc" placeholder="Describe the task">\n\n'
            "[button]Add Task[/]  [button]Cancel[/]\n\n"
            "[panel]Task list[/]"
        )


class AgentDetailsScreen(Static):
    """Agent details and inspection screen."""

    def __init__(self, agent_id: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.agent_id = agent_id

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
        self.query_one("#output-content", Static).update(
            "[dim]Output will appear here when agent executes tasks. (demo data)[/]"
        )


class DiffReviewScreen(Static):
    """Diff review screen for sensitive changes."""

    def __init__(self, diff_content: str = "", **kwargs):
        super().__init__(**kwargs)
        self.diff_content = diff_content

    def on_mount(self) -> None:
        """Focus the screen."""
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "apply-btn":
            self._apply_changes()
        elif button_id == "reject-btn" or button_id == "back-btn":
            self.app.pop_screen()

    def _apply_changes(self) -> None:
        """Apply the changes (with approval)."""
        self.app.notify("Changes would be applied here", severity="information")
        self.app.pop_screen()


class SettingsScreen(Static):
    """Settings screen for application preferences and configuration."""

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