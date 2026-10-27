"""Git Manager - Git wrapper for checkpoint management, diff generation, and recovery."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, List, Optional
from pathlib import Path


class GitManager:
    """Git wrapper for checkpoint management, diff generation, and recovery."""
    
    def __init__(self, project_root: str, approval_manager=None):
        """Initialize the git manager.
        
        Args:
            project_root: Project root directory
            approval_manager: Optional approval manager for dangerous operations
        """
        self.project_root = os.path.abspath(project_root)
        self.approval_manager = approval_manager
        self.git_tools = GitTools(self.project_root)
    
    async def status(self) -> dict:
        """Get git status."""
        return await self.git_tools.get_status()
    
    async def log(self, max_count: int = 10) -> dict:
        """Get git log."""
        return await self.git_tools.get_log(max_count=max_count)
    
    async def diff(self, commit_range: str = "HEAD~1..HEAD", file_path: Optional[str] = None) -> dict:
        """Get git diff."""
        return await self.git_tools.get_diff(commit_range, file_path)
    
    async def create_checkpoint(self, message: str) -> dict:
        """Create a git checkpoint with optional approval.
        
        Args:
            message: Commit message
            
        Returns:
            Dict with checkpoint result
        """
        # For sensitive checkpoints, ask for approval
        if self.approval_manager:
            approved = await self.approval_manager.request_approval(
                operation_id=f"git_checkpoint_{message[:20]}",
                command=f"git commit -m '{message}'",
                description=f"Create git checkpoint: {message}"
            )
            
            if not approved:
                return {
                    "output": "",
                    "errors": "Checkpoint creation denied by user",
                    "exit_code": 1,
                    "timed_out": False,
                }
        
        return await self.git_tools.create_checkpoint(message)
    
    async def checkout(self, target: str) -> dict:
        """Checkout a commit, branch, or tag with approval if needed."""
        if self.approval_manager:
            approved = await self.approval_manager.request_approval(
                operation_id=f"git_checkout_{target[:20]}",
                command=f"git checkout {target}",
                description=f"Checkout {target}"
            )
            
            if not approved:
                return {
                    "output": "",
                    "errors": "Checkout denied by user",
                    "exit_code": 1,
                    "timed_out": False,
                }
        
        return await self.git_tools.checkout(target)
    
    async def reset(self, target: str, hard: bool = True) -> dict:
        """Reset to a checkpoint with approval.
        
        Args:
            target: Commit hash, branch, or tag
            hard: Whether to do a hard reset
            
        Returns:
            Dict with reset result
        """
        if self.approval_manager:
            reset_type = "--hard" if hard else "--soft"
            approved = await self.approval_manager.request_approval(
                operation_id=f"git_reset_{target[:20]}",
                command=f"git reset {reset_type} {target}",
                description=f"Reset to {target} ({reset_type})"
            )
            
            if not approved:
                return {
                    "output": "",
                    "errors": "Reset denied by user",
                    "exit_code": 1,
                    "timed_out": False,
                }
        
        return await self.git_tools._run(["reset", ("--hard" if hard else "--soft"), target])
    
    async def get_current_commit(self) -> Optional[str]:
        """Get the current commit hash."""
        return await self.git_tools.get_current_commit()