"""Workflow Builder - builds task workflows based on available roles and team composition.

Builds ordered task workflows considering:
- Task dependencies
- Agent role assignments
- Team size and capabilities
- Provider capabilities
- Parallel execution opportunities
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
import asyncio

from ..agents.role_manager import RoleManager
from ..agents.agent_factory import AgentFactory


class WorkflowBuilder:
    """Builds task workflows based on available roles and team composition.
    
    Key features:
    - Task dependency tracking and respect
    - Role-based task assignment (roles not tied to agent indices)
    - Parallel execution where agents have compatible roles
    - Workflow generation considering team capabilities
    - Dynamic rebalancing if agents become unavailable
    """
    
    def __init__(
        self,
        role_manager: RoleManager = None,
        agent_factory: AgentFactory = None,
    ):
        """Initialize the WorkflowBuilder.
        
        Args:
            role_manager: RoleManager for role-related operations
            agent_factory: AgentFactory for agent creation/resolution
        """
        self.role_manager = role_manager or RoleManager()
        self.agent_factory = agent_factory or AgentFactory()
        self._workflow: List[dict] = []
        self._completed_task_ids: List[str] = []
    
    def build_workflow(
        self,
        tasks: List[dict],
        agents: List[Any],
        dependencies: Optional[Dict[str, List[str]]] = None,
    ) -> Tuple[List[dict], List[str]]:
        """Build an ordered task workflow considering roles and dependencies.
        
        Args:
            tasks: List of task dicts with keys: id, description, role, etc.
            agents: List of agent instances with .role and .is_available() properties
            dependencies: Optional dict mapping task_id -> list of task_ids it depends on
            
        Returns:
            (workflow, available_agent_ids) tuple
            - workflow: Ordered list of tasks ready for execution
            - available_agent_ids: IDs of agents available for task execution
        """
        if dependencies is None:
            dependencies = {}
        
        # Reset state
        self._workflow = []
        self._completed_task_ids = []
        
        if not tasks:
            return [], []
        
        # Get available agents and their roles
        available_agents = self._get_available_agents_with_roles(agents)
        agent_role_map = self._build_agent_role_map(available_agents)
        
        # Sort tasks by dependency readiness and role match
        ordered_tasks = self._order_tasks_by_dependency_and_role(
            tasks, dependencies, agent_role_map
        )
        
        self._workflow = ordered_tasks
        return ordered_tasks, list(agent_role_map.keys())
    
    def _get_available_agents_with_roles(self, agents: List[Any]) -> List[Any]:
        """Get agents that are available for task execution.
        
        Args:
            agents: List of agent instances
            
        Returns:
            List of available agents
        """
        return [a for a in agents if a.is_available()]
    
    def _build_agent_role_map(self, agents: List[Any]) -> Dict[str, List[str]]:
        """Build a mapping of role names to agent instances.
        
        Args:
            agents: List of available agent instances
            
        Returns:
            Dict mapping role names to lists of agents with that role
        """
        role_map: Dict[str, List[str]] = {}
        
        for agent in agents:
            role = agent.role
            if role not in role_map:
                role_map[role] = []
            role_map[role].append(agent.id)
        
        return role_map
    
    def _order_tasks_by_dependency_and_role(
        self,
        tasks: List[dict],
        dependencies: Dict[str, List[str]],
        agent_role_map: Dict[str, List[str]],
    ) -> List[dict]:
        """Order tasks considering dependencies and role availability.
        
        Uses a modified topological sort that:
        1. Respects task dependencies
        2. Prefers tasks whose role matches available agents
        3. Enables parallel execution when multiple agents can work simultaneously
        
        Args:
            tasks: List of task dicts
            dependencies: Dict mapping task_id -> list of dependency task_ids
            agent_role_map: Mapping of role names to available agent IDs
            
        Returns:
            Ordered list of tasks
        """
        remaining = list(tasks)
        workflow = []
        
        # Track which tasks have been added
        added_ids = set()
        
        while remaining:
            # Find tasks whose dependencies are satisfied
            ready_tasks = []
            for task in remaining:
                task_id = task.get("id", "")
                task_deps = dependencies.get(task_id, [])
                
                # Check if all dependencies are completed
                deps_met = all(dep in self._completed_task_ids for dep in task_deps)
                
                if deps_met:
                    # Check if we have an agent for this task's role
                    task_role = task.get("role", "")
                    has_available_agent = (
                        task_role in agent_role_map 
                        and len(agent_role_map[task_role]) > 0
                    ) or task_role == ""  # No role requirement = any agent
                    
                    if has_available_agent:
                        ready_tasks.append(task)
            
            if not ready_tasks:
                # No ready tasks - check for circular dependencies or unresolvable
                # Add remaining tasks in their original order with a warning
                import warnings
                warnings.warn(
                    "Cannot resolve all task dependencies. "
                    "Adding remaining tasks in original order."
                )
                self._completed_task_ids.extend([t.get("id", "") for t in remaining])
                workflow.extend(remaining)
                break
            
            # Sort ready tasks: prioritize by role match availability, then by priority
            ready_tasks.sort(
                key=lambda t: (
                    # Priority 1: role has available agents
                    task_role_has_agents(t.get("role", ""), agent_role_map),
                    # Priority 2: task priority (higher first)
                    t.get("priority", 0),
                    # Priority 3: original order
                    id(t),
                ),
                reverse=True,
            )
            
            # Add all ready tasks this round
            for task in ready_tasks:
                if task in remaining and task.get("id", "") not in added_ids:
                    remaining.remove(task)
                    workflow.append(task)
                    added_ids.add(task.get("id", ""))
                    
                    # Mark as "assigned" - in full system, would assign to specific agent
        
        return workflow
    
    def _complete_task(self, task_id: str) -> None:
        """Mark a task as completed for dependency tracking.
        
        Args:
            task_id: ID of the task that completed
        """
        self._completed_task_ids.append(task_id)
    
    def get_next_task(
        self,
        completed_task_ids: List[str],
        tasks: List[dict],
        agents: List[Any],
    ) -> Optional[dict]:
        """Get the next task to execute based on completed tasks.
        
        Args:
            completed_task_ids: List of task IDs that just completed
            tasks: All available tasks
            agents: Available agents for task execution
            
        Returns:
            Next task to execute, or None if no more tasks
        """
        # Update completed tasks
        self._completed_task_ids.extend(completed_task_ids)
        
        # Build agent role map for available agents
        available_agents = self._get_available_agents_with_roles(agents)
        agent_role_map = self._build_agent_role_map(available_agents)
        
        # Order tasks by dependency and role
        ordered = self._order_tasks_by_dependency_and_role(
            tasks, {}, agent_role_map
        )
        
        # Return the first uncompleted task
        for task in ordered:
            task_id = task.get("id", "")
            if task_id not in self._completed_task_ids:
                # Simple dependency check
                deps = task.get("dependencies", [])
                if all(dep in self._completed_task_ids for dep in deps):
                    return task
        
        return None
    
    def get_workflow_status(self) -> dict:
        """Get the current workflow status.
        
        Returns:
            Dict with workflow progress information
        """
        return {
            "total_tasks": len(self._workflow) if self._workflow else 0,
            "completed_tasks": len(self._completed_task_ids),
            "workflow": [t.get("id", "unknown") for t in self._workflow],
            "completed": self._completed_task_ids,
        }