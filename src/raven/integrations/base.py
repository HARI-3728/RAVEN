"""Integrations Base - common interface for all AI tool integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio


class IntegrationBase(ABC):
    """Base class for all RAVEN integrations (CLI tools, etc.)."""
    
    def __init__(self, config: dict = None):
        """Initialize the integration."""
        self.config = config or {}
        self.name = self.__class__.__name__.lower()
        self.installed = False
        self.version = None
    
    @abstractmethod
    def detect(self) -> bool:
        """Detect whether the supported CLI or tool is installed.
        
        Returns:
            True if the tool is installed and detectable, False otherwise
        """
        pass
    
    @abstractmethod
    async def execute(self, command: str, **kwargs) -> dict:
        """Execute a command through the integrated tool.
        
        Args:
            command: The command to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Dict with execution results (output, errors, exit_code, etc.)
        """
        pass
    
    @abstractmethod
    def parse_output(self, raw_output: str) -> Any:
        """Parse the raw output from the integrated tool.
        
        Args:
            raw_output: The raw stdout/stderr from the tool
            
        Returns:
            Parsed, structured output
        """
        pass
    
    def get_info(self) -> dict:
        """Get information about this integration."""
        return {
            "name": self.name,
            "installed": self.installed,
            "version": self.version,
            "config": dict(self.config) if self.config else {},
        }


class SubprocessManager:
    """Cross-platform subprocess execution with streaming output support."""
    
    def __init__(self, timeout: int = 60, strip_ansi: bool = True):
        """Initialize the subprocess manager.
        
        Args:
            timeout: Default timeout in seconds
            strip_ansi: Whether to strip ANSI escape codes from output
        """
        self.timeout = timeout
        self.strip_ansi = strip_ansi
    
    async def run(self, 
                  command: List[str], 
                  cwd: str = "",
                  env: Optional[dict] = None,
                  stream: bool = False) -> dict:
        """Run a subprocess command.
        
        Args:
            command: Command and arguments as a list
            cwd: Working directory for the command
            env: Environment variables to override
            stream: Whether to stream output in real-time
            
        Returns:
            Dict with keys: output, errors, exit_code, timed_out
        """
        try:
            import shlex
            full_cmd = shlex.join(command)
            
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd or None,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "output": "",
                    "errors": "Command timed out",
                    "exit_code": -1,
                    "timed_out": True,
                }
            
            output = stdout.decode(errors="replace")
            errors = stderr.decode(errors="replace")
            
            # Strip ANSI codes if requested
            if self.strip_ansi:
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                output = ansi_escape.sub('', output)
                errors = ansi_escape.sub('', errors)
            
            return {
                "output": output,
                "errors": errors,
                "exit_code": proc.returncode if proc.returncode is not None else -1,
                "timed_out": False,
            }
            
        except FileNotFoundError:
            return {
                "output": "",
                "errors": f"Command not found: {command[0]}",
                "exit_code": -1,
                "timed_out": False,
            }
        except Exception as e:
            return {
                "output": "",
                "errors": str(e),
                "exit_code": -1,
                "timed_out": False,
            }