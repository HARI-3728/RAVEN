"""Prompt Builder - constructs prompts from agent configurations, roles, and project context."""

from __future__ import annotations

from typing import Dict, Any, Optional
import json


class PromptBuilder:
    """Constructs prompts from agent configurations, roles, and project context."""
    
    def __init__(self, context_manager: Any = None, role_manager: Any = None):
        """Initialize the prompt builder."""
        self.context_manager = context_manager
        self.role_manager = role_manager
    
    def build_agent_prompt(
        self,
        agent_id: str,
        task_description: str,
        project_context: Optional[dict] = None,
        additional_instructions: Optional[str] = None,
    ) -> str:
        """Build a complete prompt for an agent to execute a task.
        
        Args:
            agent_id: The agent's ID (to fetch role and context)
            task_description: Description of the task to perform
            project_context: Optional project context dict
            additional_instructions: Optional additional instructions to append
            
        Returns:
            Formatted prompt string
        """
        # Get agent role from context manager or config
        role = self._get_agent_role(agent_id)
        
        # Get default instructions for the role
        default_instructions = self._get_role_instructions(role)
        
        # Get project context
        proj_ctx = self._get_project_context(project_context)
        
        # Build the prompt using a template
        prompt_parts = [
            f"=== Agent Role: {role} ===",
            f"Agent ID: {agent_id}",
        ]
        
        if default_instructions:
            prompt_parts.append(f"Default Instructions: {default_instructions}")
        
        prompt_parts.extend([
            "",
            f"=== Task Description ===",
            task_description,
        ])
        
        if proj_ctx:
            prompt_parts.extend([
                "",
                "=== Project Context ===",
                proj_ctx,
            ])
        
        if additional_instructions:
            prompt_parts.extend([
                "",
                "=== Additional Instructions ===",
                additional_instructions,
            ])
        
        prompt_parts.append("")
        prompt_parts.append("=== Response ===")
        prompt_parts.append("Provide your response above, following the agent role and task requirements.")
        
        return "\n".join(prompt_parts)
    
    def _get_agent_role(self, agent_id: str) -> str:
        """Get the role for an agent."""
        # Try to get from context manager
        if self.context_manager:
            ctx_role = self.context_manager.get_agent_context(agent_id, "role")
            if ctx_role:
                return ctx_role
        
        # Default fallback
        return "developer"
    
    def _get_role_instructions(self, role: str) -> str:
        """Get default instructions for a role."""
        if self.role_manager:
            return self.role_manager.get_role_instructions(role)
        return f"You are a {role}."
    
    def _get_project_context(self, project_context: Optional[dict]) -> str:
        """Format project context for inclusion in prompt."""
        if not project_context:
            return ""
        
        # Format common context keys
        ctx_parts = []
        if "project_root" in project_context:
            ctx_parts.append(f"Project Root: {project_context['project_root']}")
        if "shared_context" in project_context:
            ctx_parts.append(f"Shared Context: {project_context['shared_context']}")
        if "event_history" in project_context:
            ctx_parts.append(f"Recent Events: {project_context['event_history']}")
        
        return "\n".join(ctx_parts) if ctx_parts else ""