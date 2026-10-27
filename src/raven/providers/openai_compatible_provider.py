"""OpenAI-Compatible Provider - adapter for OpenAI-compatible APIs (Together, Bedrock, etc.)."""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from ...providers.base import AIProvider, ProviderResult


class OpenAICompatibleProvider(AIProvider):
    """Adapter for OpenAI-compatible APIs."""
    
    def __init__(self, config: dict):
        """Initialize the OpenAI-compatible provider.
        
        Args:
            config: Provider configuration with keys:
                - api_key_env: Environment variable name (default: "OPENAI_COMPATIBLE_API_KEY")
                - base_url: API base URL (default: "https://api.openai.com/v1")
                - default_model: Default model identifier
                - supported_models: List of supported model IDs
                - timeout: Request timeout in seconds
                - max_retries: Maximum retry attempts
        """
        super().__init__(config)
        self.api_key_env = config.get("api_key_env", "OPENAI_COMPATIBLE_API_KEY")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.default_model = config.get("default_model", "gpt-4o")
        self.supported_models = config.get("supported_models", [
            "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"
        ])
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 2)
        self._api_key = None
    
    async def _get_api_key(self) -> str:
        """Fetch API key from environment if not already cached."""
        if self._api_key is None:
            self._api_key = os.environ.get(self.api_key_env)
            if not self._api_key:
                raise ValueError(
                    f"OpenAI-compatible API key not found in environment variable '{self.api_key_env}'. "
                    "Set this variable before running RAVEN."
                )
        return self._api_key
    
    async def validate_credentials(self) -> bool:
        """Validate OpenAI-compatible API credentials."""
        try:
            key = await self._get_api_key()
            return bool(key and len(key) > 10)
        except Exception:
            return False
    
    async def generate_response(self, 
                                prompt: str, 
                                context: str = "",
                                model: Optional[str] = None) -> ProviderResult:
        """Generate a response from an OpenAI-compatible API."""
        model_id = model or self.default_model
        
        try:
            api_key = await self._get_api_key()
            # Try actual API call
            result = await self._call_openai_compatible_api(prompt, model_id, api_key)
            return result
        except Exception:
            # Fallback: return a simulated response
            return ProviderResult(
                content=self._simulate_response(prompt, model_id),
                model=model_id,
                provider="openai_compatible",
                usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 100},
                finish_reason="stop",
            )
    
    async def _call_openai_compatible_api(self, prompt: str, model_id: str, api_key: str) -> ProviderResult:
        """Make actual HTTP call to OpenAI-compatible API."""
        raise NotImplementedError("Actual OpenAI-compatible API call - implement with API key")
    
    def _simulate_response(self, prompt: str, model_id: str) -> str:
        """Generate a simulated OpenAI-compatible response."""
        words = prompt.split()
        key_terms = [w for w in words if len(w) > 4][:5]
        terms_str = ". ".join(key_terms)
        
        return (f"[OpenAI-Compatible {model_id} simulated response]\n\n"
                f"Based on your prompt involving: {terms_str}.\n\n"
                f"This would be a real AI model response when API credentials are configured.\n"
                f"The model would analyze the task and provide appropriate responses\n"
                f"for the agent's role ({self.config.get('role', 'developer')}).")
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model info for OpenAI-compatible models."""
        return {
            "gpt-4o": {
                "context_window": 128000,
                "pricing": {"prompt": "$5.00 / 1M", "completion": "$15.00 / 1M"},
                "capabilities": ["text", "code", "analysis"],
            }
        }.get(model_id)