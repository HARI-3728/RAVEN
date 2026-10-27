"""Context Manager - maintains shared context across agents, project state, and historical events."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import json
import asyncio


class ContextManager:
    """Maintains shared context across agents, project state, and historical events."""
    
    def __init__(self, project_root: str, database=None):
        """Initialize context manager.
        
        Args:
            project_root: Root directory of the project
            database: Optional database connection for persistence
        """
        self.project_root = project_root
        self.database = database
        self.shared_context: Dict[str, Any] = {}
        self.agent_contexts: Dict[str, Dict[str, Any]] = {}  # agent_id -> context
        self.event_history: List[dict] = []
        self._max_history = 1000
    
    def update_shared_context(self, key: str, value: Any) -> None:
        """Update a key in the shared context accessible by all agents."""
        self.shared_context[key] = value
    
    def get_shared_context(self, key: str, default: Any = None) -> Any:
        """Get a value from the shared context."""
        return self.shared_context.get(key, default)
    
    def set_agent_context(self, agent_id: str, key: str, value: Any) -> None:
        """Set a value in an agent's private context."""
        if agent_id not in self.agent_contexts:
            self.agent_contexts[agent_id] = {}
        self.agent_contexts[agent_id][key] = value
    
    def get_agent_context(self, agent_id: str, key: str, default: Any = None) -> Any:
        """Get a value from an agent's private context."""
        return self.agent_contexts.get(agent_id, {}).get(key, default)
    
    def add_event(self, event: dict) -> None:
        """Add an event to the history."""
        self.event_history.append(event)
        if len(self.event_history) > self._max_history:
            self.event_history = self.event_history[-self._max_history:]
    
    def get_event_history(self, agent_id: Optional[str] = None) -> List[dict]:
        """Get event history, optionally filtered by agent.
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            List of events
        """
        if agent_id:
            return [e for e in self.event_history if e.get("agent_id") == agent_id]
        return self.event_history.copy()
    
    def get_project_context(self) -> dict:
        """Get the project context dictionary for agent prompting."""
        return {
            "project_root": self.project_root,
            "shared_context": dict(self.shared_context),
            "event_history_count": len(self.event_history),
            "agent_count": len(self.agent_contexts),
        }
    
    async def persist(self) -> None:
        """Persist context to database for session resumption."""
        if self.database:
            await self.database.save_context({
                "shared_context": self.shared_context,
                "agent_contexts": self.agent_contexts,
                "event_history": self.event_history,
            })