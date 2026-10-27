"""OpenAI Provider - adapter for OpenAI API models (GPT-4, GPT-3.5, etc.)."""

from __future__ import annotations

import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any

from ...providers.base import AIProvider, ProviderResult, ProviderError, ModelNotFoundError, TimeoutError, RateLimitError, format_prompt


class OpenAIProvider(AIProvider):
    """Adapter for OpenAI API models."""
    
    @property
    def default_model(self) -> str:
        return self.config.get("default_model", "gpt-4o")
    
    @property
    def supported_models(self) -> list:
        return self.config.get("supported_models", [
            "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"
        ])
    
    async def _get_api_key(self) -> str:
        """Fetch API key from environment if not already cached."""
        if self._api_key is None:
            self._api_key = os.environ.get(self.api_key_env)
            if not self._api_key:
                raise CredentialError(
                    f"OpenAI API key not found in environment variable '{self.api_key_env}'. "
                    "Set this variable before running RAVEN."
                )
        return self._api_key
    
    def _validate_key_format(self, key: str) -> bool:
        """Validate the format of an OpenAI API key."""
        # OpenAI keys start with 'sk-' and are typically 48+ characters
        return bool(key and key.startswith("sk-") and len(key) > 20)
    
    async def _generate_response_core(
        self,
        prompt: str,
        context: str,
        model_id: str,
    ) -> ProviderResult:
        """Make actual HTTP call to OpenAI API."""
        api_key = await self._get_api_key()
        
        # Format the prompt properly
        formatted_prompt = format_prompt(system="", user=prompt + "\n\n" + context)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        
        timeout_client = aiohttp.ClientTimeout(total=self._timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout_client) as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    # Check response status
                    if response.status == 429:
                        # Rate limit exceeded
                        error_text = await response.text()
                        raise RateLimitError(
                            f"OpenAI rate limit exceeded: {error_text}"
                        )
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise ProviderError(
                            f"OpenAI API error {response.status}: {error_text}"
                        )
                    
                    # Parse successful response
                    data = await response.json()
                    
                    if not data.get("choices"):
                        return ProviderResult(
                            content="",
                            model=model_id,
                            provider="openai",
                            usage={"prompt_tokens": 0, "completion_tokens": 0},
                            finish_reason="stop",
                            raw_response=data,
                        )
                    
                    choice = data["choices"][0]
                    content = choice.get("message", {}).get("content", "")
                    finish_reason = choice.get("finish_reason", "stop")
                    
                    usage = data.get("usage", {})
                    
                    return ProviderResult(
                        content=content or "",
                        model=model_id,
                        provider="openai",
                        usage=usage,
                        finish_reason=finish_reason,
                        raw_response=data,
                    )
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"OpenAI API request timed out after {self._timeout}s")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ProviderConnectionError(f"Connection error: {str(e)}")
        except Exception as e:
            raise ProviderError(f"OpenAI API call failed: {str(e)}")
    
    def _model_info_for_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model-specific information for OpenAI models."""
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
    
    async def validate_credentials(self) -> bool:
        """Validate that OpenAI API credentials are available and valid."""
        try:
            key = await self._get_api_key()
            if not key or not key.startswith("sk-"):
                return False
            # Try a minimal API call to validate
            # In foundation step, just check key format
            return True
        except Exception:
            return False