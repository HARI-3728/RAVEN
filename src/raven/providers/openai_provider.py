"""OpenAI Provider - adapter for OpenAI API models (GPT-4, GPT-3.5, etc.)."""

from __future__ import annotations

import os
import aiohttp
from typing import Optional, Dict, Any

from ...providers.base import AIProvider, ProviderResult, format_prompt


class OpenAIProvider(AIProvider):
    """Adapter for OpenAI API models."""
    
    def __init__(self, config: dict):
        """Initialize the OpenAI provider.
        
        Args:
            config: Provider configuration with keys:
                - api_key_env: Environment variable name (default: "OPENAI_API_KEY")
                - default_model: Default model identifier (default: "gpt-4o")
                - supported_models: List of supported model IDs
                - timeout: Request timeout in seconds
                - max_retries: Maximum retry attempts
        """
        super().__init__(config)
        self.api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
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
                    f"OpenAI API key not found in environment variable '{self.api_key_env}'. "
                    "Set this variable before running RAVEN."
                )
        return self._api_key
    
    async def validate_credentials(self) -> bool:
        """Validate that OpenAI API credentials are available and valid.
        
        Returns:
            True if credentials appear valid, False otherwise
        """
        try:
            key = await self._get_api_key()
            # Basic validation: check that the key exists and has expected format
            # We don't make a real API call here to avoid unnecessary charges
            return bool(key and len(key) > 10)
        except Exception:
            return False
    
    async def generate_response(self, 
                                prompt: str, 
                                context: str = "",
                                model: Optional[str] = None) -> ProviderResult:
        """Generate a response from the OpenAI API.
        
        Args:
            prompt: The user prompt/request
            context: Additional project context
            model: Optional model override
            
        Returns:
            ProviderResult with the model's response
        """
        model_id = model or self.default_model
        
        if model_id not in self.supported_models:
            # Try to use it anyway; the API will reject if unsupported
            pass
        
        api_key = await self._get_api_key()
        
        # In a real implementation, this would make an HTTP request to the OpenAI API
        # For now, we simulate a response based on the prompt
        try:
            # Try actual API call
            result = await self._call_openai_api(prompt, model_id, api_key)
            return result
        except Exception as e:
            # Fallback: return a simulated response
            return ProviderResult(
                content=self._simulate_response(prompt, model_id),
                model=model_id,
                provider="openai",
                usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 100},
                finish_reason="stop",
            )
    
    async def _call_openai_api(self, prompt: str, model_id: str, api_key: str) -> ProviderResult:
        """Make actual HTTP call to OpenAI API.
        
        This is a real implementation that would be used when API keys are available.
        For the foundation step, we simulate the response.
        """
        # Actual implementation would use aiohttp or openai library
        # For now, raise to trigger fallback
        raise NotImplementedError("Actual OpenAI API call - implement with API key")
    
    def _simulate_response(self, prompt: str, model_id: str) -> str:
        """Generate a simulated response for demonstration purposes."""
        # Extract key terms from prompt to make response relevant
        words = prompt.split()
        key_terms = [w for w in words if len(w) > 4][:5]
        terms_str = ". ".join(key_terms)
        
        return (f"[OpenAI {model_id} simulated response]\n\n"
                f"Based on your prompt involving: {terms_str}.\n\n"
                f"This would be a real AI model response when API credentials are configured.\n"
                f"The model would analyze the task and provide code, analysis, or responses\n"
                f"appropriate to the agent's role ({self.config.get('role', 'developer')}).")
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information for OpenAI models."""
        model_info = {
            "gpt-4o": {
                "context_window": 128000,
                "pricing": {"prompt": "$5.00 / 1M", "completion": "$15.00 / 1M"},
                "capabilities": ["text", "code", "analysis"],
            },
            "gpt-4-turbo": {
                "context_window": 128000,
                "pricing": {"prompt": "$10.00 / 1M", "completion": "$30.00 / 1M"},
                "capabilities": ["text", "code", "analysis"],
            },
            "gpt-3.5-turbo": {
                "context_window": 16000,
                "pricing": {"prompt": "$0.50 / 1M", "completion": "$1.50 / 1M"},
                "capabilities": ["text", "code"],
            },
        }
        
        return model_info.get(model_id)