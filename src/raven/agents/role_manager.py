"""Role Manager - manages role definitions, validation, and assignment to agents.

Manages predefined and custom roles for RAVEN agents. Roles are independent
of agent indices - any agent can have any role, and roles can be dynamically
assigned based on task requirements.
"""

from __future__ import annotations

from typing import Dict, Set, List, Optional
import yaml
import os
import warnings

# Predefined roles available in RAVEN
PREDEFINED_ROLES: Dict[str, dict] = {
    "developer": {
        "description": "Writes code, implements features, and produces production-quality software",
        "required_skills": ["programming", "code_architecture"],
        "default_instructions": "Write clean, maintainable, and well-documented code.",
    },
    "reviewer": {
        "description": "Reviews code for quality, security, and best practices",
        "required_skills": ["code_review", "security"],
        "default_instructions": "Review code for quality, security vulnerabilities, and best practices.",
    },
    "tester": {
        "description": "Writes and runs tests for code changes",
        "required_skills": ["testing", "quality_assurance"],
        "default_instructions": "Write comprehensive tests and verify code correctness.",
    },
    "analyst": {
        "description": "Analyzes data and provides insights",
        "required_skills": ["data_analysis", "interpretation"],
        "default_instructions": "Analyze data and provide actionable insights.",
    },
    "architect": {
        "description": "Designs system architecture and guidelines",
        "required_skills": ["system_design", "scalability"],
        "default_instructions": "Design system architecture following best practices.",
    },
    "interpreter": {
        "description": "Interprets results and explains findings",
        "required_skills": ["interpretation", "communication"],
        "default_instructions": "Interpret results and explain findings clearly.",
    },
    "iterator": {
        "description": "Iterates over data structures and extracts values",
        "required_skills": ["iteration", "data_structures"],
        "default_instructions": "Iterate over data structures and extract values systematically.",
    },
}


class RoleManager:
    """Manages role definitions, validation, and assignment to agents.
    
    Key design:
    - Roles are independent of agent indices - any agent can have any role
    - Supports both predefined and custom roles
    - Provides role recommendations based on team size
    - Validates role assignments before agent creation
    """
    
    def __init__(self, role_yaml_path: Optional[str] = None):
        """Initialize the role manager.
        
        Args:
            role_yaml_path: Optional path to YAML file with custom role definitions
        """
        self.roles: Dict[str, dict] = dict(PREDEFINED_ROLES)
        
        # Load custom roles from YAML if provided
        if role_yaml_path and os.path.exists(role_yaml_path):
            try:
                with open(role_yaml_path) as f:
                    custom_roles = yaml.safe_load(f)
                    if custom_roles:
                        self.roles.update(custom_roles)
            except Exception as e:
                warnings.warn(f"Could not load custom roles from {role_yaml_path}: {e}")
    
    def is_valid_role(self, role_name: str) -> bool:
        """Check if a role name is valid (predefined or custom).
        
        Args:
            role_name: Role name to check
            
        Returns:
            True if the role is valid
        """
        return role_name in self.roles
    
    def get_role_description(self, role_name: str) -> str:
        """Get the description for a role.
        
        Args:
            role_name: Role name
            
        Returns:
            Human-readable role description, or description string if not found
        """
        role = self.roles.get(role_name, {})
        return role.get("description", f"Role: {role_name}")
    
    def get_role_instructions(self, role_name: str) -> str:
        """Get the default instructions for a role.
        
        Args:
            role_name: Role name
            
        Returns:
            Default instructions string for agents with this role
        """
        role = self.roles.get(role_name, {})
        return role.get("default_instructions", "No default instructions.")
    
    def get_required_skills(self, role_name: str) -> List[str]:
        """Get the required skills for a role.
        
        Args:
            role_name: Role name
            
        Returns:
            List of required skill names
        """
        role = self.roles.get(role_name, {})
        return role.get("required_skills", [])
    
    def list_roles(self) -> List[str]:
        """List all available roles (predefined + custom).
        
        Returns:
            List of role names
        """
        return list(self.roles.keys())
    
    def recommend_roles(self, team_size: int, project_context: str = "") -> List[str]:
        """Recommend suitable roles based on team size and project context.
        
        Args:
            team_size: Number of agents in the team
            project_context: Description of the project for better recommendations
            
        Returns:
            List of recommended role names
        """
        # Base recommendations by team size
        recommendations = {
            2: ["developer", "reviewer"],
            3: ["developer", "reviewer", "tester"],
            4: ["developer", "reviewer", "tester", "analyst"],
            5: ["developer", "reviewer", "tester", "analyst", "architect"],
        }
        
        base = recommendations.get(team_size, ["developer"])
        
        # Could add project-context-based adjustments here
        # For now, return base recommendations
        return list(base)
    
    def create_custom_role(
        self,
        name: str,
        description: str,
        required_skills: Optional[List[str]] = None,
        default_instructions: str = "",
    ) -> None:
        """Create a new custom role.
        
        Args:
            name: Role name (must be unique)
            description: Human-readable description
            required_skills: List of required skills (defaults to empty list)
            default_instructions: Default instructions for agents with this role
            
        Raises:
            ValueError: If a role with this name already exists
        """
        if name in self.roles:
            raise ValueError(f"Role '{name}' already exists")
        
        if required_skills is None:
            required_skills = []
        
        self.roles[name] = {
            "description": description,
            "required_skills": required_skills,
            "default_instructions": default_instructions,
        }
    
    def get_role_config(self, role_name: str) -> dict:
        """Get the full configuration dict for a role.
        
        Args:
            role_name: Role name
            
        Returns:
            Dict with role configuration (description, skills, instructions)
        """
        role = self.roles.get(role_name, {})
        return {
            "description": role.get("description", ""),
            "required_skills": role.get("required_skills", []),
            "default_instructions": role.get("default_instructions", ""),
        }
    
    def role_exists(self, role_name: str) -> bool:
        """Check if a role exists without importing the full manager state.
        
        Args:
            role_name: Role name to check
            
        Returns:
            True if the role exists
        """
        return role_name in self.roles