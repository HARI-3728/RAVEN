"""Agent Registry - registry of available agents and their capabilities."""

from __future__ import annotations

from typing import Dict, Any, Optional
import uuid


class AgentRegistry:
    """Registry of available agents and their capabilities."""
    
    def __init__(self):
        """Initialize the agent registry."""
        self.agents: Dict[str, Any] = {}
        self.capabilities: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
    
    def register(self, agent: Any) -> str:
        """Register an agent in the registry.
        
        Args:
            agent: Agent instance to register
            
        Returns:
            Agent ID
        """
        agent_id = agent.id
        self.agents[agent_id] = agent
        
        # Register agent's capabilities
        caps = agent.get_capabilities() if hasattr(agent, 'get_capabilities') else set()
        self.capabilities[agent_id] = caps
        
        # Also register individual capabilities
        for cap in caps:
            if cap not in self._global_caps:
                self._global_caps.add(cap)
        
        return agent_id
    
    def unregister(self, agent_id: str) -> None:
        """Unregister an agent from the registry."""
        self.agents.pop(agent_id, None)
        self.capabilities.pop(agent_id, None)
    
    def get(self, agent_id: str) -> Optional[Any]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Any]:
        """List all registered agents."""
        return list(self.agents.values())
    
    def get_agent_for_role(self, role: str) -> Optional[Any]:
        """Get an agent capable of performing a given role.
        
        Args:
            role: The role to find an agent for
            
        Returns:
            Agent instance or None
        """
        for agent in self.agents.values():
            if agent.role == role or role in agent.capabilities:
                return agent
        return None
    
    def get_agents_by_role(self, role: str) -> List[Any]:
        """Get all agents that can perform a given role."""
        return [
            agent for agent in self.agents.values()
            if agent.role == role or role in agent.capabilities
        ]
    
    _global_caps: Set[str] = set()