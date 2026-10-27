"""Secrets Manager - secure handling of API keys and secrets."""

from __future__ import annotations

import os
import json
import base64
from typing import Dict, Any, Optional
import warnings


class SecretsManager:
    """Secure handling of API keys and secrets."""
    
    @staticmethod
    def load_env_file(env_path: str = ".env") -> Dict[str, str]:
        """Load environment variables from a .env file.
        
        Args:
            env_path: Path to the .env file
            
        Returns:
            Dict of environment variable names to values
        """
        env_vars: Dict[str, str] = {}
        
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    
                    # Skip var=value with empty value patterns
                    if "=" not in line:
                        continue
                    
                    # Parse KEY=VALUE
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove surrounding quotes
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    if value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
        except FileNotFoundError:
            # .env file doesn't exist - that's OK, environment variables may still be set
            pass
        except Exception as e:
            warnings.warn(f"Error loading .env file: {e}")
        
        return env_vars
    
    @staticmethod
    def get_api_key(provider: str, env_file: str = ".env") -> Optional[str]:
        """Get an API key for a specific provider.
        
        Args:
            provider: Provider name (openai, gemini, anthropic, etc.)
            env_file: Path to .env file
            
        Returns:
            API key value or None if not found
        """
        # First try direct environment variable
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY", 
            "anthropic": "ANTHROPIC_API_KEY",
            "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
        }
        
        env_var = env_var_map.get(provider.lower())
        if env_var:
            # Check direct environment variable first
            key = os.environ.get(env_var)
            if key:
                return key
        
        # Then try .env file
        env_vars = SecretsManager.load_env_file(env_file)
        if env_var and env_vars.get(env_var):
            return env_vars[env_var]
        
        # Check if .env has the key under a different name
        for key, value in env_vars.items():
            if provider.lower() in key.lower():
                return value
        
        return None
    
    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        """Mask sensitive data in text for logging/output.
        
        Args:
            text: Text that may contain API keys or secrets
            
        Returns:
            Text with sensitive data masked
        """
        # Common patterns for API keys (simplified)
        import re
        
        # Mask OpenAI keys (start with sk-)
        text = re.sub(r'sk-[a-zA-Z0-9]{48,}', 'sk-MASKED-****', text)
        
        # Mask generic bearer tokens
        text = re.sub(r' bearer [a-zA-Z0-9._-]+', ' bearer **MASKED**', text, flags=re.IGNORECASE)
        
        # Mask quoted strings that look like keys
        text = re.sub(r'"[a-zA-Z0-9_/]{20,}"', '"**MASKED**', text)
        
        return text
    
    @staticmethod
    def validate_no_secrets(config: dict) -> bool:
        """Validate that a configuration dict doesn't contain API secrets.
        
        Args:
            config: Configuration dict to check
            
        Returns:
            True if no secrets detected
        """
        secret_patterns = ["sk-", "api_key", "secret_key", "token=", "password"]
        
        def _check_dict(d: dict, path: str = "") -> bool:
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if key name suggests a secret
                if any(pattern in current_path.lower() for pattern in secret_patterns):
                    return False
                
                # Check value
                if isinstance(value, str):
                    if any(pattern in value.lower() for pattern in secret_patterns):
                        return False
                
                # Recurse into nested dicts
                if isinstance(value, dict):
                    if not _check_dict(value, current_path):
                        return False
            
            return True
        
        return _check_dict(config)