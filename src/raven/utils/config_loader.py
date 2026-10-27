"""Config Loader - YAML/JSON configuration loading with Pydantic validation."""

from __future__ import annotations

import os
import yaml
import json
from typing import Dict, Any, Optional, Type, get_type_hints
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, validator


class BaseConfig(BaseModel):
    """Base configuration class with common validation."""
    
    model_config = {"extra": "forbid"}  # Disallow extra fields
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.model_dump(), indent=2)


def load_yaml(path: str) -> Optional[dict]:
    """Load a YAML configuration file.
    
    Args:
        path: Path to the YAML file
        
    Returns:
        Dict with YAML content or None if file not found/unparseable
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError, IOError):
        return None


def load_json(path: str) -> Optional[dict]:
    """Load a JSON configuration file.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        Dict with JSON content or None if file not found/unparseable
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return None


def load_config(
    path: str,
    model: Type[BaseModel],
    env_override: bool = True,
) -> Optional[BaseModel]:
    """Load a configuration file and validate against a Pydantic model.
    
    Args:
        path: Path to the configuration file (YAML or JSON)
        model: Pydantic model class for validation
        env_override: Whether to allow environment variable overrides
        
    Returns:
        Validated Pydantic model instance or None
    """
    # Try YAML first, then JSON
    config_data = load_yaml(path)
    if config_data is None:
        config_data = load_json(path)
    
    if config_data is None:
        return None
    
    try:
        # Handle both dict and already-validated cases
        if isinstance(config_data, BaseModel):
            return config_data
        
        instance = model(**config_data)
        
        # Apply environment variable overrides if enabled
        if env_override:
            instance = _apply_env_overrides(instance)
        
        return instance
    except ValidationError as e:
        # Log and return None rather than raising
        import warnings
        warnings.warn(f"Configuration validation error: {e}")
        return None
    except Exception as e:
        import warnings
        warnings.warn(f"Error loading configuration: {e}")
        return None


def _apply_env_overrides(instance: BaseModel) -> BaseModel:
    """Apply environment variable overrides to a Pydantic model instance.
    
    Args:
        instance: Pydantic model instance
        
    Returns:
        Updated model instance with env overrides applied
    """
    import os
    
    # Get all field names
    fields = instance.model_fields
    
    if not fields:
        return instance
    
    # For each field, check if there's an corresponding environment variable
    for field_name in fields:
        env_var_name = f"RAVEN_{field_name.upper()}"
        env_value = os.environ.get(env_var_name)
        
        if env_value is not None:
            # Try to convert to the field's type
            field_info = fields[field_name]
            field_type = field_info.annotation
            
            try:
                # Handle various types
                if field_type in (str,):
                    converted = env_value
                elif field_type in (int,):
                    converted = int(env_value)
                elif field_type in (float,):
                    converted = float(env_value)
                elif field_type in (bool,):
                    converted = env_value.lower() in ("true", "1", "yes", "y")
                else:
                    converted = env_value
                
                # Create a new instance with the updated field
                instance_dict = instance.model_dump()
                instance_dict[field_name] = converted
                instance = type(instance)(**instance_dict)
            except (ValueError, TypeError):
                # If conversion fails, skip this override
                pass
    
    return instance


# Configuration model examples

class ProviderConfig(BaseConfig):
    """Configuration for an AI provider."""
    name: str = Field(description="Provider name (openai, gemini, anthropic, etc.)")
    api_key_env: str = Field(description="Environment variable name for API key")
    default_model: str = Field(description="Default model identifier")
    supported_models: list = Field(
        default_factory=list, 
        description="List of supported model IDs"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(
        default=2, 
        description="Maximum retry attempts"
    )


class AgentConfig(BaseConfig):
    """Configuration for a single agent."""
    provider: str = Field(description="Provider name")
    model: str = Field(description="Model identifier")
    role: str = Field(description="Agent role")
    instructions: str = Field(
        default="", 
        description="Custom instructions for the agent"
    )


class TeamConfig(BaseConfig):
    """Configuration for the agent team."""
    num_agents: int = Field(
        ge=2, le=5, 
        description="Number of agents (2-5)"
    )
    agents: list = Field(
        default_factory=list, 
        description="List of agent configurations"
    )