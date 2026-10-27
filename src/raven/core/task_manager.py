"""Task Manager - manages task lifecycle: creation, assignment, execution, completion, and cancellation."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import uuid
import asyncio

from ..core.event_bus import EventBus


class TaskManager:
    """Manages task lifecycle: creation, assignment, execution, completion, and cancellation."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.tasks: Dict[str, Any] = {}
        self._cancellation_flags: Dict[str, bool] = {}
    
    def create_task(
        self,
        description: str,
        role: str,
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
    ) -> str:
        """Create a new task and return its ID.
        
        Args:
            description: Human-readable task description
            role: Required role for an agent to execute this task
            dependencies: List of task IDs that must complete first
            priority: Priority number (higher = more urgent)
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "description": description,
            "role": role,
            "dependencies": dependencies or [],
            "priority": priority,
            "status": "pending",
            "created_at": asyncio.get_event_loop().time(),
        }
        self.tasks[task_id] = task
        
        asyncio.create_task(self._publish_task_created(task))
        return task_id
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: str, result: Any = None) -> None:
        """Update a task's status and optionally store result."""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
            if result is not None:
                self.tasks[task_id]["result"] = result
            asyncio.create_task(self._publish_status_update(task_id, status, result))
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if task was cancelled, False if task doesn't exist or already completed
        """
        if task_id not in self.tasks:
            return False
        
        if self.tasks[task_id]["status"] in ("completed", "failed", "cancelled"):
            return False
        
        self.tasks[task_id]["status"] = "cancelled"
        self._cancellation_flags[task_id] = True
        asyncio.create_task(self._publish_cancellation(task_id))
        return True
    
    async def _publish_task_created(self, task: dict) -> None:
        """Publish task created event."""
        await self.event_bus.publish("task_created", task)
    
    async def _publish_status_update(self, task_id: str, status: str, result: Any) -> None:
        """Publish task status update event."""
        task = self.tasks.get(task_id, {})
        await self.event_bus.publish("task_status_updated", {
            "task_id": task_id,
            "status": status,
            "description": task.get("description", ""),
        })
    
    async def _publish_cancellation(self, task_id: str) -> None:
        """Publish task cancellation event."""
        await self.event_bus.publish("task_cancelled", {"task_id": task_id})