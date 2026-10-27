"""Capability Manager - tracks agent capabilities and matches them to task requirements."""

from __future__ import annotations

from typing import Dict, Set, List, Optional, Any
import asyncio


class CapabilityManager:
    """Tracks agent capabilities and matches them to task requirements."""
    
    def __init__(self):
        """Initialize the capability manager."""
        # agent_id -> set of capabilities
        self.agent_capabilities: Dict[str, Set[str]] = {}
        # capability -> set of agent_ids that have this capability
        self.capability_agents: Dict[str, Set[str]] = {}
    
    def assign_capability(self, agent_id: str, capability: str) -> None:
        """Assign a capability to an agent.
        
        Args:
            agent_id: The agent's ID
            capability: The capability name (e.g., "python", "javascript", "testing")
        """
        if agent_id not in self.agent_capabilities:
            self.agent_capabilities[agent_id] = set()
        
        self.agent_capabilities[agent_id].add(capability)
        
        if capability not in self.capability_agents:
            self.capability_agents[capability] = set()
        self.capability_agents[capability].add(agent_id)
    
    def remove_capability(self, agent_id: str, capability: str) -> None:
        """Remove a capability from an agent."""
        self.agent_capabilities.get(agent_id, set()).discard(capability)
        self.capability_agents.get(capability, set()).discard(agent_id)
    
    def has_capability(self, agent_id: str, capability: str) -> bool:
        """Check if an agent has a specific capability."""
        return capability in self.agent_capabilities.get(agent_id, set())
    
    def agent_matches_role(self, agent_id: str, role: str) -> bool:
        """Check if an agent's capabilities match a role requirement."""
        agent_caps = self.agent_capabilities.get(agent_id, set())
        # Check if agent has role as capability or if role is their assigned role
        return role in agent_caps or agent_id in self._get_agents_by_role(role, [])
    
    def _get_agents_by_role(self, role: str, fallback: List[Any]) -> List[Any]:
        """Helper to get agents by role."""
        return [
            aid for aid, caps in self.agent_capabilities.items()
            if role in caps
        ]
    
    def find_suitable_agent(
        self, 
        required_capabilities: List[str], 
        exclude_agents: Optional[List[str]] = None
    ) -> Optional[str]:
        """Find an agent that matches required capabilities.
        
        Args:
            required_capabilities: List of capabilities needed
            exclude_agents: List of agent IDs to exclude
            
        Returns:
            Agent ID that matches, or None if no suitable agent found
        """
        exclude_set = set(exclude_agents or [])
        
        # Find agents that have ALL required capabilities
        for agent_id, caps in self.agent_capabilities.items():
            if agent_id in exclude_set:
                continue
            if all(cap in caps for cap in required_capabilities):
                return agent_id
        
        # If no agent has all capabilities, find one with the most matches
        best_agent = None
        best_match_count = 0
        
        for agent_id, caps in self.agent_capabilities.items():
            if agent_id in exclude_set:
                continue
            match_count = sum(1 for cap in required_capabilities if cap in caps)
            if match_count > best_match_count:
                best_match_count = match_count
                best_agent = agent_id
        
        return best_agent
    
    def get_available_agents(
        self, 
        required_capabilities: List[str],
        available_ids: Optional[List[str]] = None
    ) -> List[str]:
        """Get list of agent IDs that match the required capabilities.
        
        Args:
            required_capabilities: List of capabilities needed
            available_ids: Optional list of agent IDs considered available
            
        Returns:
            List of matching agent IDs
        """
        available = set(available_ids) if available_ids else set(self.agent_capabilities.keys())
        
        matching = []
        for agent_id in available:
            caps = self.agent_capabilities.get(agent_id, set())
            if all(cap in caps for cap in required_capabilities):
                matching.append(agent_id)
        
        return matching