"""Terminal Tools - terminal output handling with Rich integration for formatted logging."""

from __future__ import annotations

import sys
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box


class TerminalTools:
    """Terminal output handling with Rich integration for formatted logging."""
    
    def __init__(self, 
                 console: Optional[Console] = None,
                 theme: Optional[dict] = None):
        """Initialize terminal tools.
        
        Args:
            console: Rich Console instance (created if not provided)
            theme: Theme dict with color keys
        """
        self.console = console or Console(
            force_terminal=True,
            color_system="dark",
            width=120,
        )
        self.theme = theme or {
            "background": "#080A12",
            "electric_blue": "#168CFF",
            "purple": "#842BFF",
            "agent_1": "#FF5555",
            "agent_2": "#55FF55",
            "agent_3": "#5555FF",
            "agent_4": "#FF55FF",
            "agent_5": "#FFFF55",
        }
    
    def print_header(self, text: str, style: Optional[str] = None) -> None:
        """Print a formatted header."""
        color = style or self.theme.get("electric_blue", "#168CFF")
        panel = Panel(
            Text(text, style=f"bold {color}"),
            box=box.ROUNDED,
            style=f"on {self.theme.get('background', '#080A12')}",
        )
        self.console.print(panel)
    
    def print_agent_status(self, agent_id: str, role: str, status: str, 
                          provider: str, model: str) -> None:
        """Print an agent status line."""
        # Color-code by agent number
        agent_colors = {
            "1": self.theme.get("agent_1", "#FF5555"),
            "2": self.theme.get("agent_2", "#55FF55"),
            "3": self.theme.get("agent_3", "#5555FF"),
            "4": self.theme.get("agent_4", "#FF55FF"),
            "5": self.theme.get("agent_5", "#FFFF55"),
        }
        
        color = agent_colors.get(agent_id, "#FFFFFF")
        
        status_text = f"Agent {agent_id}: {role} | {provider} | {model} | {status}"
        self.console.print(
            Panel(
                Text(status_text, style=f"bold {color}"),
                box=box.MINIMAL,
                style=f"on {self.theme.get('background', '#080A12')}",
            )
        )
    
    def print_task_progress(self, task_id: str, description: str, agent_id: str) -> None:
        """Print task progress line."""
        self.console.print(
            Panel(
                Text(
                    f"Task {task_id[:8]}...: {description} (assigned to Agent {agent_id})",
                    style="cyan",
                ),
                box=box.MINIMAL,
                style=f"on {self.theme.get('background', '#080A12')}",
            )
        )
    
    def print_error(self, error: str, context: Optional[str] = None) -> None:
        """Print an error message."""
        error_text = f"Error: {error}"
        if context:
            error_text += f" ({context})"
        
        self.console.print(
            Panel(
                Text(error_text, style="bold red"),
                box=box.MINIMAL,
                style=f"on {self.theme.get('background', '#080A12')}",
            )
        )
    
    def print_success(self, message: str) -> None:
        """Print a success message."""
        self.console.print(
            Panel(
                Text(message, style="bold green"),
                box=box.MINIMAL,
                style=f"on {self.theme.get('background', '#080A12')}",
            )
        )
    
    def print_info(self, message: str) -> None:
        """Print an info message."""
        self.console.print(
            Panel(
                Text(message, style="white"),
                box=box.MINIMAL,
                style=f"on {self.theme.get('background', '#080A12')}",
            )
        )
    
    def print_divider(self) -> None:
        """Print a divider line."""
        self.console.print(
            Panel(
                Text("=" * 60, style="dim"),
                box=box.MINIMAL,
                style=f"on {self.theme.get('background', '#080A12')}",
            )
        )
    
    def format_request_response(self, request: str, response: str, 
                                agent_id: str) -> Panel:
        """Format a request/response pair for display."""
        return Panel(
            f"[bold {self.theme.get('electric_blue', '#168CFF')'}]Request from Agent {agent_id}:[/]\n"
            f"{request}\n\n"
            f"[bold {self.theme.get('purple', '#842BFF')'}]Response:[/]\n"
            f"{response}",
            box=box.DOUBLE,
            style=f"on {self.theme.get('background', '#080A12')}",
        )