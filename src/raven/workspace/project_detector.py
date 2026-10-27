"""Project Detector - detects project type, configuration, and relevant files."""

from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class ProjectDetector:
    """Detects project type, configuration, and relevant files."""
    
    def __init__(self, project_root: str):
        """Initialize the project detector.
        
        Args:
            project_root: Root directory of the project to detect
        """
        self.project_root = os.path.abspath(project_root)
    
    def detect_project_type(self) -> str:
        """Detect the type of project."""
        # Check for common project indicators
        indicators = {
            "python": self._check_python_project,
            "node": self._check_node_project,
            "rust": self._check_rust_project,
            "go": self._check_go_project,
            "java": self._check_java_project,
        }
        
        for project_type, check_func in indicators.items():
            if check_func():
                return project_type
        
        return "generic"
    
    def _check_python_project(self) -> bool:
        """Check if this is a Python project."""
        return (
            Path(self.project_root).joinpath("pyproject.toml").exists()
            or Path(self.project_root).joinpath("setup.py").exists()
            or Path(self.project_root).joinpath("setup.cfg").exists()
            or any(f.endswith(".py") for f in Path(self.project_root).glob("*.py"))
        )
    
    def _check_node_project(self) -> bool:
        """Check if this is a Node.js project."""
        return Path(self.project_root).joinpath("package.json").exists()
    
    def _check_rust_project(self) -> bool:
        """Check if this is a Rust project."""
        return Path(self.project_root).joinpath("Cargo.toml").exists()
    
    def _check_go_project(self) -> bool:
        """Check if this is a Go project."""
        return Path(self.project_root).joinpath("go.mod").exists()
    
    def _check_java_project(self) -> bool:
        """Check if this is a Java project."""
        return Path(self.project_root).joinpath("pom.xml").exists() or \
               Path(self.project_root).joinpath("build.gradle").exists()
    
    def detect_configurations(self) -> Dict[str, Any]:
        """Detect existing RAVEN configurations in the project."""
        configs = {}
        
        # Look for RAVEN config files
        config_files = [
            "raven/config.yaml",
            ".ravenconfig",
            "raves config.yaml",
        ]
        
        for cf in config_files:
            path = Path(self.project_root) / cf
            if path.exists():
                try:
                    with open(path) as f:
                        configs[cf] = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
        
        # Look for existing RAVEN session
        session_path = Path(self.project_root) / ".raven" / "session.json"
        if session_path.exists():
            try:
                with open(session_path) as f:
                    configs["session"] = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return configs
    
    def get_project_context(self) -> dict:
        """Get project context dictionary for agent prompting."""
        return {
            "project_root": self.project_root,
            "project_type": self.detect_project_type(),
            "has_git": self._has_git(),
            "configurations": self.detect_configurations(),
        }
    
    def _has_git(self) -> bool:
        """Check if the project has git."""
        try:
            proc = asyncio.create_subprocess_exec(
                "git", "rev-parse", "--is-inside-work-tree",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            asyncio.get_event_loop().run_until_complete(
                asyncio.wait_for(proc.communicate(), timeout=2)
            )
            return proc.returncode == 0
        except Exception:
            return False