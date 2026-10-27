"""Provider Base - common interface for all AI model providers.

Defines the contract that all provider adapters must conform to.
"""

from __future__ import annotations

import abc
import asyncio
import time
from enum import Enum
from typing import Dict, Any, Optional, List

import warnings

# Custom exception hierarchy for provider errors
class ProviderErrorType(str, Enum):
    """Enumeration of provider error types."""
    API_ERROR = "API_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHENTICATION = "AUTHENTICATION"
    TIMEOUT = "TIMEOUT"
    NOT_FOUND = "NOT_FOUND"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"

class ProviderError(Exception):
    """Base exception for all provider-related errors."""
    
    def __init__(self, message: str = "", error_type: ProviderErrorType = ProviderErrorType.API_ERROR, details: Optional[Dict[str, Any]] = None):
        """Initialize ProviderError.
        
        Args:
            message: Error message description
            error_type: Type of error (ProviderErrorType enum)
            details: Additional error details dictionary
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}


class CredentialError(ProviderError):
    """Raised when API credentials are invalid or missing."""
    pass

class ModelNotFoundError(ProviderError):
    """Raised when a requested model is not supported or available."""
    pass

class TimeoutError(ProviderError):
    """Raised when a provider request times out."""
    pass

class RateLimitError(ProviderError):
    """Raised when provider rate limits are exceeded."""
    pass

class ProviderConnectionError(ProviderError):
    """Raised when provider connection fails."""
    pass

class ProviderResult:
    """Structured result from a provider call.
    
    Contains the model's response along with metadata about token usage,
    finish reasons, and the raw response for debugging.
    """
    
    __slots__ = ('content', 'model', 'provider', 'usage', 'finish_reason', 'raw_response', 'error', 'latency', '_success')
    
    def __init__(
        self,
        content: Optional[str] = None,
        model: str = "",
        provider: str = "",
        usage: Optional[Dict[str, Any]] = None,
        finish_reason: Optional[str] = None,
        raw_response: Optional[Any] = None,
        error: Optional[ProviderError] = None,
        latency: Optional[float] = None,
        success: Optional[bool] = None,
    ):
        """Initialize ProviderResult.
        
        Args:
            content: The model's text response
            model: The model identifier that was used
            provider: The provider name
            usage: Token usage information (if available)
            finish_reason: Why the model stopped generating
            raw_response: The raw API response for debugging
            error: ProviderError if the call failed
            latency: Time taken for the request in seconds
            success: Explicit success override flag
        """
        self.content = content if content is not None else ""
        self.model = model
        self.provider = provider
        self.usage = usage or {}
        self.finish_reason = finish_reason
        self.raw_response = raw_response
        self.error = error
        self.latency = latency
        self._success = success
    
    @property
    def success(self) -> bool:
        """Check if the provider call was successful (no error)."""
        if self._success is not None:
            return self._success
        return self.error is None
    
    @property
    def has_content(self) -> bool:
        """Check if the result contains meaningful content."""
        return bool(self.content and self.content.strip())


    def __str__(self) -> str:
        if self.error:
            return f"ProviderResult(error={self.error}, model={self.model})"
        return f"ProviderResult(content={self.content[:80] if self.content else ''}..., model={self.model})"
    
    def __repr__(self) -> str:
        return (f"ProviderResult(content={self.content!r}, model={self.model!r}, "
                f"provider={self.provider!r}, success={self.success}, "
                f"latency={self.latency})")


def format_prompt(system: str = "", user: str = "") -> str:
    """Format a system/user prompt pair."""
    if system and system.strip():
        return f"System: {system}\nUser: {user}"
    return user


from enum import Enum

class ProviderCapabilities:
    """Capabilities of an AI provider.
    
    Defines what features a provider supports, such as tool use,
    streaming, vision, and function calling.
    """
    
    def __init__(
        self,
        supports_tools: bool = False,
        supports_streaming: bool = False,
        max_tokens: Optional[int] = None,
        supports_vision: bool = False,
        supports_function_calling: bool = False,
    ):
        """Initialize provider capabilities.
        
        Args:
            supports_tools: Whether the provider supports tool use
            supports_streaming: Whether the provider supports streaming responses
            max_tokens: Maximum number of tokens the provider supports
            supports_vision: Whether the provider supports vision/multimodal inputs
            supports_function_calling: Whether the provider supports function calling
        """
        self.supports_tools = supports_tools
        self.supports_streaming = supports_streaming
        self.max_tokens = max_tokens
        self.supports_vision = supports_vision
        self.supports_function_calling = supports_function_calling
    
    def __bool__(self) -> bool:
        """Check if the provider has any capabilities enabled."""
        return any([
            self.supports_tools,
            self.supports_streaming,
            self.max_tokens is not None,
            self.supports_vision,
            self.supports_function_calling,
        ])


class AsyncProviderInterface(abc.ABC):
    """Abstract interface for async AI providers.
    
    All async provider adapters must implement this interface to be compatible
    with RAVEN's orchestration system. This separates the async interface
    from the synchronous AIProvider interface.
    """
    
    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """Get the default model identifier for this provider."""
        pass
    
    @abc.abstractmethod
    def supported_models(self) -> List[str]:
        """Get list of supported model identifiers for this provider."""
        pass
    
    @abc.abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate that API credentials are available and valid."""
        pass
    
    @abc.abstractmethod
    async def _get_api_key(self) -> str:
        """Fetch API key from environment or configuration."""
        pass
    
    @abc.abstractmethod
    def _validate_key_format(self, key: str) -> bool:
        """Validate the format of an API key."""
        pass
    
    @abc.abstractmethod
    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        model: Optional[str] = None,
    ) -> ProviderResult:
        """Generate a response from the AI model."""
        pass
    
    @abc.abstractmethod
    async def _generate_response_core(
        self,
        prompt: str,
        context: str,
        model_id: str,
    ) -> ProviderResult:
        """Core implementation of response generation."""
        pass
    
    @abc.abstractmethod
    def cancel_generate_response(self) -> None:
        """Request cancellation of an in-progress response generation."""
        pass


