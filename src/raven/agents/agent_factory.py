"""Agent Factory - creates agent instances from configuration."""

from __future__ import annotations

from typing import Dict, Any, Optional
import uuid

from .base_agent import BaseAgent, SimpleAgent


class AgentFactory:
    """Factory for creating agent instances from configuration."""
    
    def __init__(self, agent_registry: Optional[Any] = None):
        """Initialize the agent factory."""
        self.agent_registry = agent_registry
    
    def create(self, config: dict, agent_id: Optional[str] = None) -> BaseAgent:
        """Create an agent instance from configuration.
        
        Args:
            config: Agent configuration dict with keys:
                - provider: Provider name (e.g., "openai", "anthropic")
                - model: Model identifier (e.g., "gpt-4o")
                - role: Agent role (e.g., "developer", "reviewer")
                - instructions: Agent instructions
                - (any other agent-specific settings)
            agent_id: Optional agent ID; if not generated automatically
            
        Returns:
            BaseAgent instance
        """
        agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        config = dict(config)  # Copy to avoid mutation
        
        # Extract and validate required fields
        role = config.pop("role", "developer")
        model = config.pop("model", "")
        instructions = config.pop("instructions", "")
        provider_name = config.pop("provider", "openai")
        
        # Create simple agent (full provider integration would inject provider instance)
        agent = SimpleAgent(
            agent_id=agent_id,
            config={
                "role": role,
                "model": model,
                "instructions": instructions,
                "provider": provider_name,
            },
        )
        
        return agent
    
    def create_with_provider(
        self,
        config: dict,
        provider_instance: Any,
        agent_id: Optional[str] = None,
    ) -> BaseAgent:
        """Create an agent instance with a pre-configured provider.
        
        Args:
            config: Agent configuration dict
            provider_instance: Initialized provider instance (e.g., OpenAIProvider)
            agent_id: Optional agent ID
            
        Returns:
            BaseAgent instance with provider injected
        """
        agent = self.create(config, agent_id=agent_id)
        agent.provider = provider_instance
        return agent