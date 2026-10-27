"""Codex CLI Integration - adapter for Codex CLI integration."""

from __future__ import annotations

import os
import shutil
import subprocess
import asyncio
from typing import Optional, Dict, Any

from .base import IntegrationBase, SubprocessManager


class CodexCLIIntegration(IntegrationBase):
    """Adapter for Codex CLI integration.
    
    Detects whether Codex CLI is installed and provides execution interface.
    """
    
    def __init__(self, config: dict = None):
        """Initialize the Codex CLI integration."""
        super().__init__(config)
        self.codex_path: Optional[str] = None
        self._manager = SubprocessManager(timeout=120)
    
    def detect(self) -> bool:
        """Detect whether Codex CLI is installed.
        
        Returns:
            True if codex is available, False otherwise
        """
        possible_paths = [
            "codex",  # In PATH
            "/usr/local/bin/codex",
            "/usr/bin/codex",
            os.path.expanduser("~/bin/codex"),
            os.path.expanduser("~/.local/bin/codex"),
        ]
        
        for path in possible_paths:
            resolved = shutil.which(path) or (path if os.path.isfile(path) else None)
            if resolved:
                self.codex_path = resolved
                self.installed = True
                return True
        
        # Try running --version
        try:
            res = subprocess.run(
                ["codex", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_output = (res.stdout + res.stderr).strip().lower()
            if "codex" in version_output:
                self.codex_path = "codex"
                self.installed = True
                return True
        except Exception:
            pass
        
        self.installed = False
        return False
    
    async def _path_exists(self, path: str) -> bool:
        """Check if a path exists."""
        try:
            proc = asyncio.create_subprocess_exec(
                "test", "-f", path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subrupt.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=1)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def execute(self, command: str, **kwargs) -> dict:
        """Execute a command through Codex CLI.
        
        Args:
            command: The Codex command to execute
            **kwargs: Additional parameters (project_dir, etc.)
            
        Returns:
            Execution result dict
        """
        if not self.installed:
            if not self.detect():
                return {
                    "output": "",
                    "errors": "Codex CLI not installed",
                    "exit_code": -1,
                    "timed_out": False,
                }
        
        project_dir = kwargs.get("project_dir", os.getcwd())
        
        # Build the codex command
        cmd = ["codex", command]
        
        # Add project directory if specified
        if project_dir and project_dir != os.getcwd():
            cmd.extend(["--dir", project_dir])
        
        return await self._manager.run(cmd, cwd=project_dir)
    
    def parse_output(self, raw_output: str) -> dict:
        """Parse Codex CLI tool output."""
        result = {
            "raw": raw_output,
            "commands": [],
            "errors": [],
            "summary": "",
        }
        
        # Try to extract JSON sections
        import json
        import re
        
        json_pattern = r'\{[^}]+\}'
        matches = re.findall(json_pattern, raw_output)
        
        for match in matches:
            try:
                parsed = json.loads(match)
                result["commands"].extend(parsed.get("commands", []))
                result["errors"].extend(parsed.get("errors", []))
                if not result["summary"] and "summary" in parsed:
                    result["summary"] = parsed["summary"]
            except json.JSONDecodeError:
                pass
        
        # Basic text fallback
        if not result["commands"] and not result["errors"]:
            lines = raw_output.strip().split("\n")
            if lines:
                result["summary"] = lines[0]
        
        return result