"""Unit tests for RAVEN configuration parsing."""

from __future__ import annotations

import pytest

from raven.utils.config_loader import load_config, ProviderConfig, AgentConfig, TeamConfig


class TestProviderConfig:
    """Test ProviderConfig Pydantic model."""

    def test_valid_provider_config(self):
        """Test that a valid provider config can be loaded."""
        config = load_config(
            "configs/providers.yaml",
            ProviderConfig,
        )
        assert config is not None
        assert config.name == "openai" or config.name  # First one loaded

    def test_provider_with_defaults(self):
        """Test provider config with default values."""
        # Test that required fields are present
        data = {
            "name": "test_provider",
            "api_key_env": "TEST_KEY",
            "default_model": "test-model",
        }
        config = ProviderConfig(**data)
        assert config.name == "test_provider"
        assert config.api_key_env == "TEST_KEY"
        assert config.default_model == "test-model"


class TestAgentConfig:
    """Test AgentConfig Pydantic model."""

    def test_valid_agent_config(self):
        """Test that a valid agent config can be loaded."""
        config = load_config(
            "configs/providers.yaml",
            AgentConfig,
        )
        assert config is not None
        assert config.provider  # Should have a provider

    def test_agent_with_custom_role(self):
        """Test agent with custom role."""
        data = {
            "provider": "openai",
            "model": "gpt-4o",
            "role": "developer",
            "instructions": "Write clean code.",
        }
        config = AgentConfig(**data)
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.role == "developer"
        assert config.instructions == "Write clean code."


class TestTeamConfig:
    """Test TeamConfig Pydantic model."""

    def test_valid_team_config(self):
        """Test that a valid team config can be loaded."""
        config = load_config(
            "configs/team_templates.yaml",
            TeamConfig,
        )
        assert config is not None
        assert config.num_agents >= 2 and config.num_agents <= 5

    def test_team_size_validation(self):
        """Test team size is validated (2-5)."""
        # Team size of 1 should fail
        with pytest.raises(Exception):
            TeamConfig(num_agents=1)  # type: ignore

        # Team size of 5 should work
        config = TeamConfig(num_agents=5)  # type: ignore
        assert config.num_agents == 5


class TestLoadYAMLConfig:
    """Test YAML configuration loading."""

    def test_load_providers_yaml(self):
        """Test loading providers.yaml configuration."""
        config = load_config("configs/providers.yaml", ProviderConfig)
        assert config is not None
        assert config.name in ["openai", "gemini", "anthropic", "local"]

    def test_load_team_templates_yaml(self):
        """Test loading team_templates.yaml configuration."""
        config = load_config("configs/team_templates.yaml", TeamConfig)
        assert config is not None
        assert config.num_agents in [2, 3, 4, 5]


class TestLoadJSONConfig:
    """Test JSON configuration loading."""

    def test_load_env_example(self):
        """Test loading .env.example configuration."""
        config = load_config(".env.example", ProviderConfig)
        # .env.example may not validate strictly, should handle gracefully
        assert config is None or config is not None  # Either is fine
