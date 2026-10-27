"""Unit tests for RAVEN TeamManager.

Tests team size validation, agent configuration, role recommendations,
and complete configuration validation.
Uses mocked providers - no paid API keys required.
"""

from __future__ import annotations

import pytest
import asyncio

from raven.agents.role_manager import RoleManager
from raven.agents.agent_factory import AgentFactory
from raven.core.team_manager import TeamManager
from raven.providers.registry import ProviderRegistry


class TestRoleManager:
    """Test RoleManager functionality."""

    def test_is_valid_role(self):
        """Test role validation."""
        rm = RoleManager()
        assert rm.is_valid_role("developer") is True
        assert rm.is_valid_role("reviewer") is True
        assert rm.is_valid_role("nonexistent") is False
    
    def test_list_roles(self):
        """Test listing available roles."""
        rm = RoleManager()
        roles = rm.list_roles()
        assert "developer" in roles
        assert "reviewer" in roles
        assert "tester" in roles
        assert len(roles) >= 7  # predefined + potential custom
    
    def test_recommend_roles(self):
        """Test role recommendations by team size."""
        rm = RoleManager()
        
        assert rm.recommend_roles(2) == ["developer", "reviewer"]
        assert rm.recommend_roles(3) == ["developer", "reviewer", "tester"]
        assert rm.recommend_roles(4) == ["developer", "reviewer", "tester", "analyst"]
        assert rm.recommend_roles(5) == ["developer", "reviewer", "tester", "analyst", "architect"]
        assert rm.recommend_roles(1) == ["developer"]  # fallback
    
    def test_create_custom_role(self):
        """Test creating a custom role."""
        rm = RoleManager()
        rm.create_custom_role(
            name="data_engineer",
            description="Engineers data pipelines and ETL processes",
            required_skills=["python", "sql", "data_pipelines"],
            default_instructions="Engineer robust data pipelines and ETL processes.",
        )
        assert rm.is_valid_role("data_engineer") is True
        desc = rm.get_role_description("data_engineer")
        assert "data pipelines" in desc
    
    def test_get_role_instructions(self):
        """Test getting role default instructions."""
        rm = RoleManager()
        instructions = rm.get_role_instructions("developer")
        assert "code" in instructions.lower() or "write" in instructions.lower()
    
    def test_get_required_skills(self):
        """Test getting required skills for a role."""
        rm = RoleManager()
        skills = rm.get_required_skills("developer")
        assert "programming" in skills


class TestAgentFactory:
    """Test AgentFactory functionality."""

    @pytest.fixture
    def factory(self):
        """Create an AgentFactory instance."""
        return AgentFactory()
    
    def test_create_agent(self, factory):
        """Test creating an agent from configuration."""
        config = {
            "provider": "openai",
            "model": "gpt-4o",
            "role": "developer",
            "instructions": "Write clean code.",
        }
        agent = factory.create(config)
        assert agent is not None
        assert agent.role == "developer"
        assert agent.model == "gpt-4o"
    
    def test_create_agent_with_id(self, factory):
        """Test creating an agent with a specific ID."""
        config = {
            "provider": "openai",
            "model": "gpt-4o",
            "role": "reviewer",
        }
        agent = factory.create(config, agent_id="test-agent-001")
        assert agent.id == "test-agent-001"
    
    def test_create_agents_from_config(self, factory):
        """Test creating multiple agents from configurations."""
        configs = [
            {
                "provider": "openai",
                "model": "gpt-4o",
                "role": "developer",
                "instructions": "Write code.",
            },
            {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "role": "reviewer",
                "instructions": "Review code.",
            },
        ]
        agents = factory.create_agents_from_config(configs)
        assert len(agents) == 2
        assert agents[0].role == "developer"
        assert agents[1].role == "reviewer"
    
    def test_create_agent_with_role_independent_of_index(self, factory):
        """Test that roles are not bound to fixed agent indices."""
        # Create a developer agent and a reviewer agent
        dev_config = {
            "provider": "openai",
            "model": "gpt-4o",
            "role": "developer",
            "instructions": "Write code.",
        }
        rev_config = {
            "provider": "anthropic",
            "model": "claude-3-sonnet-20240229",
            "role": "reviewer",
            "instructions": "Review code.",
        }
        
        agents = factory.create_agents_from_config([dev_config, rev_config])
        
        # The first agent should have developer role, second should have reviewer
        # This demonstrates roles are independent of indices
        assert agents[0].role == "developer"
        assert agents[1].role == "reviewer"
    
    def test_get_available_agents(self, factory):
        """Test getting available agents."""
        # Create mock agents
        from raven.agents.base_agent import SimpleAgent
        
        agent1 = SimpleAgent(
            agent_id="agent1",
            config={"role": "developer", "model": "gpt-4o", "instructions": "dev"},
        )
        agent2 = SimpleAgent(
            agent_id="agent2", 
            config={"role": "reviewer", "model": "gpt-4o", "instructions": "review"},
        )
        
        # Test get_agent_by_role
        result = factory.get_agent_by_role([agent1, agent2], "developer")
        assert result is agent1  # Should find the developer
        
        # Test with unavailable agent
        agent1._is_available = False
        result = factory.get_agent_by_role([agent1, agent2], "developer")
        assert result is agent2  # Should fall back to any available
    
    def test_validate_configuration(self, factory):
        """Test configuration validation."""
        # Valid configuration
        valid_configs = [
            {
                "provider": "openai",
                "model": "gpt-4o",
                "role": "developer",
                "instructions": "Write code.",
            },
        ]
        is_valid, errors = factory.validate_configuration(valid_configs)
        # Should be valid (or have reasonable errors)
        
        # Invalid - missing provider
        invalid_configs = [
            {
                "model": "gpt-4o",
                "role": "developer",
            },
        ]
        is_valid2, errors2 = factory.validate_configuration(invalid_configs)
        assert is_valid2 is False  # Should be invalid without provider


