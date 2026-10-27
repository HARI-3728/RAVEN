"""Git Tools - git operations for checkpointing, diffing, and change tracking."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Dict, Any, List, Optional
import json


class GitTools:
    """Git operations for checkpoint management, diff generation, and recovery."""
    
    def __init__(self, project_root: str, timeout: int = 30):
        """Initialize git tools.
        
        Args:
            project_root: Path to the project's git repository
            timeout: Default timeout for git commands in seconds
        """
        self.project_root = os.path.abspath(project_root)
        self.timeout = timeout
    
    async def get_status(self) -> dict:
        """Get git status."""
        return await self._run(["status", "--porcelain"])
    
    async def get_log(self, 
                      max_count: int = 10, 
          file_path: Optional[str] = None) -> dict:
        """Get git log.
        
        Args:
            max_count: Maximum number of commits to return
            file_path: Optional path to filter by
            
        Returns:
            Dict with log entries
        """
        cmd = ["log", f"--max-count={max_count}", "--format=%H||%an||%ad||%s"]
        if file_path:
            cmd.append(f"--={file_path}")
        
        return await self._run(cmd)
    
    async def get_diff(self, 
                       commit_range: str = "HEAD~1..HEAD",
                       file_path: Optional[str] = None) -> dict:
        """Get git diff for a commit range.
        
        Args:
            commit_range: Git commit range (e.g., "HEAD~1..HEAD")
            file_path: Optional path to filter diff by
            
        Returns:
            Dict with diff content
        """
        cmd = ["diff", commit_range]
        if file_path:
            cmd.append(f"--={file_path}")
        
        return await self._run(cmd)
    
    async def create_checkpoint(self, message: str) -> dict:
        """Create a git checkpoint (commit).
        
        Args:
            message: Commit message
            
        Returns:
            Dict with checkpoint info
        """
        # Stage changes
        stage_result = await self._run(["add", "."])
        if stage_result.get("exit_code", 0) != 0:
            # Some files may be gitignored; that's OK
            pass
        
        # Create commit
        return await self._run(["commit", "-m", message])
    
    async def get_current_commit(self) -> Optional[str]:
        """Get the current commit hash."""
        result = await self._run(["rev-parse", "HEAD"])
        if result.get("exit_code") == 0:
            return result.get("output", "").strip()
        return None
    
    async def checkout(self, target: str) -> dict:
        """Checkout a commit, branch, or tag.
        
        Args:
            target: Commit hash, branch name, or tag
            
        Returns:
            Dict with execution result
        """
        return await self._run(["checkout", target])
    
    async def get_branch(self) -> Optional[str]:
        """Get current branch name."""
        result = await self._run(["branch", "--show-current"])
        if result.get("exit_code") == 0:
            return result.get("output", "").strip()
        return None
    
    async def _run(self, command: List[str]) -> dict:
        """Run a git command and return structured result."""
        full_cmd = ["git", *command]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=self.project_root,
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
            
            return {
                "output": output,
                "errors": errors,
                "exit_code": proc.returncode if proc.returncode is not None else -1,
                "timed_out": False,
            }
            
        except FileNotFoundError:
            return {
                "output": "",
                "errors": "Git not found - is this a git repository?",
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