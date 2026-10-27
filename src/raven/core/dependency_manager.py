"""Dependency Manager - manages task and agent dependencies."""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Set
import asyncio


class DependencyManager:
    """Manages dependencies between tasks and agents."""
    
    def __init__(self):
        """Initialize dependency manager."""
        # task_id -> set of task_ids it depends on
        self.task_deps: Dict[str, Set[str]] = {}
        # task_id -> set of task_ids that depend on it
        self.task_dependents: Dict[str, Set[str]] = {}
        # agent_id -> set of task_ids currently assigned
        self.agent_tasks: Dict[str, Set[str]] = {}
    
    def add_task_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency: task_id depends on depends_on."""
        if task_id not in self.task_deps:
            self.task_deps[task_id] = set()
        self.task_deps[task_id].add(depends_on)
        
        if depends_on not in self.task_dependents:
            self.task_dependents[depends_on] = set()
        self.task_dependents[depends_on].add(task_id)
    
    def remove_task_dependency(self, task_id: str, depends_on: str) -> None:
        """Remove a dependency."""
        self.task_deps[task_id].discard(depends_on)
        self.task_dependents[depends_on].discard(task_id)
    
    def are_deps_met(self, task_id: str, completed_ids: Set[str]) -> bool:
        """Check if all dependencies for a task are met.
        
        Args:
            task_id: The task to check
            completed_ids: Set of task IDs that have completed
            
        Returns:
            True if all deps are completed
        """
        deps = self.task_deps.get(task_id, set())
        return all(dep in completed_ids for dep in deps)
    
    def get_ready_tasks(
        self, 
        all_task_ids: Set[str], 
        completed_ids: Set[str]
    ) -> Set[str]:
        """Get tasks whose dependencies are all completed.
        
        Args:
            all_task_ids: All task IDs in the system
            completed_ids: Set of completed task IDs
            
        Returns:
            Set of task IDs ready to execute
        """
        ready = set()
        for tid in all_task_ids:
            if self.are_deps_met(tid, completed_ids):
                ready.add(tid)
        return ready