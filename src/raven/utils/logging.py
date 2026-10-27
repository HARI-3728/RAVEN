"""Logging - structured logging with Rich integration for terminal output."""

from __future__ import annotations

import sys
import logging
from typing import Dict, Any, Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


# Configure the Rich handler for terminal output
rich_console = Console(
    force_terminal=True,
    color_system="auto",  # Use "auto" instead of "dark"
    width=120,
)

# Set up Python standard logger with Rich handler
def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    rich: bool = True,
) -> logging.Logger:
    """Set up structured logging with Rich integration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Optional custom format string
        rich: Whether to use Rich terminal formatting
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("raven")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers = []
    
    if rich:
        # Rich handler for colored terminal output
        rich_handler = RichHandler(
            console=rich_console,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        rich_handler.setFormatter(
            logging.Formatter("%(message)s", datefmt="[X]")
        )
        logger.addHandler(rich_handler)
    else:
        # Standard handler
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(stdout_handler)
    
    return logger


# Standard log level functions with Rich formatting
class StructuredLogger:
    """Logger with Rich-formatted output for terminal UI."""
    
    def __init__(self, logger: logging.Logger, console: Console):
        """Initialize the structured logger."""
        self.logger = logger
        self.console = console
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(message, **kwargs)
    
    def success(self, message: str) -> None:
        """Log a success message (green)."""
        self.console.print(f"[green]✓[/] {message}")
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(message, **kwargs)
    
    def agent_activity(self, agent_id: str, role: str, message: str) -> None:
        """Log an agent activity message with color coding."""
        colors = {
            "1": "red",
            "2": "green", 
            "3": "blue",
            "4": "magenta",
            "5": "yellow",
        }
        color = colors.get(agent_id, "white")
        self.console.print(
            f"[bold {color}]Agent {agent_id}[/] [{color}]{role}[/] {message}"
        )
    
    def task_event(self, task_id: str, event: str, detail: str = "") -> None:
        """Log a task event."""
        tid = task_id[:8] if len(task_id) > 8 else task_id
        self.console.print(
            f"[cyan]Task {tid}[/] {event}: {detail}"
        )
    
    def provider_activity(self, provider: str, model: str, message: str) -> None:
        """Log provider activity."""
        self.console.print(
            f"[magenta]Provider {provider}/{model}[/] {message}"
        )


# Pre-configured logger instance
raven_logger = setup_logging()