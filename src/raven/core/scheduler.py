"""Scheduler - schedules task execution with dependency resolution and parallel execution support."""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Set
import asyncio
from collections import defaultdict


class Scheduler:
    """Scheduler with dependency resolution and appropriate parallel execution."""
    
    def __init__(self, max_parallel: int = 3):
        """Initialize scheduler.
        
        Args:
            max_parallel: Maximum number of tasks to run in parallel
        """
        self.max_parallel = max_parallel
        self._running_tasks: Set[asyncio.Task] = set()
        self._completed: set = set()
        self._dependencies: Dict[str, List[str]] = defaultdict(list)
        self._task_adjacency: Dict[str, List[str]] = defaultdict(list)  # dep -> dependents
    
    def set_dependencies(self, task_ids: List[str], dependencies: Dict[str, List[str]]) -> None:
        """Set task dependencies.
        
        Args:
            task_ids: List of all task IDs
            dependencies: Dict mapping task_id -> list of task_ids it depends on
        """
        for task_id in task_ids:
            if task_id in dependencies:
                self._dependencies[task_id] = dependencies[task_id]
                # Build reverse adjacency (dependency -> dependents)
                for dep in dependencies[task_id]:
                    self._task_adjacency[dep].append(task_id)
    
    async def execute_with_deps(
        self,
        tasks: List[dict],
        agent: Any,
    ) -> List[dict]:
        """Execute tasks respecting dependencies and parallel limits.
        
        Args:
            tasks: List of tasks to execute
            agent: The agent executing the tasks
            
        Returns:
            List of task results
        """
        # Build dependency graph
        task_map = {t["id"]: t for t in tasks}
        all_task_ids = list(task_map.keys())
        self.set_dependencies(all_task_ids, self._dependencies)
        
        results: Dict[str, dict] = {}
        completed_ids: set = set()
        
        # Track which tasks are ready to run
        remaining = set(all_task_ids)
        
        while remaining:
            # Find ready tasks (all deps completed)
            ready = [
                tid for tid in remaining
                if all(dep in completed_ids for dep in self._dependencies.get(tid, []))
            ]
            
            if not ready:
                # No tasks are ready - check if any are running
                if self._running_tasks:
                    # Wait for running tasks to complete
                    done, _ = await asyncio.wait(
                        self._running_tasks,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in done:
                        result = await task
                        task_id = task.get("id", "")
                        completed_ids.add(task_id)
                        results[task_id] = result
                        self._running_tasks.discard(task)
                        
                        # Check if any waiting tasks are now ready
                        remaining -= completed_ids
                        continue
                else:
                    # No tasks running and no ready tasks - deadlock or all done
                    break
            
            # Execute up to max_parallel ready tasks
            to_execute = ready[:self.max_parallel]
            remaining -= set(to_execute)
            
            for task_id in to_execute:
                task = task_map[task_id]
                coro = self._execute_task_with_agent(task, agent)
                task_coro = asyncio.create_task(coro)
                self._running_tasks.add(task_coro)
        
        # Wait for all remaining running tasks
        if self._running_tasks:
            done, _ = await asyncio.wait(
                self._running_tasks,
                return_when=asyncio.ALL_COMPLETED,
            )
            for task in done:
                result = await task
                task_id = task.get("id", "")
                if task_id in results:
                    continue  # Already have result
                results[task_id] = result
        
        return list(results.values())
    
    async def _execute_task_with_agent(self, task: dict, agent: Any) -> dict:
        """Execute a single task with the given agent.
        
        Args:
            task: Task dictionary
            agent: Agent to execute with
            
        Returns:
            Task result dictionary
        """
        # Publish task started event
        # Actually execute via agent
        try:
            result = await agent.execute_task(task)
            return {
                "task_id": task.get("id", ""),
                "status": "completed",
                "result": result,
                "agent_id": agent.id,
            }
        except asyncio.TimeoutError:
            return {
                "task_id": task.get("id", ""),
                "status": "timeout",
                "error": "Task execution timed out",
                "agent_id": agent.id,
            }
        except Exception as e:
            return {
                "task_id": task.get("id", ""),
                "status": "failed",
                "error": str(e),
                "agent_id": agent.id,
            }