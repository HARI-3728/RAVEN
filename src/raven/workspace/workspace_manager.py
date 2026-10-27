"""Workspace Manager - high-level workspace lifecycle management."""

from __future__ import annotations

import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from ..tools.filesystem import FileSystemTools
from .project_detector import ProjectDetector
from .file_indexer import FileIndexer


class WorkspaceManager:
    """High-level workspace lifecycle management."""
    
    def __init__(self, project_root: str):
        """Initialize the workspace manager.
        
        Args:
            project_root: Root directory of the workspace
        """
        self.project_root = os.path.abspath(project_root)
        self.detector = ProjectDetector(self.project_root)
        self.fs_tools = FileSystemTools(self.project_root)
        self.file_indexer = FileIndexer(self.project_root)
        self.context: dict = {}
    
    async def initialize(self) -> dict:
        """Initialize the workspace and gather context.
        
        Returns:
            Dict with workspace initialization results
        """
        # Detect project type
        project_type = self.detector.detect_project_type()
        
        # Detect configurations
        configurations = self.detector.detect_configurations()
        
        # Index files
        index = self.file_indexer.index_files()
        
        # Get project context
        self.context = self.detector.get_project_context()
        
        return {
            "project_root": self.project_root,
            "project_type": project_type,
            "indexed_files": len(self.indexer.get_indexed_files()),
            "has_git": self.detector._has_git(),
            "configurations": configurations,
            "context": self.context,
        }
    
    async def update_context(self) -> dict:
        """Update workspace context (e.g., after git changes).
        
        Returns:
            Updated context dict
        """
        # Re-index files
        self.file_indexer.index_files()
        
        # Update detector context
        self.context = self.detector.get_project_context()
        
        return self.context
    
    def get_context(self) -> dict:
        """Get the current workspace context for agent prompting."""
        return self.context
    
    def get_file_indexer(self) -> FileIndexer:
        """Get the file indexer instance."""
        return self.file_indexer