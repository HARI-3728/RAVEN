"""RAVEN TUI Theme - cyber-inspired terminal aesthetic colors."""

from __future__ import annotations

# RAVEN color palette
THEME = {
    "background": "#080A12",  # Black
    "electric_blue": "#168CFF",  # Electric blue
    "purple": "#842BFF",  # Purple
    "text_primary": "#E0E0E0",  # White/light gray
    "text_secondary": "#888888",  # Dim white
    "agent_1": "#FF5555",  # Agent 1 accent (red)
    "agent_2": "#55FF55",  # Agent 2 accent (green)
    "agent_3": "#5555FF",  # Agent 3 accent (blue)
    "agent_4": "#FF55FF",  # Agent 4 accent (magenta)
    "agent_5": "#FFFF55",  # Agent 5 accent (yellow)
}


def get_theme() -> dict:
    """Get the complete theme dictionary."""
    return THEME.copy()