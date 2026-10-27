"""TUI Event Bus - minimal event system for screen communication."""

from __future__ import annotations

import asyncio
from typing import Dict, Any, List, Callable
from collections import defaultdict


class TUIEventBus:
    """Minimal event bus for TUI screen communication."""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, event_name: str, handler: Callable) -> None:
        """Subscribe to an event."""
        self._handlers[event_name].append(handler)
    
    def publish(self, event_name: str, data: Any = None) -> None:
        """Publish an event to all subscribers."""
        for handler in self._handlers.get(event_name, []):
            try:
                handler(data)
            except Exception:
                pass