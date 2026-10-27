"""Provider Registry - maps provider names to provider classes and validates availability."""

from __future__ import annotations

from typing import Dict, Type, Optional
import importlib
import os


class ProviderRegistry:
    """Registry of available AI providers."""
    
    def __init__(self):
        """Initialize the provider registry."""
        self._providers: Dict[str, Type] = {}
        self._default_models: Dict[str, str] = {}
        self._instance_map: Dict[str, Any] = {}
    
    def register(self, name: str, provider_class: Type) -> None:
        """Register a provider class under a name.
        
        Args:
            name: Provider name (e.g., "openai", "anthropic")
            provider_class: Provider class conforming to AIProvider interface
        """
        self._providers[name] = provider_class
    
    def get(self, name: str) -> Type:
        """Get a provider class by name.
        
        Args:
            name: Provider name
            
        Returns:
            Provider class
            
        Raises:
            ValueError: If provider name is not registered
        """
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}. Available: {self.list_providers()}")
        return self._providers[name]
    
    def list_providers(self) -> list:
        """List all registered provider names."""
        return list(self._providers.keys())
    
    def set_default_model(self, provider_name: str, model_id: str) -> None:
        """Set the default model for a provider.
        
        Args:
            provider_name: Provider name
            model_id: Default model identifier
        """
        self._default_models[provider_name] = model_id
    
    def get_default_model(self, provider_name: str) -> Optional[str]:
        """Get the default model for a provider.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Model identifier or None
        """
        return self._default_models.get(provider_name)
    
    def create_instance(self, provider_name: str, config: dict = None) -> Any:
        """Create a provider instance from configuration.
        
        Args:
            provider_name: Provider name
            config: Provider configuration dict
            
        Returns:
            Initialized provider instance
        """
        provider_class = self.get(provider_name)
        config = config or {}
        instance = provider_class(config)
        self._instance_map[provider_name] = instance
        return instance
    
    def get_instance(self, provider_name: str) -> Any:
        """Get an existing provider instance.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Provider instance or None
        """
        return self._instance_map.get(provider_name)
    
    async def validate_all_credentials(self) -> Dict[str, bool]:
        """Validate credentials for all registered providers.
        
        Returns:
            Dict mapping provider name to validation status
        """
        results: Dict[str, bool] = {}
        for name in self._providers:
            try:
                instance = self.create_instance(name)
                results[name] = instance.validate_credentials()
            except Exception as e:
                results[name] = False
        return results