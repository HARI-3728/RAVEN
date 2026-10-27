"""Errors - custom error types and error handling framework for RAVEN."""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import enum


class ErrorCategory(enum.Enum):
    """Categories of errors that can occur in RAVEN."""
    PROVIDER = "provider"           # AI provider/API errors
    VALIDATION = "validation"       # Configuration/validation errors
    SECURITY = "security"           # Security/approval errors
    FILESYSTEM = "filesystem"       # File operation errors
    GIT = "git"                     # Git operation errors
    TASK = "task"                   # Task execution errors
    TIMEOUT = "timeout"             # Timeout errors
    INTEGRATION = "integration"     # CLI/API integration errors
    CONFIGURATION = "configuration" # Configuration errors


class ErrorSeverity(enum.Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RAVENError:
    """Base error data class for RAVEN."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    error_id: str
    timestamp: float
    context: Dict[str, Any] = None
    retryable: bool = False
    original_error: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        base = {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "error_id": self.error_id,
            "timestamp": self.timestamp,
            "retryable": self.retryable,
        }
        if self.context:
            base["context"] = self.context
        if self.original_error:
            base["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error),
            }
        return base
    
    def __str__(self) -> str:
        """String representation of the error."""
        retry_str = " [RETRY]" if self.retryable else ""
        return f"[{self.category.value.upper()}] {self.message}{retry_str}"


class ErrorHandler:
    """Handles error processing, logging, and retry decisions."""
    
    def __init__(self, logger: Any = None):
        """Initialize the error handler."""
        self.logger = logger
        self.error_history: List[RAVENError] = []
    
    def handle(self, error: Exception, 
               category: ErrorCategory,
               severity: ErrorSeverity = ErrorSeverity.MEDIUM,
               context: Dict[str, Any] = None,
               retryable: bool = False) -> RAVENError:
        """Process and log an error.
        
        Args:
            error: The exception that occurred
            category: Error category
            severity: Error severity
            context: Additional context about the error
            retryable: Whether this error should trigger retries
            
        Returns:
            RAVENError instance with full details
        """
        error_id = f"{category.value}_{id(error)}"
        raven_error = RAVENError(
            category=category,
            severity=severity,
            message=str(error),
            error_id=error_id,
            timestamp=__import__("time").time(),
            context=context or {},
            retryable=retryable,
            original_error=error,
        )
        
        # Log the error
        if self.logger:
            self.logger.error(
                f"Error {error_id}: {str(error)}",
                extra={"context": context, "category": category.value}
            )
        
        # Store in history
        self.error_history.append(raven_error)
        
        # Keep history manageable
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
        
        return raven_error
    
    def should_retry(self, raven_error: RAVENError, max_retries: int = 2) -> bool:
        """Determine if an error should trigger a retry attempt.
        
        Args:
            raven_error: The RAVENError to evaluate
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if the error is retryable and within retry limits
        """
        return (
            raven_error.retryable
            and raven_error.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)
            and len([e for e in self.error_history if e.retryable]) < max_retries
        )
    
    def get_recent_errors(self, count: int = 10) -> List[RAVENError]:
        """Get the most recent errors."""
        return self.error_history[-count:] if self.error_history else []


# Common error instances for quick use
def provider_error(message: str, original: Exception = None, **context) -> RAVENError:
    """Create a provider-related error."""
    handler = ErrorHandler()
    return handler.handle(
        original or Exception(message),
        category=ErrorCategory.PROVIDER,
        severity=ErrorSeverity.HIGH,
        context=context,
        retryable=original is not None and "rate limit" in str(original).lower(),
    )


def validation_error(message: str, **context) -> RAVENError:
    """Create a validation error."""
    handler = ErrorHandler()
    return handler.handle(
        Exception(message),
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.MEDIUM,
        context=context,
        retryable=False,
    )


def security_error(message: str, **context) -> RAVENError:
    """Create a security-related error."""
    handler = ErrorHandler()
    return handler.handle(
        Exception(message),
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.HIGH,
        context=context,
        retryable=False,
    )


def filesystem_error(message: str, **context) -> RAVENError:
    """Create a filesystem error."""
    handler = ErrorHandler()
    return handler.handle(
        Exception(message),
        category=ErrorCategory.FILESYSTEM,
        severity=ErrorSeverity.MEDIUM,
        context=context,
        retryable=True,
    )


def timeout_error(message: str, **context) -> RAVENError:
    """Create a timeout error."""
    handler = ErrorHandler()
    return handler.handle(
        Exception(message),
        category=ErrorCategory.TIMEOUT,
        severity=ErrorSeverity.HIGH,
        context=context,
        retryable=True,
    )