class AIProvider(abc.ABC):
    """Common interface for all AI model providers.
    
    All provider adapters must implement this interface to be compatible
    with RAVEN's orchestration system.
    """
    
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
        self._timeout = config.get("timeout", 30)
        self._max_retries = config.get("max_retries", 2)
        self._api_key: Optional[str] = None
        self._model_cache: dict = {}  # model_id -> model_info
    
    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """Get the default model identifier for this provider."""
        pass
    
    @abc.abstractmethod
    def supported_models(self) -> List[str]:
        """Get list of supported model identifiers for this provider."""
        pass
    
    async def validate_credentials(self) -> bool:
        """Validate that API credentials are available and valid.
        
        Returns:
            True if credentials appear valid, False otherwise
        """
        try:
            key = await self._get_api_key()
            if not key:
                return False
            # Basic validation - check key format
            return self._validate_key_format(key)
        except Exception:
            return False
    
    @abc.abstractmethod
    async def _get_api_key(self) -> str:
        """Fetch API key from environment or configuration.
        
        Returns:
            The API key string
        """
        pass
    
    @abc.abstractmethod
    def _validate_key_format(self, key: str) -> bool:
        """Validate the format of an API key.
        
        Args:
            key: The API key to validate
            
        Returns:
            True if the key format appears valid
        """
        pass
    
    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        model: Optional[str] = None,
    ) -> ProviderResult:
        """Generate a response from the AI model.
        
        Args:
            prompt: The user prompt/request
            context: Additional project context
            model: Optional model override from configuration
            
        Returns:
            ProviderResult with response content and metadata
        """
        model_id = model or self.default_model
        
        # Check if model is supported
        if model_id not in self.supported_models:
            raise ModelNotFoundError(
                f"Model '{model_id}' is not supported by {self.name}. "
                f"Supported models: {self.supported_models}"
            )
        
        # Input validation
        if not prompt or not prompt.strip():
            return ProviderResult(
                content="",
                model=model_id,
                provider=self.name,
                error=ValueError("Empty prompt provided"),
            )
        
        start_time = time.time()
        
        try:
            result = await self._generate_response_core(prompt, context, model_id)
            latency = time.time() - start_time
            
            # Ensure result has proper structure
            if not isinstance(result, ProviderResult):
                result = ProviderResult(
                    content=str(result) if result else "",
                    model=model_id,
                    provider=self.name,
                    latency=latency,
                )
            else:
                result.latency = latency
            
            return result
            
        except asyncio.TimeoutError:
            latency = time.time() - start_time
            return ProviderResult(
                content="",
                model=model_id,
                provider=self.name,
                error=TimeoutError(f"Request timed out after {self._timeout}s"),
                latency=latency,
            )
        except ModelNotFoundError:
            latency = time.time() - start_time
            raise
        except Exception as e:
            latency = time.time() - start_time
            return ProviderResult(
                content="",
                model=model_id,
                provider=self.name,
                error=ProviderError(f"Provider error: {str(e)}"),
                latency=latency,
            )
    
    @abc.abstractmethod
    async def _generate_response_core(
        self,
        prompt: str,
        context: str,
        model_id: str,
    ) -> ProviderResult:
        """Core implementation of response generation.
        
        This is where the actual API call or model invocation happens.
        Must be implemented by subclasses.
        
        Args:
            prompt: The user prompt/request
            context: Additional project context
            model_id: The model identifier to use
            
        Returns:
            ProviderResult with the model's response
        """
        pass
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information and availability.
        
        Args:
            model_id: The model identifier to look up
            
        Returns:
            Dictionary with model info or None if not found
        """
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        
        # Build model info from supported models
        info = {
            "model_id": model_id,
            "provider": self.name,
            "supported": model_id in self.supported_models,
        }
        
        # Add model-specific info if available
        supported_dict = {m: self._model_info_for_model(m) for m in self.supported_models}
        if model_id in supported_dict:
            info.update(supported_dict[model_id])
        
        self._model_cache[model_id] = info
        return info
    
    @abc.abstractmethod
    def _model_info_for_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model-specific information.
        
        Args:
            model_id: The model identifier
            
        Returns:
            Dictionary with context_window, pricing, capabilities, etc.
        """
        pass
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported model identifiers for this provider."""
        return list(self.supported_models)
    
    async def generate_with_retry(
        self,
        prompt: str,
        context: str = "",
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> ProviderResult:
        """Generate a response with automatic retry on failure.
        
        Args:
            prompt: The user prompt/request
            context: Additional project context
            model: Optional model override
            max_retries: Maximum retry attempts (uses config default if None)
            
        Returns:
            ProviderResult with successful response or last error
        """
        max_retries = max_retries or self._max_retries
        last_error: Optional[ProviderResult] = None
        
        for attempt in range(max_retries + 1):
            result = await self.generate_response(prompt, context, model)
            
            # Check if successful
            if result.success:
                return result
            
            # Check if it's a retryable error
            error_type = type(result.error).__name__ if result.error else None
            retryable_errors = (
                ProviderError,
                TimeoutError,
                RateLimitError,
            )
            
            if isinstance(result.error, retryable_errors) and attempt < max_retries:
                # Exponential backoff
                backoff = min(2 ** attempt, 30)  # Max 30 second backoff
                await asyncio.sleep(backoff)
                last_error = result
                continue
            else:
                last_error = result
                break
        
        # Return last result even if it failed
        return last_error or ProviderResult(
            content="",
            model=model or self.default_model,
            provider=self.name,
            error=ProviderError("All retries exhausted"),
        )
    
    async def cancel_generate_response(self) -> None:
        """Request cancellation of an in-progress response generation.
        
        Note: Actual cancellation depends on the underlying implementation.
        This method provides a hook for subclasses to implement cancellation.
        """
        # Default implementation - can be overridden by subclasses
        # that support actual cancellation (e.g., via abort signals)
        pass
    
    def format_prompt(self, system: str, user: str) -> str:
        """Format a system/user prompt pair for this provider.
        
        Different providers have different prompt formatting requirements.
        This default implementation uses a system/user message pair.
        
        Args:
            system: System prompt/instructions
            user: User message/content
            
        Returns:
            Formatted prompt string ready for API call
        """
        return f"System: {system}\nUser: {user}"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, timeout={self._timeout}, retries={self._max_retries})>"