"""Provider Base - common interface for all AI model providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json


class ProviderResult:
    """Structured result from a provider call."""
    
    def __init__(
        self,
        content: str,
        model: str,
        provider: str,
        usage: Optional[Dict[str, Any]] = None,
        finish_reason: Optional[str] = None,
        raw_response: Optional[Any] = None,
    ):
        """Initialize ProviderResult.
        
        Args:
            content: The model's text response
            model: The model identifier that was used
            provider: The provider name
            usage: Token usage information (if available)
            finish_reason: Why the model stopped generating
            raw_response: The raw API response for debugging
        """
        self.content = content
        self.model = model
        self.provider = provider
        self.usage = usage
        self.finish_reason = finish_reason
        self.raw_response = raw_response


class AIProvider(ABC):
    """Common interface for all AI model providers."""
    
    def __init__(self, config: dict):
        """Initialize the provider with configuration.
        
        Args:
            config: Provider configuration dict with keys like:
                - api_key_env: Environment variable name for API key
                - default_model: Default model identifier
                - supported_models: List of supported model IDs
                - timeout: Request timeout in seconds
                - max_retries: Maximum retry attempts
        """
        self.config = config
        self.name = self.__class__.__name__.lower()
    
    @abstractmethod
    async def generate_response(self, 
                                prompt: str, 
                                context: str = "",
                                model: Optional[str] = None) -> ProviderResult:
        """Generate a response from the AI model.
        
        Args:
            prompt: The user prompt/request
            context: Additional project context
            model: Optional model override from configuration
            
        Returns:
            ProviderResult with response content and metadata
        """
        pass
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate that API credentials are available and valid.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        pass
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information and availability.
        
        Args:
            model_id: The model identifier to look up
            
        Returns:
            Dictionary with model info or None if not found
        """
        return None
    
    def get_supported_models(self) -> list:
        """Get list of supported model identifiers for this provider.
        
        Returns:
            List of model IDs supported by this provider
        """
        return []
    
    def format_prompt(self, system: str, user: str) -> str:
        """Format a system/user prompt pair for this provider.
        
        Different providers have different prompt formatting requirements.
        This method handles the formatting convention for each provider.
        
        Args:
            system: System prompt/instructions
            user: User message/content
            
        Returns:
            Formatted prompt string ready for API call
        """
        return f"System: {system}\nUser: {user}"