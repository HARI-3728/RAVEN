"""Change Tracker - tracks modifications and supports Git checkpoints and rollbacks."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from ...tools.git_tools import GitTools


class ChangeTracker:
    """Tracks modifications and supports Git checkpoints and rollbacks."""
    
    def __init__(self, git_tools: Optional[GitTools] = None, project_root: Optional[str] = None):
        """Initialize the change tracker.
        
        Args:
            git_tools: GitTools instance (created if not provided)
            project_root: Project root directory
        """
        self.project_root = os.path.abspath(project_root) if project_root else os.getcwd()
        self.git_tools = git_tools or GitTools(self.project_root)
        self.pending_changes: List[dict] = []
        self.checkpoint_history: List[dict] = []
    
    def record_change(self, 
                      file_path: str, 
                      operation: str, 
                      old_content: Optional[str] = None,
                      new_content: Optional[str] = None,
                      agent_id: Optional[str] = None) -> None:
        """Record a change made to a file.
        
        Args:
            file_path: Path to the file that was changed
            operation: Type of operation ("write", "edit", "delete", "create")
            old_content: Content before the change (for undo)
            new_content: Content after the change
            agent_id: ID of the agent that made the change
        """
        change = {
            "file_path": file_path,
            "operation": operation,
            "old_content": old_content,
            "new_content": new_content,
            "agent_id": agent_id,
            "timestamp": asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0,
        }
        self.pending_changes.append(change)
    
    async def create_checkpoint(self, message: str) -> dict:
        """Create a git checkpoint.
        
        Args:
            message: Checkpoint message
            
        Returns:
            Dict with checkpoint creation result
        """
        result = await self.git_tools.create_checkpoint(message)
        
        # Record in history
        checkpoint = {
            "message": message,
            "commit_hash": result.get("output", "").strip() 
                          if result.get("exit_code") == 0 else None,
            "timestamp": asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0,
            "success": result.get("exit_code") == 0,
        }
        self.checkpoint_history.append(checkpoint)
        
        # Keep only last 50 checkpoints
        if len(self.checkpoint_history) > 50:
            self.checkpoint_history = self.checkpoint_history[-50:]
        
        return checkpoint
    
    async def rollback_to_checkpoint(self, commit_hash: str) -> dict:
        """Rollback to a specific git checkpoint.
        
        Args:
            commit_hash: The commit hash to rollback to
            
        Returns:
            Dict with rollback result
        """
        # Reset to the checkpoint commit
        result = await self.git_tools.checkout(commit_hash)
        
        # Record the rollback
        self.record_change(
            file_path="checkout_rollback",
            operation="rollback",
            new_content=f"Rolled back to commit {commit_hash}",
            agent_id="orchestrator",
        )
        
        return result
    
    async def get_diff_since_checkpoint(self, commit_hash: Optional[str] = None) -> Optional[dict]:
        """Get diff since a specific checkpoint.
        
        Args:
            commit_hash: The commit to diff against (defaults to last checkpoint)
            
        Returns:
            Dict with diff information or None
        """
        if commit_hash is None:
            # Get diff since last successful checkpoint
            successful_checkpoints = [
                c for c in self.checkpoint_history 
                if c.get("commit_hash")
            ]
            if successful_checkpoints:
                last_cp = successful_checkpoints[-1]
                return await self.git_tools.get_diff(
                    f"{last_cp['commit_hash']}..HEAD"
                )
            return None
        
        return await self.git_tools.get_diff(f"{commit_hash}..HEAD")
    
    def get_change_summary(self) -> dict:
        """Get a summary of pending and recorded changes."""
        return {
            "pending_changes": len(self.pending_changes),
            "checkpoint_count": len(self.checkpoint_history),
            "last_checkpoint": self.checkpoint_history[-1]["message"] 
                              if self.checkpoint_history else None,
        }