"""Agent Setup Screen - configures each agent's provider, model, role, and instructions."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import (
    Input,
    Button,
    Select,
    Static,
)
from textual.containers import Vertical, Horizontal as HContainer
from textual.screen import Screen
from textual.binding import Binding
from pathlib import Path

# Provider options
PROVIDER_OPTIONS = [
    ("OpenAI", "openai"),
    ("Anthropic", "anthropic"),
    ("Google Gemini", "gemini"),
    ("Local (Ollama)", "local"),
]

# Role options (predefined)
ROLE_OPTIONS = [
    ("Developer", "developer"),
    ("Reviewer", "reviewer"),
    ("Tester", "tester"),
    ("Analyst", "analyst"),
    ("Architect", "architect"),
    ("Custom", "custom"),
]


class AgentSetupScreen(Screen):
    """Agent configuration screen - configures each agent's provider, model, role, and instructions."""

    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("c", "continue", "Continue"),
        Binding("q", "quit", "Quit"),
        Binding("b", "back", "Back"),
    ]

    def __init__(self, team_size: int = 2, **kwargs):
        super().__init__(**kwargs)
        self.team_size = team_size
        self.agent_configs: list = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical(id="agent-setup-container", classes="agent-container"):
            yield Static(f"Configure {self.team_size} Agents", id="agent-setup-title")
            yield Static("─" * 60)

            # Agent configuration area - dynamic based on team_size
            for i in range(self.team_size):
                yield self._make_agent_card(i)

            yield Static("─" * 60)

            # Action buttons
            with HContainer(id="action-buttons"):
                yield Button("← Prev", id="prev-btn", disabled=True)
                yield Button("Save & Continue", id="save-btn")
                yield Button("Quit", id="quit-btn")

            # Status
            yield Static(id="status-bar")

    def _make_agent_card(self, agent_index: int):
        """Create a configuration card for a single agent."""
        agent_id = f"agent-{agent_index + 1}"

        with Static(id=f"agent-{agent-id}"):
            yield Static(f"Agent {agent_id}", id=f"agent-{agent_id}-label")
            yield Input(
                "openai",
                id=f"agent{agent_index + 1}-provider",
                placeholder="openai",
            )
            yield Input(
                "gpt-4o",
                id=f"agent{agent_index + 1}-model",
                placeholder="gpt-4o",
            )
            yield Static("Role:", id=f"agent{agent_index + 1}-label-role")
            yield Select(
                [(label, value) for label, value in ROLE_OPTIONS],
                value="developer",
                id=f"agent{agent_index + 1}-role",
            )
            yield Static("Instructions:", id=f"agent{agent_index + 1}-label-instructions")
            yield Input(
                "Write clean, maintainable code.",
                id=f"agent{agent_index + 1}-instructions",
                placeholder="Agent instructions...",
            )
            yield Static("─" * 30)
            yield Button(
                "Test Connection",
                id=f"test-btn-agent-{agent_index + 1}",
                disabled=True,
                classes="small-btn",
            )

    def on_mount(self) -> None:
        """Initialize agent configurations and focus."""
        # Initialize agent configs
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

        # Populate the UI
        self._populate_agent_cards()

        # Focus first agent's provider
        self.query_one("#agent1-provider", Input).focus()

    def _populate_agent_cards(self) -> None:
        """Populate the agent configuration cards from agent_configs."""
        # Update each agent card with saved config values
        for i, config in enumerate(self.agent_configs):
            agent_idx = i + 1  # 1-based for UI IDs
            try:
                provider_input = self.query_one(f"#agent{agent_idx}-provider", Input)
                if provider_input:
                    provider_input.value = config.get("provider", "openai")

                model_input = self.query_one(f"#agent{agent_idx}-model", Input)
                if model_input:
                    model_input.value = config.get("model", "gpt-4o")

                role_select = self.query_one(f"#agent{agent_idx}-role", Select)
                if role_select:
                    role_select.value = config.get("role", "developer")

                instructions_input = self.query_one(
                    f"agent{agent_index + 1}-instructions", Input
                )
                # Note: the ID pattern may vary, handle gracefully
            except Exception:
                pass  # IDs may not match exactly, values set via on_input_changed

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for agent configuration."""
        input_id = event.input.id

        # Parse agent number from input ID
        # Format: agent1-provider, agent1-model, etc.
        parts = input_id.split("-")
        if len(parts) >= 2 and parts[0].startswith("agent"):
            agent_num = int(parts[0].replace("agent", ""))
            field = parts[1]  # provider, model, role, instructions

            if 1 <= agent_num <= self.team_size:
                # Update the agent config
                agent_idx = agent_num - 1

                if field == "provider":
                    self.agent_configs[agent_idx]["provider"] = event.value
                elif field == "model":
                    self.agent_configs[agent_idx]["model"] = event.value
                elif field == "role":
                    # Find the select widget
                    try:
                        select_widget = self.query_one(
                            f"#agent{agent_num}-role", Select
                        )
                        self.agent_configs[agent_idx]["role"] = select_widget.value
                    except Exception:
                        pass
                elif field == "instructions":
                    self.agent_configs[agent_idx]["instructions"] = event.value

                # Enable test button if provider is set
                test_btn_id = f"test-btn-agent-{agent_num}"
                # Check if test button exists in current query
                try:
                    test_btn = self.query_one(f"#{test_btn_id}", Button)
                    test_btn.disabled = (
                        self.agent_configs[agent_idx]["provider"] == ""
                    )
                except Exception:
                    pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle role selection changes."""
        select_id = event.select.id
        # Similar parsing as input changed
        parts = select_id.split("-")
        if len(parts) >= 2 and parts[0].startswith("agent"):
            agent_num = int(parts[0].replace("agent", ""))
            if 1 <= agent_num <= self.team_size:
                agent_idx = agent_num - 1
                self.agent_configs[agent_idx]["role"] = event.value

                # Enable test button
                test_btn_id = f"test-btn-agent-{agent_num}"
                try:
                    test_btn = self.query_one(f"#{test_btn_id}", Button)
                    test_btn.disabled = (
                        self.agent_configs[agent_idx]["provider"] == ""
                    )
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

        # Show loading indicator
        self.app.show_loader(True)

        # Simulate connection test (foundation step - no real API calls)
        import asyncio

        asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))

        self.app.show_loader(False)

        # Show success/failure (demo data - clearly labeled)
        self.app.notify(
            f"Connection test for Agent {agent_num} ({provider}): Demo mode - no real API tested",
            severity="information",
        )

    def _save_agent_configs(self) -> None:
        """Save all agent configurations and move to next screen."""
        # Validate all agents have provider and model
        all_valid = True
        for i, config in enumerate(self.agent_configs):
            if not config.get("provider") or not config.get("model"):
                all_valid = False
                self.app.notify(
                    f"Agent {i + 1} missing provider or model",
                    severity="error",
                )

        if all_valid:
            # Save configurations to app state
            self.app.agent_configs = self.agent_configs
            self.app.switch_screen("connection_test")

    def action_save(self) -> None:
        """Save agent configs."""
        self._save_agent_configs()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_back(self) -> None:
        """Go back to team size."""
        self.app.switch_screen("team_size")