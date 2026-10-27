"""Path Validator - validates file paths for security boundaries, prevents path traversal."""

from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Optional, Tuple


class PathValidator:
    """Validates file paths for security boundaries, preventing path traversal and unauthorized access."""
    
    def __init__(self, project_root: str):
        """Initialize the path validator.
        
        Args:
            project_root: The project root directory for boundary checking
        """
        self.project_root = os.path.abspath(project_root)
        self._real_project_root = os.path.realpath(self.project_root)
    
    def _resolve_and_validate(self, path: str) -> Tuple[Optional[str], bool]:
        """Resolve a path and check it's within project boundaries.
        
        Returns:
            (resolved_path, is_safe) tuple
        """
        # Normalize the path
        normalized = os.path.normpath(path)
        
        # Check for path traversal attempts
        # Reject paths that go above project root
        # Normalize and resolve
        try:
            resolved = os.path.realpath(os.path.join(self.project_root, normalized))
        except Exception:
            return None, False
        
        # Check if resolved path is within project root
        is_safe = resolved.startswith(self._real_project_root + os.sep) or resolved == self._real_project_root
        
        return (resolved if is_safe else None, is_safe)
    
    def validate_read(self, path: str, allow_directory: bool = True) -> Tuple[bool, Optional[str], str]:
        """Validate that a file or directory read operation is permitted.
        
        Args:
            path: File or directory path to read (relative or absolute)
            allow_directory: Whether directory paths are accepted
            
        Returns:
            (is_allowed, resolved_path, reason) tuple
        """
        resolved, is_safe = self._resolve_and_validate(path)
        if not is_safe or not resolved:
            return False, None, f"Path traversal detected: {path} escapes project boundary"
        
        if not os.path.exists(resolved):
            return False, None, f"Path not found: {path}"
            
        if not allow_directory and os.path.isdir(resolved):
            return False, None, f"Expected file, found directory: {path}"
        
        return True, resolved, ""
    
    def validate_write(self, path: str, allow_overwrite: bool = True) -> Tuple[bool, Optional[str], str]:
        """Validate that a file write operation is permitted.
        
        Args:
            path: File path to write (relative or absolute)
            allow_overwrite: Whether overwriting/modifying an existing file is allowed
            
        Returns:
            (is_allowed, resolved_path, reason) tuple
        """
        resolved, is_safe = self._resolve_and_validate(path)
        if not is_safe or not resolved:
            return False, None, f"Path traversal detected: {path} escapes project boundary"

        # Check parent directory exists or can be created
        parent_dir = os.path.dirname(resolved)
        if parent_dir and not os.path.isdir(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                return False, None, f"Cannot create parent directory: {str(e)}"

        if os.path.exists(resolved) and not allow_overwrite:
            return False, None, f"File already exists: {path}. Overwriting not allowed."

        return True, resolved, ""
    
    def validate_delete(self, path: str) -> Tuple[bool, Optional[str], str]:
        """Validate that a file delete operation is permitted.
        
        Args:
            path: File path to delete (relative or absolute)
            
        Returns:
            (is_allowed, resolved_path, reason) tuple
        """
        # Handle absolute paths
        if os.path.isabs(path):
            resolved, is_safe = self._resolve_and_validate(path)
            if not is_safe:
                return False, None, f"Path traversal detected: {path} escapes project boundary"
            return True, resolved, ""
        
        # Relative path - resolve relative to project root
        resolved, is_safe = self._resolve_and_validate(os.path.join(self.project_root, path))
        if not is_safe:
            return False, None, f"Path traversal detected: {path} escapes project boundary"
        
        if not os.path.exists(resolved):
            return False, None, f"File not found: {path}"
        
        # Prevent deletion of critical project files
        critical_names = {"raven", "config", "session", "database", ".env"}
        basename = os.path.basename(resolved).lower()
        if basename in critical_names:
            return False, None, f"Protected file cannot be deleted: {path}"
        
        return True, resolved, ""
    
    def validate_edit(self, path: str, backup: bool = True) -> Tuple[bool, Optional[str], str]:
        """Validate that a file edit operation is permitted.
        
        Args:
            path: File path to edit
            backup: Whether to create a backup before editing
            
        Returns:
            (is_allowed, resolved_path, reason) tuple
        """
        # For editing, we allow modification of existing files within project
        if os.path.isabs(path):
            resolved, is_safe = self._resolve_and_validate(path)
            if not is_safe:
                return False, None, f"Path traversal detected: {path} escapes project boundary"
            if not os.path.exists(resolved):
                return False, None, f"File not found: {path}"
            return True, resolved, ""
        
        # Relative path
        resolved, is_safe = self._resolve_and_validate(os.path.join(self.project_root, path))
        if not is_safe:
            return False, None, f"Path traversal detected: {path} escapes project boundary"
        
        if not os.path.exists(resolved):
            return False, None, f"File not found: {path}"
        
        return True, resolved, ""
    
    def get_project_root(self) -> str:
        """Get the project root directory."""
        return self.project_root