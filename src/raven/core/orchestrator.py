"""Orchestrator - coordinates agent workflow and execution flow."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import asyncio

from ..providers.registry import ProviderRegistry
from ..agents.agent_factory import AgentFactory
from ..core.event_bus import EventBus
from ..storage.task_repository import TaskRepository


class Orchestrator:
    """Coordinates agent workflow, task distribution, and execution flow."""
    
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        agent_factory: AgentFactory,
        task_repository: TaskRepository,
        event_bus: EventBus,
    ):
        self.provider_registry = provider_registry
        self.agent_factory = agent_factory
        self.task_repository = task_repository
        self.event_bus = event_bus
        self.agents: Dict[str, Any] = {}
        self.tasks: Dict[str, Any] = {}
        self.running = False
    
    async def start_session(self, team_config: dict) -> None:
        """Start a new agent session with the given team configuration.
        
        Args:
            team_config: Dictionary with agent configurations (provider, model, role, instructions)
        """
        self.running = True
        
        # Create agents from configuration
        for agent_config in team_config.get("agents", []):
            agent = self.agent_factory.create(agent_config)
            self.agents[agent.id] = agent
            await self.event_bus.publish("agent_ready", {"agent_id": agent.id, "agent": agent})
        
        # Process tasks from repository
        await self._process_tasks()
    
    async def _process_tasks(self) -> None:
        """Process and distribute tasks to available agents."""
        tasks = self.task_repository.get_pending_tasks()
        
        for task in tasks:
            if not self.running:
                break
            
            # Find suitable agent based on task role and agent capabilities
            suitable_agent = self._find_agent_for_task(task)
            
            if suitable_agent:
                await self._assign_task(suitable_agent, task)
            else:
                # No agent available yet; retry later
                await asyncio.sleep(0.5)
                await self._process_tasks()
                break
    
    def _find_agent_for_task(self, task: dict) -> Optional[Any]:
        """Find a suitable agent for a given task based on role matching."""
        required_role = task.get("role", "")
        
        for agent_id, agent in self.agents.items():
            if agent.role == required_role and agent.is_available():
                return agent
        
        # If no exact match, try any available agent
        for agent_id, agent in self.agents.items():
            if agent.is_available():
                return agent
        
        return None
    
    async def _assign_task(self, agent: Any, task: dict) -> None:
        """Assign a task to an agent."""
        await self.event_bus.publish("task_assigned", {"agent_id": agent.id, "task": task})
        agent.receive_task(task)
        await self.event_bus.publish("agent_started", {"agent_id": agent.id})
    
    async def stop_session(self) -> None:
        """Stop the current agent session."""
        self.running = False
        await self.event_bus.publish("session_stopped", {})
        self.agents.clear()
        self.tasks.clear()