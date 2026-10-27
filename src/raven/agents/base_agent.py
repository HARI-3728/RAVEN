"""Base Agent - abstract base class defining the agent interface, capabilities, and lifecycle methods."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio


class BaseAgent(ABC):
    """Abstract base class for all RAVEN agents."""
    
    def __init__(self, agent_id: str, config: dict, provider: Any = None):
        """Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Agent configuration dict (provider, model, role, instructions)
            provider: Provider instance for AI model calls
        """
        self.id = agent_id
        self.config = config
        self.provider = provider
        self.role = config.get("role", "developer")
        self.model = config.get("model", "")
        self.instructions = config.get("instructions", "")
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._is_available = True
        self._current_task: Optional[dict] = None
    
    @property
    def available(self) -> bool:
        """Check if the agent is available for new tasks."""
        return self._is_available
    
    def is_available(self) -> bool:
        """Check if the agent is available for new tasks."""
        return self._is_available
    
    async def receive_task(self, task: dict) -> None:
        """Receive a task from the task manager.
        
        Args:
            task: Task dictionary with description, role, etc.
        """
        self._current_task = task
        await self._task_queue.put(task)
        self._is_available = False
    
    def mark_available(self) -> None:
        """Mark the agent as available after task completion."""
        self._is_available = True
        self._current_task = None
    
    @abstractmethod
    async def execute_task(self, task: dict) -> Any:
        """Execute a given task using the agent's provider.
        
        Args:
            task: Task dictionary to execute
            
        Returns:
            Task result (string, code, or structured data)
        """
        pass
    
    async def process_tasks(self) -> None:
        """Process tasks from the queue. Meant to be called in a loop."""
        while True:
            task = await self._task_queue.get()
            try:
                result = await self.execute_task(task)
                # Publish result via event bus
                await self._task_completed(task, result)
            except Exception as e:
                await self._task_failed(task, e)
            finally:
                self.mark_available()
    
    async def _task_completed(self, task: dict, result: Any) -> None:
        """Handle task completion."""
        pass
    
    async def _task_failed(self, task: dict, error: Exception) -> None:
        """Handle task failure."""
        pass


class SimpleAgent(BaseAgent):
    """Concrete implementation of a basic agent for testing and simple use cases."""
    
    async def execute_task(self, task: dict) -> str:
        """Execute a task by generating a response from the provider.
        
        Args:
            task: Task dictionary
            
        Returns:
            String result from the AI model
        """
        # Build prompt from task and agent context
        prompt = self._build_prompt(task)
        
        # Try to use provider if available
        if self.provider:
            try:
                result = await self.provider.generate_response(prompt, task.get("context", ""))
                return result.content if hasattr(result, 'content') else str(result)
            except Exception:
                pass
        
        # Fallback: generate a simple response
        return self._generate_fallback_response(task)
    
    def _build_prompt(self, task: dict) -> str:
        """Build a prompt for the AI model from the task and agent context."""
        role = self.role or "developer"
        instructions = self.instructions or "No specific instructions."
        description = task.get("description", "No description provided.")
        
        return self.config.get(
            "prompt_template",
            f"""Role: {role}
Instructions: {instructions}

Task: {description}

Provide a helpful response:"""
        )
    
    def _generate_fallback_response(self, task: dict) -> str:
        """Generate a simple fallback response when no provider is available."""
        description = task.get("description", "No description")
        return f"[Fallback] Task: {description}\n[Agent: {self.role}]\n[Status: Completed via fallback]"