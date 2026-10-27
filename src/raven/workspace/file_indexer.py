"""File Indexer - indexes project files for agent context provision."""

from __future__ import annotations

import os
import fnmatch
from typing import Dict, List, Set, Any
from pathlib import Path


class FileIndexer:
    """Indexes project files for agent context provision."""
    
    def __init__(self, project_root: str, 
                 excluded_patterns: Optional[List[str]] = None,
                 max_file_size: int = 100000):
        """Initialize the file indexer.
        
        Args:
            project_root: Root directory to index
            excluded_patterns: Optional glob patterns to exclude
            max_file_size: Maximum file size to include (bytes)
        """
        self.project_root = os.path.abspath(project_root)
        self.excluded_patterns = excluded_patterns or [
            "*.pyc", "__pycache__", ".git/", "node_modules/", 
            ".venv/", "*.egg-info/", ".svn/"
        ]
        self.max_file_size = max_file_size
        self.index: Dict[str, dict] = {}
    
    def index_files(self, 
                    recursion: bool = True,
                    include_patterns: Optional[List[str]] = None) -> Dict[str, dict]:
        """Index all project files.
        
        Args:
            recursion: Whether to recurse into subdirectories
            include_patterns: Optional include glob patterns
            
        Returns:
            Dict mapping file paths to metadata
        """
        self.index = {}
        project_path = Path(self.project_root)
        
        if recursion:
            files = project_path.rglob("*")
        else:
            files = project_path.iterdir()
        
        for file_path in files:
            # Skip if not a file
            if not file_path.is_file():
                continue
            
            # Check exclusion patterns
            if self._is_excluded(file_path.name):
                continue
            
            # Check include patterns
            if include_patterns and not any(fnmatch.fnmatch(file_path.name, p) for p in include_patterns):
                continue
            
            # Check file size
            try:
                file_size = file_path.stat().st_size
                if file_size > self.max_file_size:
                    # Store metadata only, not content
                    self.index[str(file_path.relative_to(self.project_root))] = {
                        "path": str(file_path.relative_to(self.project_root)),
                        "size": file_size,
                        "type": "large_file",
                        "extension": file_path.suffix,
                    }
                    continue
            except OSError:
                continue
            
            # Store file metadata
            self.index[str(file_path.relative_to(self.project_root))] = {
                "path": str(file_path.relative_to(self.project_root)),
                "size": file_size if 'file_size' in dir() else 0,
                "type": "source_file",
                "extension": file_path.suffix,
                "modified": file_path.stat().st_mtime,
            }
        
        return self.index
    
    def _is_excluded(self, filename: str) -> bool:
        """Check if a file should be excluded."""
        for pattern in self.excluded_patterns:
            if fnmatch.fnmatch(filename, pattern) or pattern in filename:
                return True
        return False
    
    def get_file_content(self, relative_path: str, max_chars: int = 5000) -> Optional[str]:
        """Get file content with size limit.
        
        Args:
            relative_path: Path relative to project root
            max_chars: Maximum characters to read
            
        Returns:
            File content or None if unable to read
        """
        full_path = Path(self.project_root) / relative_path
        
        if not full_path.exists():
            return None
        
        try:
            file_size = full_path.stat().st_size
            if file_size > self.max_file_size:
                return None  # Too large to read
            
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
                # Truncate with indicator if needed
                if file_size > max_chars:
                    content += f"\n... (truncated at {max_chars} chars of {file_size})"
                return content
        except (IOError, OSError, UnicodeDecodeError):
            return None
    
    def get_indexed_files(self) -> List[str]:
        """Get list of all indexed file paths."""
        return list(self.index.keys())