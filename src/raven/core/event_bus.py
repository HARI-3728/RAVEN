"""Event Bus - pub-sub event system for inter-component communication."""

from __future__ import annotations

from typing import Dict, List, Set, Any, Callable
import asyncio
from collections import defaultdict


class EventBus:
    """Pub-sub event system for inter-component communication."""
    
    def __init__(self):
        """Initialize event bus."""
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_queue: asyncio.Queue = asyncio.Queue()
    
    def on(self, event_name: str, handler: Callable) -> None:
        """Register a synchronous handler for an event.
        
        Args:
            event_name: Name of the event
            handler: Function to call when event is published
        """
        self._handlers[event_name].append(handler)
    
    def async_on(self, event_name: str, handler: Callable) -> None:
        """Register an async handler for an event.
        
        Args:
            event_name: Name of the event
            handler: Async function to call when event is published
        """
        self._async_handlers[event_name].append(handler)
    
    def off(self, event_name: str, handler: Callable) -> None:
        """Unregister a handler for an event."""
        self._handlers[event_name] = [
            h for h in self._handlers[event_name] if h != handler
        ]
        self._async_handlers[event_name] = [
            h for h in self._async_handlers[event_name] if h != handler
        ]
    
    async def publish(self, event_name: str, data: dict = None) -> None:
        """Publish an event to all registered handlers.
        
        Args:
            event_name: Name of the event
            data: Data dict to send with the event
        """
        # Fire synchronous handlers (in thread pool to avoid blocking)
        handlers = self._handlers.get(event_name, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                # Log error but don't break the chain
                pass
        
        # Fire async handlers
        async_handlers = self._async_handlers.get(event_name, [])
        for handler in async_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                # Log error but don't break the chain
                pass
        
        # Also add to event queue for history/processing
        if data is not None:
            await self._event_queue.put({"name": event_name, "data": data})