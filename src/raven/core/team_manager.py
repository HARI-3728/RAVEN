"""Team Manager - manages agent team configuration, role assignment, and validation."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from ..providers.registry import ProviderRegistry
from ..agents.role_manager import RoleManager


class TeamManager:
    """Manages agent team configuration, role assignment, and team size validation."""
    
    VALID_TEAM_SIZES = [2, 3, 4, 5]
    
    def __init__(self, role_manager: RoleManager, provider_registry: ProviderRegistry):
        self.role_manager = role_manager
        self.provider_registry = provider_registry
        self.team_size: Optional[int] = None
        self.agent_configs: List[dict] = []
    
    def set_team_size(self, size: int) -> bool:
        """Set the number of agents in the team.
        
        Args:
            size: Number of agents (must be 2, 3, 4, or 5)
            
        Returns:
            True if team size set successfully, False otherwise
        """
        if size not in self.VALID_TEAM_SIZES:
            raise ValueError(f"Team size must be 2, 3, 4, or 5, got {size}")
        
        self.team_size = size
        return True
    
    def configure_agents(self, provider_models_roles: List[dict]) -> bool:
        """Configure agents with providers, models, and roles.
        
        Args:
            provider_models_roles: List of dicts with keys: provider, model, role, instructions
            
        Returns:
            True if configuration valid
        """
        if self.team_size is None:
            raise ValueError("Team size must be set before configuring agents")
        
        if len(provider_models_roles) != self.team_size:
            raise ValueError(
                f"Expected {self.team_size} agent configurations, got {len(provider_models_roles)}"
            )
        
        # Validate each agent configuration
        for i, config in enumerate(provider_models_roles):
            # Validate provider exists
            provider = config.get("provider", "")
            if not self.provider_registry.get(provider, None):
                raise ValueError(f"Unknown provider: {provider} for agent {i}")
            
            # Validate role is valid
            role = config.get("role", "")
            if not self.role_manager.is_valid_role(role):
                raise ValueError(f"Invalid role: {role} for agent {i}")
            
            # Validate model availability
            model = config.get("model", "")
            # Could call provider.get_model_info here
            
            self.agent_configs.append(config)
        
        return True
    
    def get_team_size(self) -> Optional[int]:
        """Get the current team size."""
        return self.team_size
    
    def get_agent_configs(self) -> List[dict]:
        """Get the list of agent configurations."""
        return self.agent_configs
    
    def recommend_roles(self, project_context: str = "") -> List[str]:
        """Recommend suitable roles based on team size and project context.
        
        Args:
            project_context: Description of the project for role recommendations
            
        Returns:
            List of recommended role names
        """
        base_roles = {
            2: ["developer", "reviewer"],
            3: ["developer", "reviewer", "tester"],
            4: ["developer", "reviewer", "tester", "analyst"],
            5: ["developer", "reviewer", "tester", "analyst", "architect"],
        }
        
        return base_roles.get(self.team_size, ["developer"]) if self.team_size else ["developer"]