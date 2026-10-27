"""Agent Communication - structured communication between agents (result exchange, hand-offs)."""

from __future__ import annotations

from typing import Dict, Any, Optional, List
import asyncio


class AgentCommunication:
    """Structured communication between agents via the event bus."""
    
    def __init__(self, event_bus: Any = None):
        """Initialize agent communication."""
        self.event_bus = event_bus
    
    async def send_result(
        self,
        from_agent_id: str,
        to_agent_id: str,
        result: Any,
        task_id: str,
        result_type: str = "general",
    ) -> None:
        """Send a structured result from one agent to another.
        
        Args:
            from_agent_id: ID of the agent sending the result
            to_agent_id: ID of the agent receiving the result
            result: The result data (string, code, analysis, etc.)
            task_id: The task ID this result relates to
            result_type: Type of result (e.g., "code", "analysis", "test", "summary")
        """
        message = {
            "from": from_agent_id,
            "to": to_agent_id,
            "result": result,
            "task_id": task_id,
            "type": result_type,
            "timestamp": asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0,
        }
        
        # Publish via event bus if available
        if self.event_bus:
            await self.event_bus.publish("agent_result_sent", message)
        else:
            # Direct publication (no event bus)
            await self._direct_deliver(message)
    
    async def _direct_deliver(self, message: dict) -> None:
        """Direct delivery of a message (fallback without event bus)."""
        # Could implement direct agent referencing here
        pass
    
    async def broadcast_result(
        self,
        sender_id: str,
        result: Any,
        task_id: str,
        result_type: str = "general",
        exclude: Optional[List[str]] = None,
    ) -> None:
        """Broadcast a result to all agents except the sender.
        
        Args:
            sender_id: ID of the agent sending the result
            result: The result data
            task_id: The task ID this result relates to
            result_type: Type of result
            exclude: Optional list of agent IDs to exclude
        """
        message = {
            "from": sender_id,
            "to": "all",
            "result": result,
            "task_id": task_id,
            "type": result_type,
            "broadcast": True,
        }
        
        if self.event_bus:
            await self.event_bus.publish("agent_result_broadcast", message)