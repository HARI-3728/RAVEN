"""Claude Code Integration - adapter for Claude Code CLI integration."""

from __future__ import annotations

import os
import asyncio
from typing import Optional, Dict, Any

from ...integrations.base import IntegrationBase, SubprocessManager


class ClaudeCodeIntegration(IntegrationBase):
    """Adapter for Claude Code CLI integration.
    
    Detects whether Claude Code is installed and provides execution interface.
    """
    
    def __init__(self, config: dict = None):
        """Initialize the Claude Code integration."""
        super().__init__(config)
        self.claude_code_path: Optional[str] = None
        self._manager = SubprocessManager(timeout=120)
    
    def detect(self) -> bool:
        """Detect whether Claude Code CLI is installed.
        
        Returns:
            True if claude-code is available, False otherwise
        """
        # Check common installation paths
        possible_paths = [
            "claude-code",  # In PATH
            "/usr/local/bin/claude-code",
            "/usr/bin/claude-code",
            os.path.expanduser("~/bin/claude-code"),
            os.path.expanduser("~/.local/bin/claude-code"),
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) or await self._path_exists(path):
                self.claude_code_path = path
                self.installed = True
                return True
        
        # Try running --version
        try:
            proc = asyncio.create_subprocess_exec(
                "claude-code", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = asyncio.get_event_loop().run_until_complete(
                asyncio.wait_for(proc.communicate(), timeout=5)
            )
            version_output = stderr.decode().strip()
            if "claude-code" in version_output.lower() or "anthropic" in version_output.lower():
                self.claude_code_path = "claude-code"
                self.installed = True
                return True
        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            pass
        
        self.installed = False
        return False
    
    async def _path_exists(self, path: str) -> bool:
        """Check if a path exists."""
        try:
            proc = asyncio.create_subprocess_exec(
                "test", "-f", path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=1)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def execute(self, command: str, **kwargs) -> dict:
        """Execute a command through Claude Code CLI.
        
        Args:
            command: The Claude Code command to execute
            **kwargs: Additional parameters (project_dir, etc.)
            
        Returns:
            Execution result dict
        """
        if not self.installed:
            if not self.detect():
                return {
                    "output": "",
                    "errors": "Claude Code CLI not installed",
                    "exit_code": -1,
                    "timed_out": False,
                }
        
        project_dir = kwargs.get("project_dir", os.getcwd())
        
        # Build the claude-code command
        cmd = ["claude-code", command]
        
        # Add project directory if specified
        if project_dir and project_dir != os.getcwd():
            cmd.extend(["--project", project_dir])
        
        return await self._manager.run(cmd, cwd=project_dir)
    
    def parse_output(self, raw_output: str) -> dict:
        """Parse Claude Code tool output.
        
        Args:
            raw_output: Raw stdout from Claude Code CLI
            
        Returns:
            Parsed structured output
        """
        # Claude Code outputs structured JSON and text
        result = {
            "raw": raw_output,
            "commands": [],
            "errors": [],
            "summary": "",
        }
        
        # Try to extract JSON sections
        import json
        import re
        
        # Look for JSON blocks
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
        
        # If no JSON found, do basic text parsing
        if not result["commands"] and not result["errors"]:
            lines = raw_output.strip().split("\n")
            if lines:
                result["summary"] = lines[0]
        
        return result