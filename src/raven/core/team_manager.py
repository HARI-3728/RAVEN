"""Team Manager - manages agent team configuration, role assignment, and validation.

Manages the complete agent team lifecycle including:
- Team size validation (2-5 agents only)
- Agent configuration with provider, model, role, and instructions
- Role recommendations based on team size
- Complete configuration validation before starting
- Dynamic adaptation to team size and role assignments
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
import warnings

from ..providers.registry import ProviderRegistry
from ..agents.role_manager import RoleManager
from ..agents.agent_factory import AgentFactory


class TeamManager:
    """Manages agent team configuration, role assignment, and team size validation.
    
    Key responsibilities:
    - Team size validation (2, 3, 4, or 5 agents only - no hardcoded 5-agent layout)
    - Agent configuration with providers, models, roles, and instructions
    - Role recommendations based on team size and project context
    - Complete configuration validation before starting execution
    - Dynamic role assignment independent of agent indices
    """
    
    VALID_TEAM_SIZES = [2, 3, 4, 5]
    MIN_AGENTS = 2
    MAX_AGENTS = 5
    
    def __init__(
        self, 
        role_manager: RoleManager = None,
        provider_registry: ProviderRegistry = None,
        agent_factory: AgentFactory = None,
    ):
        """Initialize the TeamManager.
        
        Args:
            role_manager: RoleManager instance for role validation
            provider_registry: ProviderRegistry for provider validation
            agent_factory: AgentFactory for agent creation
        """
        self.role_manager = role_manager or RoleManager()
        self.provider_registry = provider_registry or ProviderRegistry()
        self.agent_factory = agent_factory or AgentFactory(
            self.role_manager, self.provider_registry
        )
        
        self.team_size: Optional[int] = None
        self.agent_configs: List[dict] = []
        self.agents: List[Any] = []
        self._validation_errors: List[str] = []
    
    def set_team_size(self, size: int) -> Tuple[bool, str]:
        """Set the number of agents in the team.
        
        Args:
            size: Number of agents (must be 2, 3, 4, or 5)
            
        Returns:
            (success, message) tuple
        """
        if size not in self.VALID_TEAM_SIZES:
            return False, f"Team size must be 2, 3, 4, or 5, got {size}"
        
        self.team_size = size
        self.agent_configs = []
        self.agents = []
        self._validation_errors = []
        
        return True, f"Team size set to {size} agents"
    
    def get_team_size(self) -> Optional[int]:
        """Get the current team size."""
        return self.team_size
    
    def configure_agents(
        self,
        provider_models_roles: List[dict],
    ) -> Tuple[bool, str]:
        """Configure agents with providers, models, and roles.
        
        Each dict in the list should have keys: provider, model, role, instructions.
        
        Args:
            provider_models_roles: List of agent configuration dicts
            
        Returns:
            (success, message) tuple with detailed validation info
        """
        self._validation_errors = []
        
        # Validate team size is set
        if self.team_size is None:
            return False, "Team size must be set before configuring agents"
        
        # Validate count matches team size
        if len(provider_models_roles) != self.team_size:
            return False, (
                f"Expected {self.team_size} agent configurations, "
                f"got {len(provider_models_roles)}"
            )
        
        # Validate each agent configuration
        for i, config in enumerate(provider_models_roles):
            agent_errors = self._validate_agent_config(config, i)
            self._validation_errors.extend(agent_errors)
        
        # If no errors, store the configurations
        if not self._validation_errors:
            self.agent_configs = provider_models_roles
            return True, f"Successfully configured {self.team_size} agents"
        
        # Return with errors - don't store configs
        error_summary = "; ".join(self._validation_errors)
        return False, f"Configuration errors: {error_summary}"
    
    def _validate_agent_config(self, config: dict, agent_index: int) -> List[str]:
        """Validate a single agent configuration.
        
        Args:
            config: Agent configuration dict
            agent_index: Index of this agent (for error reporting)
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        provider = config.get("provider", "").strip()
        model = config.get("model", "").strip()
        role = config.get("role", "").strip()
        instructions = config.get("instructions", "").strip()
        
        if not provider:
            errors.append(f"Agent {agent_index + 1}: Missing provider name")
        
        if not model:
            errors.append(f"Agent {agent_index + 1}: Missing model identifier")
        
        if not role:
            errors.append(f"Agent {agent_index + 1}: Missing role assignment")
        
        # Validate provider exists
        if provider:
            try:
                self.provider_registry.get(provider)
            except ValueError:
                errors.append(f"Agent {agent_index + 1}: Unknown provider '{provider}'")
        
        # Validate role
        if role:
            if not self.role_manager.is_valid_role(role):
                errors.append(f"Agent {agent_index + 1}: Invalid role '{role}'")
        
        # Check model supported by provider (if provider is known)
        if provider and model:
            try:
                provider_class = self.provider_registry.get(provider)
                if hasattr(provider_class, 'supported_models'):
                    supported = provider_class.supported_models
                    if model not in supported:
                        warnings.warn(
                            f"Model '{model}' may not be fully supported by '{provider}'. "
                            f"Supported models include: {supported[:3]}..."
                        )
                # Also check via role manager for default model
                default_model = self.role_manager.get_role_instructions(role)
                # Note: model validation is primarily provider-dependent
            except Exception:
                pass
        
        # Instructions are optional but good to have
        if not instructions:
            warnings.warn(
                f"Agent {agent_index + 1}: No custom instructions provided. "
                "Using role default instructions."
            )
        
        return errors
    
    def add_agent_config(self, config: dict) -> Tuple[bool, str]:
        """Add a single agent configuration (for dynamic team building).
        
        Args:
            config: Agent configuration dict
            
        Returns:
            (success, message) tuple
        """
        # Validate the config
        agent_errors = self._validate_agent_config(config, len(self.agent_configs))
        
        if agent_errors:
            return False, f"Invalid agent config: {'; '.join(agent_errors)}"
        
        self.agent_configs.append(config)
        return True, f"Added agent configuration {len(self.agent_configs)}"
    
    def remove_agent_config(self, index: int) -> Tuple[bool, str]:
        """Remove an agent configuration at the given index.
        
        Args:
            index: Index of agent configuration to remove
            
        Returns:
            (success, message) tuple
        """
        if 0 <= index < len(self.agent_configs):
            self.agent_configs.pop(index)
            # Adjust team size if needed
            if len(self.agent_configs) < self.MIN_AGENTS and self.team_size > len(self.agent_configs):
                self.team_size = len(self.agent_configs)
            return True, f"Removed agent configuration at index {index}"
        
        return False, f"Invalid index: {index}. Must be 0-{len(self.agent_configs) - 1}"
    
    def get_agent_configs(self) -> List[dict]:
        """Get the list of agent configurations."""
        return self.agent_configs
    
    def recommend_roles(self, project_context: str = "") -> List[str]:
        """Recommend suitable roles based on current team size.
        
        Args:
            project_context: Description of the project for better recommendations
            
        Returns:
            List of recommended role names
        """
        return self.role_manager.recommend_roles(self.team_size or 2, project_context)
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """Validate the complete team configuration before starting.
        
        Performs comprehensive validation:
        - Team size is valid (2-5)
        - Number of configs matches team size
        - All providers are valid and supported
        - All roles are valid
        - Models are supported by their providers
        - Required fields are present
        
        Returns:
            (is_valid, error_messages) tuple
        """
        errors = []
        
        # 1. Check team size
        if self.team_size is None:
            errors.append("Team size not set")
        elif self.team_size not in self.VALID_TEAM_SIZES:
            errors.append(f"Invalid team size: {self.team_size}")
        
        # 2. Check agent count matches team size
        if self.team_size and len(self.agent_configs) != self.team_size:
            errors.append(
                f"Agent count ({len(self.agent_configs)}) doesn't match team size ({self.team_size})"
            )
        
        # 3. Validate each agent config
        if self.agent_configs:
            for i, config in enumerate(self.agent_configs):
                agent_errors = self._validate_agent_config(config, i)
                errors.extend(agent_errors)
        
        # 4. Check for duplicate roles (warning, not error)
        # Roles can be shared across agents per requirements
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def create_agents(self) -> Tuple[bool, str]:
        """Create agent instances from the configured agent configurations.
        
        Uses the agent factory to create BaseAgent instances from the
        stored configurations. Roles are independent of agent indices.
        
        Returns:
            (success, message) tuple
        """
        is_valid, validation_errors = self.validate_configuration()
        
        if not is_valid:
            return False, f"Configuration invalid: {'; '.join(validation_errors)}"
        
        try:
            # Create agents using the factory
            self.agents = self.agent_factory.create_agents_from_config(self.agent_configs)
            
            # Publish agent ready events
            import asyncio
            # Note: In full implementation, would publish via event bus
            
            return True, f"Successfully created {len(self.agents)} agents"
            
        except Exception as e:
            return False, f"Failed to create agents: {str(e)}"
    
    def get_available_agents(self) -> List[Any]:
        """Get list of agents that are currently available for task assignment.
        
        Returns:
            List of agents that are not currently executing tasks
        """
        if not self.agents:
            return []
        return [a for a in self.agents if a.is_available()]
    
    def get_agent_by_role(self, role: str) -> Optional[Any]:
        """Get the first available agent with a specific role.
        
        This demonstrates that roles are not bound to fixed agent indices -
        any agent can have any role, and we search by role requirement.
        
        Args:
            role: Required role name
            
        Returns:
            Available agent with matching role, or None
        """
        available = self.get_available_agents()
        for agent in available:
            if agent.role == role:
                return agent
        return None
    
    def get_role_distribution(self) -> Dict[str, int]:
        """Get a count of how many agents have each role.
        
        Returns:
            Dict mapping role names to counts
        """
        distribution: Dict[str, int] = {}
        for agent in self.agents:
            role = agent.role
            distribution[role] = distribution.get(role, 0) + 1
        return distribution