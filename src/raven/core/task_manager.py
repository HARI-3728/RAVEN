"""Task Manager - manages task lifecycle: creation, assignment, execution, completion, and cancellation.

Manages the complete task lifecycle with:
- Task creation with roles, dependencies, and priorities
- Task assignment to appropriate agents
- Execution coordination with retry and timeout handling
- Cancellation support
- Context sharing between tasks and agents
- Status tracking and event publishing
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
import uuid
import asyncio
import copy

from ..core.event_bus import EventBus


class TaskManager:
    """Manages task lifecycle: creation, assignment, execution, completion, and cancellation.
    
    Key features:
    - Task creation with roles, dependencies, and priorities
    - Assignment to agents based on role matching
    - Retry and timeout handling
    - Cancellation support with cancellation flags
    - Context sharing between tasks
    - Status tracking and event publishing
    - Failure recovery mechanisms
    """
    
    def __init__(self, event_bus: EventBus = None):
        """Initialize the TaskManager.
        
        Args:
            event_bus: EventBus instance for publishing events
        """
        self.event_bus = event_bus or EventBus()
        self.tasks: Dict[str, dict] = {}
        self._cancellation_flags: Dict[str, asyncio.Event] = {}
        self._retry_counts: Dict[str, int] = {}
        self._max_default_retries = 2
        self._context_manager = None  # Set externally if needed
    
    def set_context_manager(self, cm) -> None:
        """Set the context manager for context sharing.
        
        Args:
            cm: ContextManager instance
        """
        self._context_manager = cm
    
    def create_task(
        self,
        description: str,
        role: str,
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
        context: Optional[dict] = None,
        retry_count: Optional[int] = None,
    ) -> str:
        """Create a new task and return its ID.
        
        Args:
            description: Human-readable task description
            role: Required role for an agent to execute this task
            dependencies: List of task IDs that must complete first
            priority: Priority number (higher = more urgent)
            context: Optional context dict to share with agent
            retry_count: Max retries for this task (None uses default)
            
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
            "created_at": asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0,
            "context": copy.deepcopy(context) if context else {},
            "retry_count": retry_count or self._max_default_retries,
            "max_retries": retry_count or self._max_default_retries,
            "retry_count_used": 0,
            "result": None,
            "error": None,
        }
        
        self.tasks[task_id] = task
        
        # Publish task created event
        asyncio.create_task(self._publish_task_created(task))
        return task_id
    
    def _publish_task_created(self, task: dict) -> None:
        """Publish task created event."""
        asyncio.create_task(self.event_bus.publish("task_created", task))
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dict or None if not found
        """
        return self.tasks.get(task_id)
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Any = None,
        error: Optional[Exception] = None,
    ) -> bool:
        """Update a task's status and optionally store result/error.
        
        Args:
            task_id: Task ID
            status: New status ("pending", "running", "completed", "failed", "cancelled")
            result: Task result value
            error: Exception if task failed
            
        Returns:
            True if task was found and updated, False otherwise
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        old_status = task["status"]
        
        # Don't transition from terminal states in unexpected ways
        if old_status in ("completed", "cancelled", "failed") and status not in (
            "completed",
            "cancelled",
            "failed",
        ):
            return False
        
        task["status"] = status
        
        if result is not None:
            task["result"] = result
        
        if error is not None:
            task["error"] = error
        
        # Publish status update
        asyncio.create_task(
            self._publish_status_update(task_id, status, result, error)
        )
        
        return True
    
    async def _publish_status_update(
        self, task_id: str, status: str, result: Any, error: Optional[Exception]
    ) -> None:
        """Publish task status update event."""
        task = self.tasks.get(task_id, {})
        await self.event_bus.publish(
            "task_status_updated",
            {
                "task_id": task_id,
                "status": status,
                "description": task.get("description", ""),
                "has_result": result is not None,
                "has_error": error is not None,
            },
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if task was cancelled, False if task doesn't exist or already completed/cancelled
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # Can't cancel terminal states
        if task["status"] in ("completed", "cancelled"):
            return False
        
        # Mark task as cancelled
        task["status"] = "cancelled"
        task["error"] = Exception("Task cancelled by user")
        
        # Create cancellation event
        self._cancellation_flags[task_id] = asyncio.Event()
        
        # Publish cancellation event
        asyncio.create_task(
            self.event_bus.publish("task_cancelled", {"task_id": task_id})
        )
        
        return True
    
    def check_cancellation(self, task_id: str) -> bool:
        """Check if a task has been cancelled.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            True if the task has been cancelled
        """
        return (
            task_id in self._cancellation_flags
            and self._cancellation_flags[task_id].is_set()
        )
    
    def can_retry(self, task_id: str) -> bool:
        """Check if a task can be retried (has remaining retry attempts).
        
        Args:
            task_id: Task ID to check
            
        Returns:
            True if the task can be retried
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        return (
            task["status"] in ("failed",) 
            and task["retry_count_used"] < task["max_retries"]
        )
    
    def mark_retry_used(self, task_id: str) -> None:
        """Mark a retry as used for a task.
        
        Args:
            task_id: Task ID
        """
        task = self.tasks.get(task_id)
        if task:
            task["retry_count_used"] += 1
    
    async def _publish_cancellation(self, task_id: str) -> None:
        """Publish task cancellation event."""
        await self.event_bus.publish("task_cancelled", {"task_id": task_id})
    
    def get_pending_tasks(self) -> List[dict]:
        """Get all tasks that are pending (not yet started).
        
        Returns:
            List of task dicts with status "pending"
        """
        return [
            t for t in self.tasks.values()
            if t["status"] == "pending"
        ]
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get task status information.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status dict or None
        """
        task = self.tasks.get(task_id)
        if task:
            return {
                "id": task_id,
                "status": task["status"],
                "description": task["description"],
                "role": task["role"],
                "has_result": task["result"] is not None,
                "has_error": task["error"] is not None,
            }
        return None
    
    def get_all_tasks(self) -> Dict[str, dict]:
        """Get all tasks.
        
        Returns:
            Dict mapping task IDs to task dicts
        """
        return copy.deepcopy(self.tasks)