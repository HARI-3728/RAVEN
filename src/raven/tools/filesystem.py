"""Filesystem Tools - file system operations with safety guards and path validation."""

from __future__ import annotations

import os
import shutil
import asyncio
from typing import Dict, Any, List, Optional
import sys

# Import PathValidator directly from its module path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from raven.security.path_validator import PathValidator


class FileSystemTools:
    """File system operations with safety guards and path validation."""
    
    def __init__(self, project_root: str, path_validator: Optional[PathValidator] = None):
        """Initialize filesystem tools.
        
        Args:
            project_root: The project root directory for boundary checking
            path_validator: Optional PathValidator instance
        """
        self.project_root = os.path.abspath(project_root)
        self.path_validator = path_validator or PathValidator(project_root)