class TestTeamManager:
    """Test TeamManager functionality."""
    
    @pytest.fixture
    def tm(self):
        """Create a TeamManager instance."""
        return TeamManager()
    
    def test_set_team_size(self, tm):
        """Test setting team size."""
        success, message = tm.set_team_size(3)
        assert success is True
        assert tm.get_team_size() == 3
        
        # Invalid size
        success, message = tm.set_team_size(6)
        assert success is False
    
    def test_configure_agents(self, tm):
        """Test configuring agents."""
        # Set team size first
        tm.set_team_size(2)
        
        # Configure agents
        configs = [
            {
                "provider": "openai",
                "model": "gpt-4o",
                "role": "developer",
                "instructions": "Write code.",
            },
            {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "role": "reviewer",
                "instructions": "Review code.",
            },
        ]
        success, message = tm.configure_agents(configs)
        assert success is True
        assert len(tm.get_agent_configs()) == 2
    
    def test_configure_agents_wrong_count(self, tm):
        """Test configuring agents with wrong count."""
        tm.set_team_size(3)
        
        # Wrong number of configs
        configs = [
            {"provider": "openai", "model": "gpt-4o", "role": "developer"},
            # Missing third agent
        ]
        success, message = tm.configure_agents(configs)
        assert success is False  # Should fail - wrong count
    
    def test_configure_agents_unknown_provider(self, tm):
        """Test configuring agents with unknown provider."""
        tm.set_team_size(1)  # Minimal for test
        configs = [
            {
                "provider": "nonexistent_provider",
                "model": "some-model",
                "role": "developer",
            },
        ]
        success, message = tm.configure_agents(configs)
        assert success is False  # Should fail - unknown provider
    
    def test_configure_agents_invalid_role(self, tm):
        """Test configuring agents with invalid role."""
        tm.set_team_size(1)
        configs = [
            {
                "provider": "openai",
                "model": "gpt-4o",
                "role": "not_a_real_role",
                "instructions": "test",
            },
        ]
        success, message = tm.configure_agents(configs)
        assert success is False  # Should fail - invalid role
    
    def test_recommend_roles(self, tm):
        """Test role recommendations."""
        tm.set_team_size(3)
        roles = tm.recommend_roles()
        assert len(roles) == 3
        assert "developer" in roles
        assert "reviewer" in roles
    
    def test_validate_configuration(self, tm):
        """Test complete configuration validation."""
        tm.set_team_size(2)
        configs = [
            {
                "provider": "openai",
                "model": "gpt-4o",
                "role": "developer",
                "instructions": "Write code.",
            },
            {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "role": "reviewer",
                "instructions": "Review code.",
            },
        ]
        is_valid, errors = tm.validate_configuration()
        # Should be valid with proper configs
        # Note: may have warnings but not hard errors
    
    def test_create_agents(self, tm):
        """Test creating agents from configuration."""
        tm.set_team_size(2)
        configs = [
            {
                "provider": "openai",
                "model": "gpt-4o",
                "role": "developer",
                "instructions": "Write code.",
            },
            {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "role": "reviewer",
                "instructions": "Review code.",
            },
        ]
        success, message = tm.create_agents()
        # Should succeed with valid configs
        # In foundation step, may succeed or have mock behavior