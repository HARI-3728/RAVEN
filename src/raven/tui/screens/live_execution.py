"""Live Execution Screen - shows agent activity, task board, and command input."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import (
    Static,
    Input,
    Button,
    ProgressBar,
    LoadingIndicator,
    DataTable,
    TabbedContent,
    TabPane,
)
from textual.containers import (
    Vertical,
    Horizontal,
)
from textual.screen import Screen
from textual.binding import Binding
from datetime import datetime


class LiveExecutionScreen(Screen):
    """Live workspace screen with agent panels, activity feed, task board, and command input."""

    BINDINGS = [
        Binding("p", "pause", "Pause"),
        Binding("r", "resume", "Resume"),
        Binding("s", "stop", "Stop"),
        Binding("i", "inspect", "Inspect Agent"),
        Binding("t", "tasks", "Task Board"),
        Binding("l", "logs", "Logs"),
        Binding("q", "quit", "Quit"),
        Binding("enter", "submit", "Submit Command"),
    ]

    def __init__(self, agent_configs: list = None, **kwargs):
        super().__init__(**kwargs)
        self.agent_configs = agent_configs or []
        self.is_running = True
        self.current_agent_index = 0
        self.command_history = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="live-execution-container"):
            # Top bar with status
            with Horizontal(id="top-bar", classes="toolbar"):
                yield Static("RAVEN Live Execution", id="title")
                yield Static(f"Agents: {len(self.agent_configs)}", id="agent-count")
                yield Static("●", id="status-dot", renderable="●", style="green")
                yield Static("Running", id="status-text")

            yield Static("─" * 80)

            # Main area with tabs
            with TabbedContent(id="main-tabs"):
                # Agent panels tab
                with TabPane("Agents", id="agents-tab"):
                    yield self._agent_panels()

                # Activity log tab
                with TabPane("Activity", id="activity-tab"):
                    yield self._activity_log()

                # Task board tab
                with TabPane("Tasks", id="tasks-tab"):
                    yield self._task_board()

            yield Static("─" * 80)

            # Bottom command area
            with Horizontal(id="command-area", classes="toolbar"):
                yield Static("Command:", id="command-label")
                yield Input(
                    "",
                    id="command-input",
                    placeholder="Enter instructions for agents...",
                    placeholder_css_class="command-input",
                )
                yield Button("▶", id="execute-btn", variant="primary")

            # Status bar at bottom
            yield Static(id="bottom-status")

    def _agent_panels(self) -> VerticalScroll:
        """Create agent status panels."""
        scroll = VerticalScroll(id="agent-panels-scroll")

        for i, config in enumerate(self.agent_configs[:5]):  # Show up to 5 agents
            agent_id = f"agent-{i + 1}"
            with Panel(
                Static(
                    f"Agent {agent_id}\n"
                    f"Provider: {config.get('provider', '—')}\n"
                    f"Model: {config.get('model', '—')}\n"
                    f"Role: {config.get('role', '—')}\n"
                    f"Status: Idle",
                    id=f"agent-{agent_id}-panel",
                ),
                title=f"Agent {agent_id}",
                border_style="cyan",
                subtitle=f"Agent {agent_id}",
            ):
                pass

        return scroll

    def _activity_log(self) -> VerticalScroll:
        """Create activity log panel."""
        scroll = VerticalScroll(id="activity-log-scroll")

        return scroll

    def _task_board(self) -> VerticalScroll:
        """Create task board panel."""
        scroll = VerticalScroll(id="task-board-scroll")

        # Sample tasks - dynamic based on agent configs
        sample_tasks = [
            {"id": "T-001", "description": "Code review", "agent": "Agent 1", "status": "In Progress"},
            {"id": "T-002", "description": "Test generation", "agent": "Agent 2", "status": "Queued"},
            {"id": "T-003", "description": "Data analysis", "agent": "Agent 3", "status": "Completed"},
        ]

        for task in sample_tasks:
            status_color = {
                "In Progress": "yellow",
                "Queued": "cyan",
                "Completed": "green",
            }.get(task.get("status", "Queued"), "white")

            scroll.append(
                f"[bold]{task['id']}[/] {task['description']} "
                f"[{status_color}]{task['status']}[/] - {task['agent']}"
            )

        return scroll

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
        # Note: no full back navigation in foundation step

    def action_submit(self) -> None:
        """Submit the command from the input field."""
        command_input = self.query_one("#command-input", Input)
        command = command_input.value.strip()

        if not command:
            return

        # Add to command history/log
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.query_one("#bottom-status", Static).update(
            f"[{timestamp}] Command: {command}"
        )

        # Simulate agent activity (demo data only)
        self._simulate_agent_activity(command)

        # Clear input and refocus
        command_input.value = ""
        command_input.focus()

    def _simulate_agent_activity(self, command: str) -> None:
        """Simulate agent activity for demonstration (demo data only)."""

        async def activity_loop():
            # Show that command was received
            try:
                status_text = self.query_one("#status-text", Static)
                status_text.update("Processing")
            except Exception:
                pass

            # Simulate work
            await asyncio.sleep(1)

            # Update status back
            try:
                status_text = self.query_one("#status-text", Static)
                status_text.update("Idle")
                status_dot = self.query_one("#status-dot", Static)
                status_dot.renderable = "●"
                status_dot.styles = {"style": "green"}
            except Exception:
                pass

            # Add activity log entry (demo)
            try:
                activity_log = self.query_one("#activity-log-scroll", VerticalScroll)
                timestamp = datetime.now().strftime("%H:%M:%S")
                agent_num = (self.current_agent_index % len(self.agent_configs)) + 1
                activity_log.append(
                    f"[{timestamp}] Agent {agent_num} processing: {command[:50]}..."
                )
            except Exception:
                pass

            # Cycle to next agent
            self.current_agent_index = (self.current_agent_index + 1) % len(
                self.agent_configs
            )

        import asyncio

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