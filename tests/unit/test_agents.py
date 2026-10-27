"""Unit tests for RAVEN Provider system.

Tests the shared async provider interface with:
- Connection validation
- Model availability checks
- Request submission
- Response handling
- Timeouts and cancellation
- Normalized errors and usage metadata
Uses mocked providers - no paid API keys required.
"""
from __future__ import annotations

import pytest
import asyncio

from raven.providers.base import AsyncProviderInterface, ProviderCapabilities, ProviderError, ProviderErrorType
from raven.providers.registry import ProviderRegistry
from raven.security.secrets_manager import SecretsManager


class TestProviderError:
    """Test ProviderError normalization."""

    def test_provider_error_creation(self):
        """Test creating ProviderError with type."""
        error = ProviderError(
            message="Test error message",
            error_type="RATE_LIMIT",
        )
        assert str(error) == "Test error message"
        assert error.error_type == "RATE_LIMIT"
    
    def test_provider_error_with_details(self):
        """Test ProviderError with additional details."""
        error = ProviderError(
            message="Rate limit exceeded",
            error_type="RATE_LIMIT",
            details={"retry_after": 30, "limit": 1000},
        )
        assert error.details["retry_after"] == 30
        assert error.details["limit"] == 1000
    
    def test_provider_error_types(self):
        """Test all ProviderErrorType values."""
        from raven.providers.base import ProviderErrorType
        
        types = ["API_ERROR", "RATE_LIMIT",
                 "INVALID_REQUEST", "AUTHENTICATION",
                 "TIMEOUT", "NOT_FOUND",
                 "TOO_MANY_REQUESTS"]
        for t in types:
            error = ProviderError(message="test", error_type=ProviderErrorType[t])
            assert error.error_type == ProviderErrorType[t]