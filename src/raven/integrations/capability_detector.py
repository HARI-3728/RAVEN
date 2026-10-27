"""Capability Detector - detects available CLI tools and their versions."""

from __future__ import annotations

import asyncio
from typing import Dict, Any, Optional
import subprocess


class CapabilityDetector:
    """Detects available CLI tools and their versions for RAVEN integrations."""
    
    def __init__(self):
        """Initialize the capability detector."""
        self.detected: Dict[str, dict] = {}
    
    async def detect_all(self) -> Dict[str, dict]:
        """Detect all supported CLI tools.
        
        Returns:
            Dict mapping tool names to detection info (installed, version, path)
        """
        self.detected = {}
        
        # Detect Claude Code
        claude_installed = await self._detect_claude_code()
        self.detected["claude_code"] = claude_installed
        
        # Detect Codex CLI
        codex_installed = await self._detect_codex_cli()
        self.detected["codex_cli"] = codex_installed
        
        # Detect Python
        python_installed = await self._detect_python()
        self.detected["python"] = python_installed
        
        # Detect Git
        git_installed = await self._detect_git()
        self.detected["git"] = git_installed
        
        return self.detected
    
    async def _detect_claude_code(self) -> dict:
        """Detect Claude Code installation."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude-code", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=3)
            
            version_output = stderr.decode().strip()
            return {
                "installed": True,
                "version": version_output.replace("claude-code ", "").strip() 
                        if version_output else "unknown",
                "path": "claude-code",
            }
        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            return {
                "installed": False,
                "version": None,
                "path": None,
            }
    
    async def _detect_codex_cli(self) -> dict:
        """Detect Codex CLI installation."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "codex", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=3)
            
            version_output = stderr.decode().strip()
            return {
                "installed": True,
                "version": version_output.replace("codex ", "").strip() 
                        if version_output else "unknown",
                "path": "codex",
            }
        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            return {
                "installed": False,
                "version": None,
                "path": None,
            }
    
    async def _detect_python(self) -> dict:
        """Detect Python installation."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            version_output = stdout.decode().strip()
            return {
                "installed": True,
                "version": version_output,
                "path": "python3",
            }
        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            # Try python
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
                version_output = stdout.decode().strip()
                return {
                    "installed": True,
                    "version": version_output,
                    "path": "python",
                }
            except Exception:
                return {
                    "installed": False,
                    "version": None,
                    "path": None,
                }
    
    async def _detect_git(self) -> dict:
        """Detect Git installation."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            version_output = stdout.decode().strip()
            return {
                "installed": True,
                "version": version_output.replace("git version ", ""),
                "path": "git",
            }
        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            return {
                "installed": False,
                "version": None,
                "path": None,
            }