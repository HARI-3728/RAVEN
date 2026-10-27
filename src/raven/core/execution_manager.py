"""Execution Manager - manages agent task execution with timeouts, retries, and failure handling."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import asyncio


class ExecutionManager:
    """Manages agent task execution with timeouts, retries, and failure handling."""
    
    def __init__(self, 
                 default_timeout: int = 60,
                 max_retries: int = 2,
                 retry_delay: float = 1.0):
        """Initialize execution manager.
        
        Args:
            default_timeout: Default timeout in seconds for task execution
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    async def execute_with_timeout(
        self,
        coroutine,
        timeout: Optional[int] = None,
        task_id: str = "",
    ) -> Any:
        """Execute a coroutine with timeout and retry logic.
        
        Args:
            coroutine: The coroutine to execute
            timeout: Override default timeout in seconds
            task_id: Task ID for logging
            
        Returns:
            Result of the coroutine
            
        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
            Exception: If all retries exhausted
        """
        actual_timeout = timeout or self.default_timeout
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(coroutine, timeout=actual_timeout)
                return result
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    # Wait before retry
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise asyncio.TimeoutError(
                        f"Task {task_id} timed out after {actual_timeout}s "
                        f"and {self.max_retries + 1} attempts"
                    )
            except Exception as e:
                if attempt < self.max_retries:
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    raise
        
        # Unreachable but needed for type checking
        raise asyncio.TimeoutError(f"Task {task_id} execution failed")
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if a failed execution should be retried.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-indexed)
            
        Returns:
            True if the execution should be retried
        """
        # Retry on network-related errors, timeouts (within limit)
        # Do NOT retry on validation errors, permission errors, or client errors
        retryable_errors = (asyncio.TimeoutError, ConnectionError, TimeoutError)
        
        if isinstance(error, retryable_errors):
            return attempt < self.max_retries
        
        # Don't retry client errors or validation errors
        error_str = str(error).lower()
        if any(keyword in error_str for keyword in ["validation", "invalid", "permission", "forbidden"]):
            return False
        
        return attempt < self.max_retries