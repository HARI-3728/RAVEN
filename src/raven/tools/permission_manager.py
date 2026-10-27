"""Permission Manager - permission checks for file operations and shell commands."""

from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Optional
from ..security.command_validator import CommandValidator
from ..security.path_validator import PathValidator


class PermissionManager:
    """Manages permissions for file operations and shell commands."""
    
    def __init__(self, 
                 path_validator: Optional[PathValidator] = None,
                 command_validator: Optional[CommandValidator] = None):
        """Initialize permission manager."""
        self.path_validator = path_validator or PathValidator(os.getcwd())
        self.command_validator = command_validator or CommandValidator()
    
    def can_read(self, path: str) -> bool:
        """Check if reading a file is permitted."""
        valid, _, reason = self.path_validator.validate_read(path)
        return valid
    
    def can_write(self, path: str) -> bool:
        """Check if writing to a file is permitted."""
        valid, _, reason = self.path_validator.validate_write(path)
        return valid
    
    def can_execute(self, command: str, cwd: str = "") -> tuple:
        """Check if a command execution is permitted.
        
        Returns:
            (is_approved, reason) tuple
        """
        valid, reason = self.command_validator.validate(command, cwd, os.getcwd())
        return valid, reason
    
    def can_delete(self, path: str) -> bool:
        """Check if deleting a file is permitted."""
        valid, _, reason = self.path_validator.validate_delete(path)
        return valid
    
    def validate_file_operation(self, 
                                operation: str, 
                                path: str,
                                agent_id: str) -> dict:
        """Validate a file operation from an agent's perspective.
        
        Args:
            operation: Type of operation ("read", "write", "delete", "edit")
            path: File path
            agent_id: The agent requesting the operation
            
        Returns:
            Dict with validation result
        """
        # Path validation
        if operation == "read":
            valid, resolved, reason = self.path_validator.validate_read(path)
        elif operation == "write":
            valid, resolved, reason = self.path_validator.validate_write(path)
        elif operation == "delete":
            valid, resolved, reason = self.path_validator.validate_delete(path)
        elif operation == "edit":
            valid, resolved, reason = self.path_validator.validate_edit(path)
        else:
            return {"approved": False, "reason": f"Unknown operation: {operation}"}
        
        return {
            "approved": valid,
            "reason": reason or "",
            "resolved_path": resolved,
        }