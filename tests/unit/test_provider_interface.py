"""Unit tests for RAVEN provider interface.

Tests the AIProvider abstract base class and provider result structure.
Uses mocked providers - no paid API keys required.
"""

from __future__ import annotations

import pytest
import asyncio

from raven.providers.base import (
    AIProvider, ProviderResult, ProviderError, ModelNotFoundError,
    TimeoutError, RateLimitError, CredentialError,
)
from raven.providers.base import format_prompt


class TestProviderResult:
    """Test ProviderResult structure and properties."""

    def test_provider_result_creation(self):
        """Test ProviderResult can be created with all fields."""
        result = ProviderResult(
            content="Hello, world!",
            model="gpt-4o",
            provider="openai",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop",
        )
        
        assert result.content == "Hello, world!"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"
        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 20}
        assert result.finish_reason == "stop"
        assert result.success is True
        assert result.has_content is True
    
    def test_provider_result_success_property(self):
        """Test success property."""
        success_result = ProviderResult(
            content="Test", model="m", provider="p", success=True
        )
        failure_result = ProviderResult(
            content="Test", model="m", provider="p", error=ProviderError("error")
        )
        
        assert success_result.success is True
        assert failure_result.success is False
    
    def test_provider_result_has_content(self):
        """Test has_content property."""
        with_content = ProviderResult(content="some content", model="m", provider="p")
        without_content = ProviderResult(model="m", provider="p")
        
        assert with_content.has_content is True
        assert without_content.has_content is False
    
    def test_provider_result_latency(self):
        """Test latency tracking."""
        result = ProviderResult(
            content="Test", model="m", provider="p", latency=1.5
        )
        assert result.latency == 1.5


class TestProviderErrorHierarchy:
    """Test provider exception hierarchy."""

    def test_provider_error_is_exception(self):
        """Test ProviderError is a subclass of Exception."""
        try:
            raise ProviderError("test error")
        except Exception:
            assert True  # ProviderError inherits from Exception
    
    def test_model_not_found_error(self):
        """Test ModelNotFoundError."""
        try:
            raise ModelNotFoundError("model not found")
        except ProviderError:
            assert True  # ModelNotFoundError inherits from ProviderError
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        try:
            raise TimeoutError("timed out")
        except ProviderError:
            assert True  # TimeoutError inherits from ProviderError
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        try:
            raise RateLimitError("rate limited")
        except ProviderError:
            assert True  # RateLimitError inherits from ProviderError


class TestFormatPrompt:
    """Test prompt formatting utilities."""

    def test_format_prompt_basic(self):
        """Test basic prompt formatting."""
        result = format_prompt(system="You are helpful", user="Hello")
        assert "System: You are helpful" in result
        assert "User: Hello" in result
    
    def test_format_prompt_with_context(self):
        """Test prompt formatting with context."""
        result = format_prompt(system="", user="Test prompt\n\nContext here")
        assert "Test prompt" in result
        assert "Context here" in result


class TestAIProviderAbstract:
    """Test that AIProvider cannot be instantiated directly (abstract)."""

    def test_cannot_instantiate_directly(self):
        """Test that AIProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AIProvider(config={})  # type: ignore


class MockProvider(AIProvider):
    """Mock provider for testing."""
    
    @property
    def default_model(self) -> str:
        return "mock-model"
    
    @property
    def supported_models(self) -> list:
        return ["mock-model"]
    
    async def _get_api_key(self) -> str:
        return "sk-mock-test-key"
    
    def _validate_key_format(self, key: str) -> bool:
        return key.startswith("sk-")
    
    async def _generate_response_core(
        self, prompt: str, context: str, model_id: str
    ) -> ProviderResult:
        return ProviderResult(
            content=f"Mock response to: {prompt[:30]}",
            model=model_id,
            provider=self.name,
        )
    
    def _model_info_for_model(self, model_id: str) -> Optional[dict]:
        return {"context_window": 10000, "capabilities": ["text"]}


class TestMockProvider:
    """Test mock provider implementation."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider instance."""
        return MockProvider(config={
            "api_key_env": "TEST_KEY",
            "default_model": "mock-model",
            "supported_models": ["mock-model"],
            "timeout": 30,
            "max_retries": 2,
        })
    
    def test_mock_provider_default_model(self, mock_provider):
        """Test mock provider returns correct default model."""
        assert mock_provider.default_model == "mock-model"
    
    def test_mock_provider_supported_models(self, mock_provider):
        """Test mock provider supported models."""
        assert "mock-model" in mock_provider.supported_models
    
    async def test_mock_provider_generate_response(self, mock_provider):
        """Test mock provider generates response."""
        result = await mock_provider.generate_response("Hello world")
        assert result.success is True
        assert result.content is not None
        assert result.model == "mock-model"
        assert result.provider == "mockprovider"
    
    async def test_mock_provider_generate_with_retry(self, mock_provider):
        """Test mock provider generate_with_retry."""
        result = await mock_provider.generate_with_retry("test prompt")
        assert result.success is True
    
    def test_mock_provider_get_model_info(self, mock_provider):
        """Test mock provider get_model_info."""
        info = mock_provider.get_model_info("mock-model")
        assert info is not None
        assert info["supported"] is True
    
    def test_mock_provider_get_model_info_unknown(self, mock_provider):
        """Test mock provider get_model_info for unknown model."""
        info = mock_provider.get_model_info("unknown-model")
        assert info is not None
        # Should still return a dict, just with supported=False
        assert "model_id" in info or info is None
    
    def test_mock_provider_validate_credentials(self, mock_provider):
        """Test mock provider validates credentials."""
        result = asyncio.get_event_loop().run_until_complete(mock_provider.validate_credentials())
        assert result is True
    
    def test_mock_provider_format_prompt(self, mock_provider):
        """Test mock provider format_prompt."""
        formatted = mock_provider.format_prompt(system="instruction", user="query")
        assert "instruction" in formatted
        assert "query" in formatted
    
    def test_mock_provider_generate_with_retry_success(self, mock_provider):
        """Test generate_with_retry returns on success."""
        result = asyncio.get_event_loop().run_until_complete(
            mock_provider.generate_with_retry("prompt")
        )
        assert result.success is True
    
    def test_mock_provider_cancel_generate(self, mock_provider):
        """Test cancel_generate_response."""
        asyncio.get_event_loop().run_until_complete(mock_provider.cancel_generate_response())
        # Should not raise