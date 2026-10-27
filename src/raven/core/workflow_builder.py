"""Workflow Builder - builds task workflows based on available roles and team composition."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import asyncio

from .event_bus import EventBus


class WorkflowBuilder:
    """Builds task workflows based on available roles and the task."""
    
    def __init__(self, event_bus: EventBus):
        """Initialize the workflow builder."""
        self.event_bus = event_bus
        self.workflow: List[dict] = []
    
    def build_workflow(
        self,
        tasks: List[dict],
        agents: List[dict],
        dependencies: Optional[Dict[str, List[str]]] = None,
    ) -> List[dict]:
        """Build a task workflow considering agent roles and task dependencies.
        
        Args:
            tasks: List of task descriptions
            agents: List of agent configurations (provider, model, role)
            dependencies: Optional dict mapping task_id -> list of task_ids it depends on
            
        Returns:
            Ordered list of tasks representing the workflow
        """
        if dependencies is None:
            dependencies = {}
        
        # Start with all tasks
        remaining = list(tasks)
        self.workflow = []
        
        # Build ordered workflow considering dependencies
        while remaining:
            # Find tasks whose dependencies are satisfied
            ready_tasks = []
            for task in remaining:
                task_deps = dependencies.get(task.get("id", ""), [])
                if all(dep in [t["id"] for t in self.workflow] for dep in task_deps):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # No ready tasks - possible circular dependency or unresolved deps
                # Add remaining tasks in their original order
                self.workflow.extend(remaining)
                break
            
            # Sort ready tasks by priority/role match
            ready_tasks.sort(key=lambda t: t.get("priority", 0), reverse=True)
            
            # Add all ready tasks this round
            for task in ready_tasks:
                if task in remaining:
                    remaining.remove(task)
                    self.workflow.append(task)
        
        # Publish workflow event
        import asyncio
        asyncio.create_task(
            self.event_bus.publish("workflow_built", {"workflow": self.workflow})
        )
        
        return self.workflow
    
    def get_next_task(self, completed_task_ids: List[str]) -> Optional[dict]:
        """Get the next task to execute based on completed tasks.
        
        Args:
            completed_task_ids: List of task IDs that just completed
            
        Returns:
            Next task or None if no more tasks
        """
        for task in self.workflow:
            if task["id"] not in completed_task_ids:
                # Check if all dependencies are met
                deps_met = all(
                    dep in completed_task_ids 
                    for dep in task.get("dependencies", [])
                )
                if deps_met:
                    return task
        return None