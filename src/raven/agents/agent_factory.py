"""Agent Factory - creates agent instances from configuration.

Factory for creating agent instances based on configuration dictionaries.
Supports dynamic agent creation with provider injection, role assignment,
and no binding to fixed agent indices.
"""

from __future__ import annotations

import uuid
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent, SimpleAgent
from .role_manager import RoleManager
from ..providers.registry import ProviderRegistry


class AgentFactory:
    """Factory for creating agent instances from configuration.
    
    Creates agent instances based on configuration dictionaries that specify:
    - provider: Provider name (e.g., "openai", "anthropic", "gemini", "local")
    - model: Model identifier (e.g., "gpt-4o", "claude-3-sonnet-20240229")
    - role: Agent role (e.g., "developer", "reviewer", "tester")
    - instructions: Custom instructions for the agent
    - Any other agent-specific settings
    
    Key design principles:
    - No agent is bound to a fixed index; roles are independent of agent indices
    - Agents are created from configuration, not hardcoded
    - Custom roles and instructions are fully supported
    - Provider instances can be injected or created lazily
    """
    
    def __init__(
        self, 
        role_manager: RoleManager = None,
        provider_registry: ProviderRegistry = None,
    ):
        """Initialize the agent factory.
        
        Args:
            role_manager: RoleManager instance for role validation/validation
            provider_registry: ProviderRegistry for creating provider instances
        """
        self.role_manager = role_manager or RoleManager()
        self.provider_registry = provider_registry or ProviderRegistry()
        self._agent_counter: int = 0
    
    def create(
        self,
        config: dict,
        agent_id: Optional[str] = None,
        provider_instance: Optional[Any] = None,
    ) -> BaseAgent:
        """Create an agent instance from configuration.
        
        Args:
            config: Agent configuration dict with keys:
                - provider: Provider name (e.g., "openai", "anthropic")
                - model: Model identifier (e.g., "gpt-4o")
                - role: Agent role (e.g., "developer", "reviewer")
                - instructions: Custom instructions for the agent
                - (any other agent-specific settings)
            agent_id: Optional agent ID; if not generated automatically
            provider_instance: Optional pre-configured provider instance
            
        Returns:
            BaseAgent instance configured per the configuration
        """
        # Generate agent ID if not provided
        agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        
        # Extract and validate configuration fields
        role = config.get("role", "developer")
        model = config.get("model", "")
        instructions = config.get("instructions", "")
        provider_name = config.get("provider", "openai")
        
        # Validate role using role manager
        if not self.role_manager.is_valid_role(role):
            # Fallback to "developer" if role is invalid
            import warnings
            warnings.warn(f"Invalid role '{role}', falling back to 'developer'")
            role = "developer"
        
        # Validate and get provider
        provider = self._create_provider(provider_name, provider_instance)
        
        # Build the agent configuration
        agent_config = {
            "role": role,
            "model": model,
            "instructions": instructions,
            "provider": provider_name,
        }
        
        # Create the agent
        agent = SimpleAgent(
            agent_id=agent_id,
            config=agent_config,
            provider=provider,
        )
        
        self._agent_counter += 1
        return agent
    
    def _create_provider(
        self, 
        provider_name: str, 
        provider_instance: Optional[Any] = None,
    ) -> Any:
        """Create or retrieve a provider instance.
        
        Args:
            provider_name: Name of the provider (e.g., "openai")
            provider_instance: Optional pre-configured provider instance
            
        Returns:
            Provider instance conforming to AIProvider interface
        """
        if provider_instance:
            return provider_instance
        
        # Try to get from registry
        provider_class = self.provider_registry.get(provider_name)
        config = self._get_provider_config(provider_name)
        
        config = self._get_provider_config(provider_name) or {}
        return provider_class(config)
    
    def _get_provider_config(self, provider_name: str) -> Optional[dict]:
        """Get provider configuration from registry or defaults.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Configuration dict or None
        """
        # Check if registry has configuration info
        instance = self.provider_registry.get_instance(provider_name)
        if instance and hasattr(instance, 'config'):
            return instance.config
        
        # Return None to use defaults in provider constructor
        return None
    
    def create_agents_from_config(
        self,
        configs: List[dict],
    ) -> List[BaseAgent]:
        """Create multiple agent instances from a list of configurations.
        
        This is the main method for team creation - creates exactly the number
        of agents specified in the configuration list. Roles are independent
        of agent indices.
        
        Args:
            configs: List of agent configuration dicts
            
        Returns:
            List of BaseAgent instances
        """
        agents = []
        
        for i, config in enumerate(configs):
            # Generate unique agent ID - not tied to index
            agent_id = f"agent_{i}_{uuid.uuid4().hex[:4]}"
            
            # Create agent with provider
            agent = self.create(
                config=config,
                agent_id=agent_id,
            )
            agents.append(agent)
        
        return agents
    
    def create_agent_with_role(
        self,
        role: str,
        model: str = "",
        instructions: str = "",
        provider_name: str = "openai",
    ) -> BaseAgent:
        """Create an agent with a specific role, independent of any index.
        
        This method supports the requirement that roles are not tied to
        specific agent numbers - any agent can have any role.
        
        Args:
            role: Agent role name
            model: Model identifier
            instructions: Custom instructions
            provider_name: Provider name
            
        Returns:
            Configured BaseAgent instance
        """
        # Validate role
        if not self.role_manager.is_valid_role(role):
            role = "developer"  # fallback
        
        # Create configuration dict
        config = {
            "provider": provider_name,
            "model": model,
            "role": role,
            "instructions": instructions,
        }
        
        # Create agent
        return self.create(config)
    
    def get_available_agents(self, agents: List[BaseAgent]) -> List[BaseAgent]:
        """Get list of agents that are currently available for task assignment.
        
        An agent is available if it's not currently executing a task.
        
        Args:
            agents: List of agents to check
            
        Returns:
        List of available agents
        """
        return [a for a in agents if a.is_available()]
    
    def get_agent_by_role(
        self, 
        agents: List[BaseAgent], 
        role: str,
    ) -> Optional[BaseAgent]:
        """Get the first available agent with a specific role.
        
        This demonstrates that roles are not bound to fixed agent indices -
        any agent can have any role, and we search by role requirement.
        
        Args:
            agents: List of agents to search
            role: Required role name
            
        Returns:
            Agent with matching role, or None if no available agent has that role
        """
        # First try to find an available agent with the exact role
        for agent in agents:
            if agent.role == role and agent.is_available():
                return agent
        
        # If no exact match, find any available agent
        for agent in agents:
            if agent.is_available():
                return agent
        
        return None
    
    def get_all_roles(self) -> List[str]:
        """Get all available role names from the role manager."""
        return self.role_manager.list_roles()
    
    def validate_configuration(
        self,
        configs: List[dict],
    ) -> tuple:
        """Validate a list of agent configurations before creating agents.
        
        Validates:
        - Provider names exist and are supported
        - Roles are valid
        - Models are supported by the specified providers
        - Required fields are present
        
        Returns:
            (is_valid, error_messages) tuple
        """
        errors = []
        
        if not configs:
            errors.append("No agent configurations provided")
            return False, errors
        
        if len(configs) > 5:
            errors.append(f"Too many agents: {len(configs)}. Maximum is 5.")
        
        if len(configs) < 2:
            errors.append(f"Too few agents: {len(configs)}. Minimum is 2.")
        
        for i, config in enumerate(configs):
            # Check required fields
            provider = config.get("provider", "")
            model = config.get("model", "")
            role = config.get("role", "")
            
            if not provider:
                errors.append(f"Agent {i}: Missing provider name")
            
            if not model:
                errors.append(f"Agent {i}: Missing model identifier")
            
            if not role:
                errors.append(f"Agent {i}: Missing role assignment")
            
            # Validate provider exists
            if provider:
                try:
                    self.provider_registry.get(provider)
                except ValueError:
                    errors.append(f"Agent {i}: Unknown provider '{provider}'")
            
            # Validate role
            if role and not self.role_manager.is_valid_role(role):
                errors.append(f"Agent {i}: Invalid role '{role}'")
            
            # Check model supported by provider (if provider is known)
            if provider and model:
                try:
                    provider_class = self.provider_registry.get(provider)
                    # Check if model is in supported list (may not have instance yet)
                    # We just check the config has the supported_models attribute
                    if hasattr(provider_class, 'supported_models'):
                        supported = provider_class.supported_models
                        if model not in supported:
                            import warnings
                            warnings.warn(
                                f"Model '{model}' may not be supported by '{provider}'. "
                                f"Supported: {supported[:3]}..."
                            )
                except Exception:
                    pass  # Provider may not be instantiable yet
        
        is_valid = len(errors) == 0
        return is_valid, errors